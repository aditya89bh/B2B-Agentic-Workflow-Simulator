"""Multi-parameter sensitivity analysis: sweep two assumptions at once over a grid.

`sensitivity.py` answers "what happens as this one assumption changes?".
Real redesign decisions usually depend on two assumptions moving
together -- e.g. AI cost and AI error rate both drift as a vendor
matures, or arrival volume grows while implementation cost is being
negotiated. This module re-simulates a before/after workflow pair once
per (x, y) combination in a grid and classifies the resulting ROI
surface into safe, negative, and unstable operating regions.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.redesign import RedesignDiff, compare_workflows
from b2b_workflow_simulator.sensitivity import PARAMETERS, set_actor_field
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow

UNSTABLE_COMPLETION_RATE_THRESHOLD = 0.5


@dataclass(frozen=True)
class GridPoint:
    """One simulated outcome at a single (x, y) combination of swept parameters."""

    x_value: float
    y_value: float
    diff: RedesignDiff


@dataclass
class SensitivityGridResult:
    """The full output of a two-parameter sensitivity sweep.

    Attributes:
        x_parameter: Name of the parameter swept along the x-axis (one of
            `PARAMETERS`).
        y_parameter: Name of the parameter swept along the y-axis.
        x_values: Values tested along the x-axis, in order.
        y_values: Values tested along the y-axis, in order.
        points: One `GridPoint` per (x, y) combination, in row-major order
            (all x values for the first y, then all x values for the
            second y, and so on).
    """

    x_parameter: str
    y_parameter: str
    x_values: list[float] = field(default_factory=list)
    y_values: list[float] = field(default_factory=list)
    points: list[GridPoint] = field(default_factory=list)

    def point_at(self, x_value: float, y_value: float) -> GridPoint:
        """Look up the `GridPoint` for an exact (x, y) combination."""
        for point in self.points:
            if point.x_value == x_value and point.y_value == y_value:
                return point
        raise KeyError(f"No grid point at x={x_value!r}, y={y_value!r}")

    def matrix(self, metric: Callable[[RedesignDiff], float]) -> list[list[float]]:
        """Build a `metric(point.diff)` matrix, one row per y value, one column per x value."""
        rows = []
        for y_value in self.y_values:
            row = [self.point_at(x_value, y_value).diff for x_value in self.x_values]
            rows.append([metric(diff) for diff in row])
        return rows

    def roi_matrix(self) -> list[list[float | None]]:
        """ROI percentage matrix (rows: y_values, columns: x_values)."""
        return [
            [self.point_at(x, y).diff.roi.roi_percentage for x in self.x_values]
            for y in self.y_values
        ]

    def classify_region(self, x_value: float, y_value: float) -> str:
        """Classify a grid point as "safe", "negative", or "unstable".

        - "unstable": completion rate after the redesign falls below
          `UNSTABLE_COMPLETION_RATE_THRESHOLD`, meaning the redesign
          breaks down operationally regardless of cost.
        - "negative": ROI is defined and non-positive (or cost savings
          are non-positive when ROI is undefined).
        - "safe": positive ROI (or positive cost savings) with an
          operationally sound completion rate.
        """
        diff = self.point_at(x_value, y_value).diff
        if diff.completion_rate.after < UNSTABLE_COMPLETION_RATE_THRESHOLD:
            return "unstable"
        if diff.roi.roi_percentage is not None:
            return "safe" if diff.roi.roi_percentage > 0 else "negative"
        return "safe" if diff.roi.total_cost_savings > 0 else "negative"

    def region_map(self) -> list[list[str]]:
        """Region classification for every grid point, rows: y_values, columns: x_values."""
        return [
            [self.classify_region(x, y) for x in self.x_values] for y in self.y_values
        ]

    def safe_region_points(self) -> list[GridPoint]:
        """All grid points classified as "safe"."""
        return [
            point
            for point in self.points
            if self.classify_region(point.x_value, point.y_value) == "safe"
        ]

    def negative_region_points(self) -> list[GridPoint]:
        """All grid points classified as "negative"."""
        return [
            point
            for point in self.points
            if self.classify_region(point.x_value, point.y_value) == "negative"
        ]

    def unstable_region_points(self) -> list[GridPoint]:
        """All grid points classified as "unstable"."""
        return [
            point
            for point in self.points
            if self.classify_region(point.x_value, point.y_value) == "unstable"
        ]


def _apply_parameter(
    parameter: str,
    value: float,
    before_workflow: Workflow,
    after_workflow: Workflow,
) -> float | None:
    """Apply `value` for `parameter` to the workflows; returns an arrival interval override."""
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
    return arrival_interval_minutes


def run_sensitivity_grid(
    build_before: Callable[[], Workflow],
    build_after: Callable[[], Workflow],
    x_parameter: str,
    x_values: Sequence[float],
    y_parameter: str,
    y_values: Sequence[float],
    num_cases: int,
    seed: int | None = None,
    implementation_cost: float | None = None,
) -> SensitivityGridResult:
    """Re-simulate a before/after workflow pair over every (x, y) combination.

    Args:
        build_before: Zero-argument callable returning a fresh "before"
            `Workflow` (called once per grid cell).
        build_after: Zero-argument callable returning a fresh "after"
            `Workflow`.
        x_parameter: Parameter swept along the x-axis. See
            `sensitivity.run_sensitivity_sweep` for the meaning of each
            option in `PARAMETERS`.
        x_values: Values to test along the x-axis.
        y_parameter: Parameter swept along the y-axis. Must differ from
            `x_parameter`.
        y_values: Values to test along the y-axis.
        num_cases: Number of cases to simulate per workflow per grid cell.
        seed: Random seed applied to every simulation, so only the swept
            parameters drive outcome differences across the grid.
        implementation_cost: Baseline implementation cost used for the
            ROI calculation at every grid cell, unless one of the swept
            parameters is "implementation_cost".

    Returns:
        A `SensitivityGridResult` with one point per (x, y) combination.
    """
    if x_parameter not in PARAMETERS:
        raise ValueError(f"Unknown sensitivity parameter: {x_parameter!r}. Expected {PARAMETERS}")
    if y_parameter not in PARAMETERS:
        raise ValueError(f"Unknown sensitivity parameter: {y_parameter!r}. Expected {PARAMETERS}")
    if x_parameter == y_parameter:
        raise ValueError("x_parameter and y_parameter must differ")
    if not x_values:
        raise ValueError("x_values must contain at least one entry")
    if not y_values:
        raise ValueError("y_values must contain at least one entry")
    if num_cases <= 0:
        raise ValueError("num_cases must be a positive integer")

    points: list[GridPoint] = []
    for y_value in y_values:
        for x_value in x_values:
            before_workflow = build_before()
            after_workflow = build_after()

            arrival_interval_minutes = _apply_parameter(
                x_parameter, x_value, before_workflow, after_workflow
            )
            y_arrival_interval_minutes = _apply_parameter(
                y_parameter, y_value, before_workflow, after_workflow
            )
            if y_arrival_interval_minutes is not None:
                arrival_interval_minutes = y_arrival_interval_minutes

            cell_implementation_cost = implementation_cost
            if x_parameter == "implementation_cost":
                cell_implementation_cost = x_value
            elif y_parameter == "implementation_cost":
                cell_implementation_cost = y_value

            before_kpi = SimulationRunner(seed=seed).run(
                before_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
            ).kpi
            after_kpi = SimulationRunner(seed=seed).run(
                after_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
            ).kpi
            diff = compare_workflows(
                before_kpi, after_kpi, implementation_cost=cell_implementation_cost
            )
            points.append(GridPoint(x_value=x_value, y_value=y_value, diff=diff))

    return SensitivityGridResult(
        x_parameter=x_parameter,
        y_parameter=y_parameter,
        x_values=list(x_values),
        y_values=list(y_values),
        points=points,
    )


def _format_value(value: float) -> str:
    return f"{value:.4g}"


def _build_roi_table(result: SensitivityGridResult) -> list[str]:
    x_width = max(10, max(len(_format_value(x)) for x in result.x_values) + 2)
    corner_label = f"{result.y_parameter} / {result.x_parameter}"
    header = f"{corner_label:<22}" + "".join(
        f"{_format_value(x):>{x_width}}" for x in result.x_values
    )
    lines = [header, "-" * len(header)]
    for y_value in result.y_values:
        cells = []
        for x_value in result.x_values:
            roi = result.point_at(x_value, y_value).diff.roi.roi_percentage
            cells.append(f"{roi:+.1f}%" if roi is not None else "n/a")
        row = f"{_format_value(y_value):<22}" + "".join(f"{cell:>{x_width}}" for cell in cells)
        lines.append(row)
    return lines


def _build_region_summary(result: SensitivityGridResult) -> list[str]:
    total = len(result.points)
    safe = len(result.safe_region_points())
    negative = len(result.negative_region_points())
    unstable = len(result.unstable_region_points())
    return [
        f"Safe operating region:     {safe}/{total} combinations "
        f"({safe / total:.0%})" if total else "Safe operating region:     n/a",
        f"Negative ROI region:       {negative}/{total} combinations "
        f"({negative / total:.0%})" if total else "Negative ROI region:       n/a",
        f"Unstable region:           {unstable}/{total} combinations "
        f"({unstable / total:.0%})" if total else "Unstable region:           n/a",
    ]


def _build_boundary_notes(result: SensitivityGridResult) -> list[str]:
    lines = []
    unstable_points = result.unstable_region_points()
    if unstable_points:
        worst = min(unstable_points, key=lambda p: p.diff.completion_rate.after)
        lines.append(
            f"Operational breakdown observed at {result.x_parameter}="
            f"{_format_value(worst.x_value)}, {result.y_parameter}="
            f"{_format_value(worst.y_value)} (completion rate "
            f"{worst.diff.completion_rate.after:.1%}); avoid this combination."
        )
    negative_points = result.negative_region_points()
    if negative_points:
        lines.append(
            f"{len(negative_points)} combination(s) produce negative ROI; review the "
            "ROI table above to identify the boundary before committing to a rollout."
        )
    if not lines:
        lines.append("Every tested combination remains in the safe operating region.")
    return lines


def generate_sensitivity_grid_report(result: SensitivityGridResult) -> str:
    """Render a `SensitivityGridResult` as a plain-text ROI matrix with region analysis."""
    sections = [
        "=" * 60,
        "MULTI-PARAMETER SENSITIVITY ANALYSIS",
        "=" * 60,
        "",
        f"Grid: {result.x_parameter} (columns) x {result.y_parameter} (rows)",
        f"ROI %, {len(result.x_values)} x {len(result.y_values)} = "
        f"{len(result.points)} combinations simulated",
        "",
        "ROI MATRIX",
        "-" * 60,
        *_build_roi_table(result),
        "",
        "OPERATING REGIONS",
        "-" * 60,
        *_build_region_summary(result),
        "",
        "NOTES",
        "-" * 60,
        *[f"  - {note}" for note in _build_boundary_notes(result)],
    ]
    return "\n".join(sections)


__all__ = [
    "UNSTABLE_COMPLETION_RATE_THRESHOLD",
    "GridPoint",
    "SensitivityGridResult",
    "run_sensitivity_grid",
    "generate_sensitivity_grid_report",
]
