"""Sensitivity analysis: sweep a redesign assumption and observe the impact on ROI."""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.redesign import RedesignDiff, compare_workflows
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow

PARAMETERS = (
    "ai_error_rate",
    "ai_cost_per_execution",
    "human_hourly_cost",
    "arrival_interval",
    "implementation_cost",
)


@dataclass(frozen=True)
class SweepPoint:
    """One simulated outcome at a single value of the swept parameter."""

    value: float
    diff: RedesignDiff


@dataclass
class SensitivityResult:
    """The full output of a sensitivity sweep across one parameter.

    Attributes:
        parameter: Name of the swept parameter (one of `PARAMETERS`).
        points: One `SweepPoint` per value tested, in the order supplied.
    """

    parameter: str
    points: list[SweepPoint] = field(default_factory=list)

    def values(self, metric: Callable[[RedesignDiff], float]) -> list[float]:
        """Return `metric(point.diff)` for every point, in sweep order."""
        return [metric(point.diff) for point in self.points]

    def break_even_range(
        self, metric: Callable[[RedesignDiff], float] = lambda diff: diff.roi.total_cost_savings
    ) -> tuple[float, float] | None:
        """Find the parameter range where `metric` crosses from positive to negative.

        Sweep points are assumed to be supplied in ascending or descending
        order of the swept parameter. Returns the `(lower, upper)` pair of
        adjacent swept values bracketing the first sign change, or `None`
        if the metric never changes sign across the sweep. Returns
        `(value, value)` if a point lands exactly on zero.
        """
        for previous, current in zip(self.points, self.points[1:], strict=False):
            previous_value = metric(previous.diff)
            current_value = metric(current.diff)
            if previous_value == 0:
                return (previous.value, previous.value)
            if (previous_value > 0) != (current_value > 0):
                lower = min(previous.value, current.value)
                upper = max(previous.value, current.value)
                return (lower, upper)
        if self.points and metric(self.points[-1].diff) == 0:
            return (self.points[-1].value, self.points[-1].value)
        return None


def set_actor_field(workflow: Workflow, actor_type: type, field_name: str, value: float) -> None:
    """Set `field_name = value` on every actor of `actor_type` in `workflow`."""
    for actor in workflow.actors.values():
        if isinstance(actor, actor_type):
            setattr(actor, field_name, value)


def run_sensitivity_sweep(
    build_before: Callable[[], Workflow],
    build_after: Callable[[], Workflow],
    parameter: str,
    values: Sequence[float],
    num_cases: int,
    seed: int | None = None,
    implementation_cost: float | None = None,
) -> SensitivityResult:
    """Re-simulate a before/after workflow pair while sweeping one parameter.

    Args:
        build_before: Zero-argument callable returning a fresh "before"
            `Workflow` (called once per sweep value, since simulation
            re-uses and mutates its inputs across a run).
        build_after: Zero-argument callable returning a fresh "after"
            `Workflow`.
        parameter: Which assumption to vary. One of:
            - "ai_error_rate": sets `error_rate` on every `AIAgentActor`
              in the after workflow.
            - "ai_cost_per_execution": sets `cost_per_execution` on every
              `AIAgentActor` in the after workflow.
            - "human_hourly_cost": sets `hourly_cost` on every
              `HumanActor` in both workflows.
            - "arrival_interval": passed as `arrival_interval_minutes` to
              the simulation runner for both workflows.
            - "implementation_cost": varies only the ROI calculation, not
              the simulation itself, so both workflows are simulated once
              and reused across every value for efficiency.
        values: Parameter values to test, in the order they should appear
            in the result (also the order used for break-even detection).
        num_cases: Number of cases to simulate per workflow per value.
        seed: Random seed applied to both the before and after runs at
            every value, so only the swept parameter drives the outcome.
        implementation_cost: Baseline implementation cost used for every
            value except when `parameter == "implementation_cost"`.

    Returns:
        A `SensitivityResult` with one point per value in `values`.
    """
    if parameter not in PARAMETERS:
        raise ValueError(
            f"Unknown sensitivity parameter: {parameter!r}. Expected one of {PARAMETERS}"
        )
    if not values:
        raise ValueError("values must contain at least one entry")
    if num_cases <= 0:
        raise ValueError("num_cases must be a positive integer")

    points: list[SweepPoint] = []
    cached_kpis: tuple | None = None

    for value in values:
        if parameter == "implementation_cost":
            if cached_kpis is None:
                before_kpi = SimulationRunner(seed=seed).run(build_before(), num_cases).kpi
                after_kpi = SimulationRunner(seed=seed).run(build_after(), num_cases).kpi
                cached_kpis = (before_kpi, after_kpi)
            before_kpi, after_kpi = cached_kpis
            diff = compare_workflows(before_kpi, after_kpi, implementation_cost=value)
            points.append(SweepPoint(value=value, diff=diff))
            continue

        before_workflow = copy.deepcopy(build_before())
        after_workflow = copy.deepcopy(build_after())
        arrival_interval_minutes = None

        if parameter == "ai_error_rate":
            set_actor_field(after_workflow, AIAgentActor, "error_rate", value)
        elif parameter == "ai_cost_per_execution":
            set_actor_field(after_workflow, AIAgentActor, "cost_per_execution", value)
        elif parameter == "human_hourly_cost":
            set_actor_field(before_workflow, HumanActor, "hourly_cost", value)
            set_actor_field(after_workflow, HumanActor, "hourly_cost", value)
        elif parameter == "arrival_interval":
            arrival_interval_minutes = value

        before_kpi = SimulationRunner(seed=seed).run(
            before_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
        ).kpi
        after_kpi = SimulationRunner(seed=seed).run(
            after_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
        ).kpi
        diff = compare_workflows(before_kpi, after_kpi, implementation_cost=implementation_cost)
        points.append(SweepPoint(value=value, diff=diff))

    return SensitivityResult(parameter=parameter, points=points)


def format_sensitivity_table(result: SensitivityResult) -> str:
    """Render a `SensitivityResult` as a plain-text table with a break-even summary."""
    header = f"{'Value':>12}{'Cost Savings':>18}{'ROI %':>10}{'Completion After':>18}"
    lines = [f"Sensitivity: {result.parameter}", header, "-" * len(header)]
    for point in result.points:
        roi = point.diff.roi.roi_percentage
        roi_str = f"{roi:+.1f}%" if roi is not None else "n/a"
        completion = f"{point.diff.completion_rate.after:.1%}"
        lines.append(
            f"{point.value:>12.4g}{point.diff.roi.total_cost_savings:>18,.2f}"
            f"{roi_str:>10}{completion:>18}"
        )

    break_even = result.break_even_range()
    lines.append("")
    if break_even is None:
        lines.append(
            "No break-even point found: cost savings do not change sign across this range."
        )
    elif break_even[0] == break_even[1]:
        lines.append(f"Break-even at {result.parameter} = {break_even[0]:.4g}.")
    else:
        lines.append(
            f"Break-even for cost savings occurs between {result.parameter} = "
            f"{break_even[0]:.4g} and {break_even[1]:.4g}."
        )
    return "\n".join(lines)


__all__ = [
    "PARAMETERS",
    "SweepPoint",
    "SensitivityResult",
    "run_sensitivity_sweep",
    "format_sensitivity_table",
    "set_actor_field",
]
