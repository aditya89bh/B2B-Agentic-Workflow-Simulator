"""Organizational restructuring simulation: evaluate design-change scenarios.

Strategy and operations teams regularly consider structural changes:
centralizing a function for scale, spinning out a team for focus,
creating a shared-services group to reduce duplication, or bringing in
an AI operations capability.  Each change has predictable directional
effects on cost, cycle time, risk, staffing, and budget.

This module models those effects analytically -- it does not re-run the
simulation engine -- by applying parameterized heuristics to the
existing KPI baseline and the organizational structure.  The result is a
fast, explainable ``RestructuringImpact`` for each scenario, which can
then be ranked and included in the org executive report.

All impacts are expressed as *deltas* from the current baseline:
negative ``cost_impact`` means savings, negative ``risk_delta`` means
lower risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.budget import OrgBudget
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.org_model import Organization

CENTRALIZE_TEAM = "centralize_team"
DECENTRALIZE_TEAM = "decentralize_team"
ADD_SHARED_SERVICES = "add_shared_services"
OUTSOURCE_STAGE = "outsource_stage"
CREATE_AI_OPS_TEAM = "create_ai_ops_team"
HIRE_ADDITIONAL_STAFF = "hire_additional_staff"
REDUCE_APPROVAL_LAYERS = "reduce_approval_layers"

SCENARIO_TYPES = (
    CENTRALIZE_TEAM,
    DECENTRALIZE_TEAM,
    ADD_SHARED_SERVICES,
    OUTSOURCE_STAGE,
    CREATE_AI_OPS_TEAM,
    HIRE_ADDITIONAL_STAFF,
    REDUCE_APPROVAL_LAYERS,
)

SCENARIO_TYPE_LABELS: dict[str, str] = {
    CENTRALIZE_TEAM: "Centralize Team",
    DECENTRALIZE_TEAM: "Decentralize Team",
    ADD_SHARED_SERVICES: "Add Shared Services Function",
    OUTSOURCE_STAGE: "Outsource Workflow Stage",
    CREATE_AI_OPS_TEAM: "Create AI Operations Team",
    HIRE_ADDITIONAL_STAFF: "Hire Additional Staff",
    REDUCE_APPROVAL_LAYERS: "Reduce Approval Layers",
}


@dataclass
class RestructuringScenario:
    """A single organizational restructuring option to evaluate.

    Attributes:
        scenario_id: Unique identifier.
        scenario_type: One of the ``SCENARIO_TYPES`` constants.
        description: Human-readable description of what this scenario
            proposes.
        parameters: Optional type-specific configuration.  Recognized
            keys differ by ``scenario_type``; unknown keys are ignored.

            Common parameters:

            - ``"headcount_delta"`` (int): Net change in headcount
              (positive = hire, negative = reduce).
            - ``"cost_reduction_fraction"`` (float 0-1): Expected
              fractional reduction in operating cost.
            - ``"cycle_time_reduction_fraction"`` (float 0-1): Expected
              fractional reduction in average cycle time.
            - ``"approval_layers_removed"`` (int): Number of approval
              stages eliminated (for ``REDUCE_APPROVAL_LAYERS``).
            - ``"outsource_cost_per_case"`` (float): Unit cost of the
              outsourced stage (for ``OUTSOURCE_STAGE``).
    """

    scenario_id: str
    scenario_type: str
    description: str
    parameters: dict = field(default_factory=dict)


@dataclass
class RestructuringImpact:
    """Projected impact of a restructuring scenario on key org metrics.

    All numeric fields are *deltas* from the current baseline:

    - Negative ``cost_impact`` → annual cost savings.
    - Negative ``cycle_time_impact_minutes`` → faster average cycle time.
    - Negative ``risk_delta`` → lower organizational risk.
    - Positive ``staffing_delta`` → net headcount increase.
    - Negative ``budget_impact`` → budget savings.

    Attributes:
        scenario: The scenario that produced this impact.
        cost_impact: Annual cost delta in currency units.
        cycle_time_impact_minutes: Delta in average case cycle time.
        risk_delta: Delta in organizational risk score (-100 to +100).
        staffing_delta: Net headcount change (integer).
        budget_impact: Annual budget delta in currency units.
        summary: One-sentence plain-text summary.
        recommendations: Actionable next steps.
    """

    scenario: RestructuringScenario
    cost_impact: float
    cycle_time_impact_minutes: float
    risk_delta: float
    staffing_delta: int
    budget_impact: float
    summary: str
    recommendations: list[str] = field(default_factory=list)

    @property
    def is_cost_positive(self) -> bool:
        """``True`` when the scenario produces cost savings."""
        return self.cost_impact < 0

    @property
    def is_risk_positive(self) -> bool:
        """``True`` when the scenario reduces organizational risk."""
        return self.risk_delta < 0

    @property
    def net_benefit_score(self) -> float:
        """Simple composite benefit score for ranking scenarios.

        Combines cost savings (40 pts), cycle time reduction (30 pts),
        and risk reduction (30 pts), each normalized to [-50, +50].
        Higher is better.
        """
        cost_pts = -self.cost_impact / 1000.0
        time_pts = -self.cycle_time_impact_minutes / 10.0
        risk_pts = -self.risk_delta
        return (cost_pts * 0.4) + (time_pts * 0.3) + (risk_pts * 0.3)


def _total_annual_cost(kpi_results: dict[str, KPIResult]) -> float:
    """Estimate annualized operating cost from a set of simulation KPIs.

    Uses ``total_cost`` (which covers one simulation run) as a proxy;
    the caller is expected to set ``num_cases`` to a monthly figure so
    ``total_cost * 12`` approximates annual cost.
    """
    return sum(kpi.total_cost for kpi in kpi_results.values()) * 12


def _avg_cycle_time(kpi_results: dict[str, KPIResult]) -> float:
    """Average cycle time across all workflows, weighted by case volume."""
    total_cases = sum(kpi.total_cases for kpi in kpi_results.values())
    if total_cases == 0:
        return 0.0
    weighted = sum(kpi.avg_cycle_time_minutes * kpi.total_cases for kpi in kpi_results.values())
    return weighted / total_cases


def evaluate_restructuring(
    org: Organization,
    base_kpi_results: dict[str, KPIResult],
    scenario: RestructuringScenario,
    org_budget: OrgBudget | None = None,
) -> RestructuringImpact:
    """Evaluate one restructuring scenario and return its projected impact.

    The evaluation applies directional heuristics anchored to the
    current baseline KPIs and org structure.  All estimates carry
    inherent uncertainty and should be treated as directional signals,
    not precise forecasts.

    Args:
        org: The current organization model.
        base_kpi_results: Baseline KPI results keyed by workflow ID.
        scenario: The restructuring option to evaluate.
        org_budget: Optional budget model; used for budget impact
            estimates when present.

    Returns:
        A :class:`RestructuringImpact` summarising projected effects.
    """
    params = scenario.parameters
    annual_cost = _total_annual_cost(base_kpi_results)
    avg_ct = _avg_cycle_time(base_kpi_results)
    total_budget = org_budget.total_budget if org_budget else annual_cost

    if scenario.scenario_type == CENTRALIZE_TEAM:
        cost_fraction = float(params.get("cost_reduction_fraction", 0.08))
        ct_fraction = float(params.get("cycle_time_reduction_fraction", 0.05))
        headcount_delta = int(params.get("headcount_delta", -1))
        cost_impact = -annual_cost * cost_fraction
        ct_impact = -avg_ct * ct_fraction
        risk_delta = -5.0
        budget_impact = cost_impact
        summary = (
            f"Centralizing the team is projected to reduce annual cost by "
            f"~{cost_fraction:.0%} and cut average cycle time by "
            f"~{ct_fraction:.0%} through reduced duplication."
        )
        recs = [
            "Identify duplicated roles across distributed teams before consolidating.",
            "Establish a single point of contact to manage cross-department requests.",
        ]

    elif scenario.scenario_type == DECENTRALIZE_TEAM:
        ct_fraction = float(params.get("cycle_time_reduction_fraction", 0.12))
        headcount_delta = int(params.get("headcount_delta", 2))
        cost_impact = annual_cost * 0.05
        ct_impact = -avg_ct * ct_fraction
        risk_delta = 3.0
        budget_impact = cost_impact
        summary = (
            "Decentralizing the team is projected to reduce cycle time by "
            f"~{ct_fraction:.0%} by embedding specialists closer to the work, "
            "at the cost of slightly higher overhead."
        )
        recs = [
            "Establish clear service standards to prevent quality divergence.",
            "Use shared tooling to maintain visibility across decentralized units.",
        ]

    elif scenario.scenario_type == ADD_SHARED_SERVICES:
        cost_fraction = float(params.get("cost_reduction_fraction", 0.10))
        headcount_delta = int(params.get("headcount_delta", 1))
        cost_impact = -annual_cost * cost_fraction
        ct_impact = avg_ct * 0.05
        risk_delta = -8.0
        budget_impact = -total_budget * 0.05
        summary = (
            "A shared-services function consolidates repetitive tasks, reducing "
            f"operating cost by ~{cost_fraction:.0%} while adding a modest "
            "coordination overhead to cycle time."
        )
        recs = [
            "Define a clear SLA between the shared-services function and consuming teams.",
            "Measure first-year adoption rate; target >70% within 6 months.",
        ]

    elif scenario.scenario_type == OUTSOURCE_STAGE:
        outsource_cost = float(params.get("outsource_cost_per_case", 20.0))
        total_cases = sum(kpi.total_cases for kpi in base_kpi_results.values())
        outsource_annual = outsource_cost * total_cases * 12
        cost_impact = outsource_annual - annual_cost * 0.15
        headcount_delta = int(params.get("headcount_delta", -2))
        ct_impact = -avg_ct * float(params.get("cycle_time_reduction_fraction", 0.08))
        risk_delta = 10.0
        budget_impact = cost_impact
        summary = (
            "Outsourcing the stage transfers execution risk to a third party and "
            "may reduce internal cost, but introduces vendor dependency and "
            "compliance exposure."
        )
        recs = [
            "Negotiate SLAs with the vendor before signing; include penalty clauses.",
            "Retain at least one internal subject-matter expert to oversee quality.",
            "Run a parallel 90-day pilot before full cutover.",
        ]

    elif scenario.scenario_type == CREATE_AI_OPS_TEAM:
        cost_fraction = float(params.get("cost_reduction_fraction", 0.15))
        ct_fraction = float(params.get("cycle_time_reduction_fraction", 0.20))
        headcount_delta = int(params.get("headcount_delta", 2))
        cost_impact = -annual_cost * cost_fraction
        ct_impact = -avg_ct * ct_fraction
        risk_delta = -12.0
        budget_impact = -total_budget * 0.08
        summary = (
            "A dedicated AI Operations team accelerates automation adoption, "
            f"projected to cut cost by ~{cost_fraction:.0%} and cycle time "
            f"by ~{ct_fraction:.0%} within 12 months."
        )
        recs = [
            "Staff the team with at least one ML engineer and one process specialist.",
            "Prioritize the highest-volume, lowest-complexity stages for first automation.",
            "Measure AI error and escalation rates monthly against targets.",
        ]

    elif scenario.scenario_type == HIRE_ADDITIONAL_STAFF:
        headcount_delta = int(params.get("headcount_delta", 1))
        ct_fraction = float(params.get("cycle_time_reduction_fraction", 0.10))
        hourly_cost = float(params.get("hourly_cost_per_hire", 60.0))
        hire_annual_cost = headcount_delta * hourly_cost * 8 * 22 * 12
        cost_impact = hire_annual_cost
        ct_impact = -avg_ct * ct_fraction
        risk_delta = -7.0
        budget_impact = hire_annual_cost
        summary = (
            f"Adding {headcount_delta} staff member(s) is projected to reduce "
            f"average cycle time by ~{ct_fraction:.0%} by relieving the current "
            "bottleneck, at a direct hiring cost."
        )
        recs = [
            "Identify the highest-utilization actor/role before creating job reqs.",
            "Consider upskilling existing staff before external hiring.",
        ]

    elif scenario.scenario_type == REDUCE_APPROVAL_LAYERS:
        layers_removed = int(params.get("approval_layers_removed", 1))
        ct_fraction = min(0.30, layers_removed * float(params.get("cycle_time_per_layer", 0.10)))
        headcount_delta = -layers_removed
        cost_impact = -annual_cost * ct_fraction * 0.5
        ct_impact = -avg_ct * ct_fraction
        risk_delta = 5.0 * layers_removed
        budget_impact = cost_impact
        summary = (
            f"Removing {layers_removed} approval layer(s) cuts average cycle time by "
            f"~{ct_fraction:.0%} and frees approver capacity, but increases "
            "process risk proportionally."
        )
        recs = [
            "Replace removed approvals with automated policy checks where possible.",
            "Monitor error and exception rates for 90 days after the change.",
            f"Ensure compliance requirements are still met without the {layers_removed} "
            "removed layer(s).",
        ]

    else:
        cost_impact = 0.0
        ct_impact = 0.0
        risk_delta = 0.0
        headcount_delta = 0
        budget_impact = 0.0
        summary = f"Unknown scenario type '{scenario.scenario_type}'; no impact estimated."
        recs = []

    return RestructuringImpact(
        scenario=scenario,
        cost_impact=cost_impact,
        cycle_time_impact_minutes=ct_impact,
        risk_delta=risk_delta,
        staffing_delta=headcount_delta,
        budget_impact=budget_impact,
        summary=summary,
        recommendations=recs,
    )


def compare_restructuring_scenarios(
    org: Organization,
    base_kpi_results: dict[str, KPIResult],
    scenarios: list[RestructuringScenario],
    org_budget: OrgBudget | None = None,
) -> list[RestructuringImpact]:
    """Evaluate a list of scenarios and return impacts sorted by net benefit.

    Args:
        org: The current organization model.
        base_kpi_results: Baseline KPI results keyed by workflow ID.
        scenarios: Scenarios to evaluate.
        org_budget: Optional budget context.

    Returns:
        List of :class:`RestructuringImpact` objects, best first.
    """
    impacts = [
        evaluate_restructuring(org, base_kpi_results, scenario, org_budget)
        for scenario in scenarios
    ]
    return sorted(impacts, key=lambda i: i.net_benefit_score, reverse=True)


def generate_restructuring_report(impacts: list[RestructuringImpact]) -> str:
    """Render a ranked restructuring comparison as a plain-text report.

    Args:
        impacts: Pre-ranked list of :class:`RestructuringImpact` objects
            (e.g. from :func:`compare_restructuring_scenarios`).

    Returns:
        A multi-line plain-text report string.
    """
    if not impacts:
        return "No restructuring scenarios to report."
    lines: list[str] = [
        "=" * 60,
        "ORGANIZATIONAL RESTRUCTURING ANALYSIS",
        "=" * 60,
        "",
    ]
    for rank, impact in enumerate(impacts, start=1):
        label = SCENARIO_TYPE_LABELS.get(
            impact.scenario.scenario_type, impact.scenario.scenario_type
        )
        lines += [
            f"{rank}. {label}: {impact.scenario.description}",
            "-" * 60,
            f"   {impact.summary}",
            f"   Cost impact:          {impact.cost_impact:+,.0f} (annual)",
            f"   Cycle time impact:    {impact.cycle_time_impact_minutes:+,.1f} min",
            f"   Risk delta:           {impact.risk_delta:+.1f}",
            f"   Staffing delta:       {impact.staffing_delta:+d}",
            f"   Budget impact:        {impact.budget_impact:+,.0f} (annual)",
        ]
        if impact.recommendations:
            lines.append("   Recommendations:")
            lines += [f"     - {r}" for r in impact.recommendations]
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "ADD_SHARED_SERVICES",
    "CENTRALIZE_TEAM",
    "CREATE_AI_OPS_TEAM",
    "DECENTRALIZE_TEAM",
    "HIRE_ADDITIONAL_STAFF",
    "OUTSOURCE_STAGE",
    "REDUCE_APPROVAL_LAYERS",
    "RestructuringImpact",
    "RestructuringScenario",
    "SCENARIO_TYPE_LABELS",
    "SCENARIO_TYPES",
    "compare_restructuring_scenarios",
    "evaluate_restructuring",
    "generate_restructuring_report",
]
