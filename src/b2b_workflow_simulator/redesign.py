"""Redesign diff engine: structured before/after comparison of two simulation runs."""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult


@dataclass(frozen=True)
class MetricDelta:
    """A single business metric compared across the before and after runs.

    Attributes:
        label: Human-readable metric name, e.g. "Cost per case".
        before: Value observed in the "before" simulation.
        after: Value observed in the "after" simulation.
    """

    label: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        """Absolute change: after minus before. Negative means it decreased."""
        return self.after - self.before

    @property
    def percent_change(self) -> float | None:
        """Relative change as a percentage of the "before" value, or None if before is 0."""
        if self.before == 0:
            return None
        return (self.after - self.before) / abs(self.before) * 100.0


@dataclass
class ROIAnalysis:
    """Financial impact of a workflow redesign, derived from simulated cost deltas.

    Attributes:
        total_cost_savings: `before.total_cost - after.total_cost` for the
            simulated case volume. Positive means the redesign is cheaper.
        cost_savings_per_case: Same idea, normalized to a single case.
        roi_percentage: `total_cost_savings` as a percentage of the
            "before" total cost, or None if the before cost was zero.
        implementation_cost: The one-time cost of implementing the redesign,
            if supplied by the caller. None if not provided.
        payback_in_cases: How many cases' worth of savings it takes to
            recover `implementation_cost`. None if no implementation cost
            was given, or if the redesign does not produce net savings.
        payback_feasible: Whether the redesign produces enough per-case
            savings to eventually recover its implementation cost at all.
    """

    total_cost_savings: float
    cost_savings_per_case: float
    roi_percentage: float | None
    implementation_cost: float | None = None
    payback_in_cases: float | None = None
    payback_feasible: bool = False


@dataclass
class RedesignDiff:
    """A structured comparison between a "before" and an "after" workflow run.

    This is the primary artifact for evaluating a proposed AI-driven
    redesign: it packages every metric a consultant or ops leader would
    want to see side by side, plus a derived ROI analysis, so a report can
    be generated without re-deriving numbers from raw `KPIResult` objects.
    """

    before_name: str
    after_name: str
    completion_rate: MetricDelta
    failure_rate: MetricDelta
    total_cost: MetricDelta
    cost_per_case: MetricDelta
    cycle_time_minutes: MetricDelta
    wait_time_minutes: MetricDelta
    escalation_rate: MetricDelta
    roi: ROIAnalysis
    before_bottlenecks: list[tuple[str, float]] = field(default_factory=list)
    after_bottlenecks: list[tuple[str, float]] = field(default_factory=list)
    before_utilization: dict[str, float] = field(default_factory=dict)
    after_utilization: dict[str, float] = field(default_factory=dict)

    @property
    def metrics(self) -> list[MetricDelta]:
        """All headline metric deltas, in a stable, report-friendly order."""
        return [
            self.completion_rate,
            self.failure_rate,
            self.total_cost,
            self.cost_per_case,
            self.cycle_time_minutes,
            self.wait_time_minutes,
            self.escalation_rate,
        ]


def compare_workflows(
    before: KPIResult,
    after: KPIResult,
    implementation_cost: float | None = None,
) -> RedesignDiff:
    """Build a `RedesignDiff` from two `KPIResult` objects.

    Args:
        before: KPI result from simulating the current-state workflow.
        after: KPI result from simulating the redesigned workflow.
        implementation_cost: Optional one-time cost of implementing the
            redesign, used to compute payback in `ROIAnalysis`.

    Returns:
        A `RedesignDiff` summarizing every metric named in `MetricDelta`
        plus an `ROIAnalysis`.
    """
    roi = _compute_roi(before, after, implementation_cost)

    return RedesignDiff(
        before_name=before.workflow_name,
        after_name=after.workflow_name,
        completion_rate=MetricDelta(
            "Completion rate", before.completion_rate, after.completion_rate
        ),
        failure_rate=MetricDelta("Failure rate", before.failure_rate, after.failure_rate),
        total_cost=MetricDelta("Total cost", before.total_cost, after.total_cost),
        cost_per_case=MetricDelta(
            "Cost per case", before.avg_cost_per_case, after.avg_cost_per_case
        ),
        cycle_time_minutes=MetricDelta(
            "Cycle time (minutes)", before.avg_cycle_time_minutes, after.avg_cycle_time_minutes
        ),
        wait_time_minutes=MetricDelta(
            "Wait time (minutes)", before.avg_wait_time_minutes, after.avg_wait_time_minutes
        ),
        escalation_rate=MetricDelta(
            "Escalation rate", before.escalation_rate, after.escalation_rate
        ),
        roi=roi,
        before_bottlenecks=before.bottleneck_nodes(),
        after_bottlenecks=after.bottleneck_nodes(),
        before_utilization=dict(before.actor_utilization),
        after_utilization=dict(after.actor_utilization),
    )


def _compute_roi(
    before: KPIResult, after: KPIResult, implementation_cost: float | None
) -> ROIAnalysis:
    total_cost_savings = before.total_cost - after.total_cost
    cost_savings_per_case = before.avg_cost_per_case - after.avg_cost_per_case
    roi_percentage = (
        (total_cost_savings / before.total_cost) * 100.0 if before.total_cost > 0 else None
    )

    payback_in_cases: float | None = None
    payback_feasible = False
    if implementation_cost is not None and cost_savings_per_case > 0:
        payback_in_cases = implementation_cost / cost_savings_per_case
        payback_feasible = True

    return ROIAnalysis(
        total_cost_savings=total_cost_savings,
        cost_savings_per_case=cost_savings_per_case,
        roi_percentage=roi_percentage,
        implementation_cost=implementation_cost,
        payback_in_cases=payback_in_cases,
        payback_feasible=payback_feasible,
    )


__all__ = ["MetricDelta", "ROIAnalysis", "RedesignDiff", "compare_workflows"]
