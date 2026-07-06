"""Growth projection engine: simulate future demand and capacity limits.

Organizations do not stay the same size.  Sales pipelines grow, customer
bases expand, and AI adoption accelerates -- all of which drive more
cases through the same (or slightly larger) workflows.  At some point,
current staffing and budgets break under the load.

`project_growth` generates a 12-month forward view by compounding
monthly growth, overlaying seasonal patterns, and tracking the gap
between rising demand and slowly-growing capacity.  It identifies
*breaking points*: months where the workflow machinery can no longer
absorb the incoming volume under current staffing assumptions.

Design notes:

- Growth is modelled analytically (not by re-running the simulation
  engine for every month), so projections are fast and explainable.
- ``GrowthConfig.seasonal_multipliers`` accepts 12 values (one per
  month, Jan-Dec).  A January value of 1.2 means 20% above the
  base-month volume.
- Capacity is approximated as ``base_headcount * actor_capacity_per_head
  * simulation_days_per_month``.  When projected demand minutes exceed
  this capacity, a breaking point is flagged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.budget import OrgBudget
from b2b_workflow_simulator.org_model import Organization

_CAPACITY_OVERLOAD_THRESHOLD = 1.0
_BUDGET_OVERLOAD_THRESHOLD = 1.15


@dataclass
class GrowthConfig:
    """Parameters for a 12-month growth projection.

    Attributes:
        monthly_growth_rate: Fractional increase in case volume each
            month (e.g. 0.05 = 5% MoM growth).
        seasonal_multipliers: 12 floats, one per month (Jan=0, Dec=11).
            Applied multiplicatively on top of compounded growth.
        headcount_growth_rate: Fractional increase in headcount per
            month (e.g. 0.02 = 2% MoM headcount growth from hiring).
        ai_adoption_increase_rate: Monthly increment in AI adoption
            level (0.0-1.0 scale; 0.02 = 2 percentage points/month).
        budget_increase_rate: Monthly fractional budget increase.
        base_cases_per_month: Baseline case volume in month 0.
        base_cost_per_case: Baseline cost per completed case.
        base_headcount: Number of people/agents in month 0.
        actor_capacity_per_head: Available minutes per person per day.
        simulation_days_per_month: Working days per month used for
            capacity calculations.
    """

    monthly_growth_rate: float = 0.05
    seasonal_multipliers: list[float] = field(default_factory=lambda: [1.0] * 12)
    headcount_growth_rate: float = 0.0
    ai_adoption_increase_rate: float = 0.0
    budget_increase_rate: float = 0.0
    base_cases_per_month: int = 200
    base_cost_per_case: float = 100.0
    base_headcount: int = 10
    actor_capacity_per_head: float = 480.0
    simulation_days_per_month: int = 22

    def __post_init__(self) -> None:
        if len(self.seasonal_multipliers) != 12:
            raise ValueError(
                f"seasonal_multipliers must have exactly 12 values, "
                f"got {len(self.seasonal_multipliers)}"
            )
        if self.base_cases_per_month <= 0:
            raise ValueError("base_cases_per_month must be positive")
        if self.base_headcount <= 0:
            raise ValueError("base_headcount must be positive")


@dataclass
class GrowthProjectionPoint:
    """Snapshot of the organization at one projected month.

    Attributes:
        month: 1-based month index (1 = first projected month).
        projected_cases: Estimated case volume for this month.
        projected_cost: Estimated total cost for this month.
        projected_headcount: Estimated headcount (may be fractional
            due to monthly compounding).
        projected_budget: Estimated total budget for this month.
        ai_adoption_level: AI adoption fraction (0.0 to 1.0).
        capacity_utilization: Ratio of demand minutes to available
            capacity minutes.  Values > 1.0 indicate overload.
        is_breaking_point: ``True`` when this month exceeds a
            capacity or budget threshold.
        breaking_point_reason: Human-readable explanation of why this
            month is a breaking point, or ``None``.
    """

    month: int
    projected_cases: int
    projected_cost: float
    projected_headcount: float
    projected_budget: float
    ai_adoption_level: float
    capacity_utilization: float
    is_breaking_point: bool = False
    breaking_point_reason: str | None = None


@dataclass
class GrowthProjection:
    """12-month growth forecast for an organization.

    Attributes:
        org_id: The organization this projection covers.
        org_name: Human-readable organization name.
        config: The ``GrowthConfig`` used to generate this projection.
        points: Ordered list of 12 :class:`GrowthProjectionPoint`
            objects (months 1-12).
    """

    org_id: str
    org_name: str
    config: GrowthConfig
    points: list[GrowthProjectionPoint]

    def at_month(self, month: int) -> GrowthProjectionPoint:
        """Return the projection point for the given 1-based month.

        Raises:
            ValueError: If ``month`` is not in 1-12.
        """
        if month < 1 or month > len(self.points):
            raise ValueError(f"month must be between 1 and {len(self.points)}, got {month}")
        return self.points[month - 1]

    def three_month(self) -> list[GrowthProjectionPoint]:
        """First 3 months of the projection."""
        return self.points[:3]

    def six_month(self) -> list[GrowthProjectionPoint]:
        """First 6 months of the projection."""
        return self.points[:6]

    def twelve_month(self) -> list[GrowthProjectionPoint]:
        """All 12 months of the projection."""
        return list(self.points)

    def breaking_points(self) -> list[GrowthProjectionPoint]:
        """All months flagged as breaking points."""
        return [p for p in self.points if p.is_breaking_point]

    def first_breaking_point(self) -> GrowthProjectionPoint | None:
        """The earliest breaking point, or ``None`` if none exist."""
        bps = self.breaking_points()
        return bps[0] if bps else None

    def peak_utilization_month(self) -> GrowthProjectionPoint:
        """Return the month with the highest capacity utilization."""
        return max(self.points, key=lambda p: p.capacity_utilization)


def project_growth(
    org: Organization,
    org_budget: OrgBudget | None,
    config: GrowthConfig,
    base_kpi_cost_per_case: float | None = None,
) -> GrowthProjection:
    """Generate a 12-month growth projection.

    Args:
        org: The organization to project growth for.  Used for naming
            and headcount context.
        org_budget: Optional budget model; the base monthly budget is
            inferred from total annual budget / 12 when provided.
        config: Growth parameters.
        base_kpi_cost_per_case: Override the cost-per-case assumption.
            When ``None``, ``config.base_cost_per_case`` is used.

    Returns:
        A :class:`GrowthProjection` with 12 monthly snapshots.
    """
    cost_per_case = (
        base_kpi_cost_per_case if base_kpi_cost_per_case is not None else config.base_cost_per_case
    )
    if org_budget is not None:
        base_monthly_budget = org_budget.total_budget / 12.0
    else:
        base_monthly_budget = config.base_cost_per_case * config.base_cases_per_month

    points: list[GrowthProjectionPoint] = []
    for i in range(12):
        month = i + 1
        growth_factor = (1.0 + config.monthly_growth_rate) ** i
        seasonal = config.seasonal_multipliers[i % 12]
        raw_cases = config.base_cases_per_month * growth_factor * seasonal
        projected_cases = max(1, int(round(raw_cases)))

        headcount = config.base_headcount * (1.0 + config.headcount_growth_rate) ** i
        current_capacity = (
            headcount * config.actor_capacity_per_head * config.simulation_days_per_month
        )

        ai_adoption = min(1.0, config.ai_adoption_increase_rate * i)
        effective_cost_per_case = cost_per_case * (1.0 - ai_adoption * 0.3)
        projected_cost = projected_cases * effective_cost_per_case

        budget_factor = (1.0 + config.budget_increase_rate) ** i
        projected_budget = base_monthly_budget * budget_factor

        demand_minutes = projected_cases * (config.actor_capacity_per_head * 0.1)
        cap_util = demand_minutes / current_capacity if current_capacity > 0 else 0.0

        is_breaking = False
        reason: str | None = None
        if cap_util > _CAPACITY_OVERLOAD_THRESHOLD:
            is_breaking = True
            reason = (
                f"Projected demand ({demand_minutes:,.0f} min) exceeds available "
                f"capacity ({current_capacity:,.0f} min) at month {month}."
            )
        elif projected_cost > projected_budget * _BUDGET_OVERLOAD_THRESHOLD:
            is_breaking = True
            reason = (
                f"Projected cost (${projected_cost:,.0f}) exceeds monthly budget "
                f"(${projected_budget:,.0f}) by more than "
                f"{(_BUDGET_OVERLOAD_THRESHOLD - 1.0):.0%} at month {month}."
            )

        points.append(
            GrowthProjectionPoint(
                month=month,
                projected_cases=projected_cases,
                projected_cost=projected_cost,
                projected_headcount=headcount,
                projected_budget=projected_budget,
                ai_adoption_level=ai_adoption,
                capacity_utilization=cap_util,
                is_breaking_point=is_breaking,
                breaking_point_reason=reason,
            )
        )

    return GrowthProjection(
        org_id=org.org_id,
        org_name=org.name,
        config=config,
        points=points,
    )


def generate_growth_report(projection: GrowthProjection) -> str:
    """Render a :class:`GrowthProjection` as a plain-text report.

    Args:
        projection: A 12-month growth projection.

    Returns:
        A multi-line plain-text report string.
    """
    cfg = projection.config
    first_bp = projection.first_breaking_point()
    lines: list[str] = [
        "=" * 60,
        f"GROWTH PROJECTION: {projection.org_name}",
        "=" * 60,
        "",
        "Configuration:",
        f"  Monthly growth rate:    {cfg.monthly_growth_rate:.1%}",
        f"  Base cases/month:       {cfg.base_cases_per_month}",
        f"  Base headcount:         {cfg.base_headcount}",
        f"  Headcount growth:       {cfg.headcount_growth_rate:.1%}/month",
        f"  AI adoption rate:       +{cfg.ai_adoption_increase_rate:.1%}/month",
        "",
        f"{'Month':<8}{'Cases':>8}{'Cost':>12}"
        f"{'Headcount':>11}{'Cap.Util':>10}{'AI Adopt':>10}{'Break?':>8}",
        "-" * 60,
    ]
    for p in projection.points:
        bp_flag = "BREAK" if p.is_breaking_point else ""
        lines.append(
            f"{p.month:<8}{p.projected_cases:>8}{p.projected_cost:>12,.0f}"
            f"{p.projected_headcount:>11.1f}{p.capacity_utilization:>9.1%}"
            f"{p.ai_adoption_level:>10.1%}{bp_flag:>8}"
        )
    lines.append("")
    if first_bp:
        lines.append(
            f"First breaking point: Month {first_bp.month} — {first_bp.breaking_point_reason}"
        )
    else:
        lines.append("No breaking points detected within the 12-month horizon.")
    return "\n".join(lines)


__all__ = [
    "GrowthConfig",
    "GrowthProjection",
    "GrowthProjectionPoint",
    "generate_growth_report",
    "project_growth",
]
