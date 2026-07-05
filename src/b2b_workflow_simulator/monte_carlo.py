"""Monte Carlo analysis: repeat a simulation across many seeds to expose variability.

A single seeded run answers "what happens under one plausible sequence of
random outcomes?" Real operations see a distribution of outcomes, not one
point estimate, so this module re-runs a workflow (or a before/after
comparison) once per seed in `seeds` and summarizes each metric's spread
with mean, minimum, maximum, median, P10 (a pessimistic-but-not-worst-case
bound), and P90 (an optimistic-but-not-best-case bound).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from b2b_workflow_simulator.arrivals import ArrivalModel
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow

KPI_METRICS = (
    "completion_rate",
    "avg_cycle_time_minutes",
    "avg_wait_time_minutes",
    "total_cost",
    "avg_cost_per_case",
)

COMPARISON_METRICS = (
    "completion_rate_before",
    "completion_rate_after",
    "cycle_time_minutes_before",
    "cycle_time_minutes_after",
    "wait_time_minutes_before",
    "wait_time_minutes_after",
    "cost_per_case_before",
    "cost_per_case_after",
    "total_cost_savings",
    "roi_percentage",
    "cost_savings_per_case",
    "payback_in_cases",
)


@dataclass(frozen=True)
class MetricStats:
    """Summary statistics for one metric observed across Monte Carlo runs.

    Attributes:
        sample_count: How many runs contributed a value for this metric
            (may be less than the total number of runs for metrics like
            `payback_in_cases` that are undefined in some runs).
        mean, minimum, maximum, median: Standard summary statistics.
        p10: The 10th percentile -- 90% of runs performed at least this
            well, a reasonable "plan for this" pessimistic bound.
        p90: The 90th percentile -- an optimistic-but-plausible bound.
        std_dev: Sample standard deviation; zero when fewer than two
            values were observed.
    """

    sample_count: int
    mean: float
    minimum: float
    maximum: float
    median: float
    p10: float
    p90: float
    std_dev: float

    @property
    def spread(self) -> float:
        """Width of the P10-P90 band, a compact measure of variability."""
        return self.p90 - self.p10


def _percentile(sorted_values: Sequence[float], percentile: float) -> float:
    """Linear-interpolated percentile of an already-sorted sequence."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * (percentile / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_values[int(rank)]
    lower_weight = sorted_values[lower] * (upper - rank)
    upper_weight = sorted_values[upper] * (rank - lower)
    return lower_weight + upper_weight


def compute_metric_stats(values: Sequence[float]) -> MetricStats:
    """Compute `MetricStats` over `values`. Returns all-zero stats if empty."""
    if not values:
        return MetricStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    ordered = sorted(values)
    return MetricStats(
        sample_count=len(ordered),
        mean=statistics.fmean(ordered),
        minimum=ordered[0],
        maximum=ordered[-1],
        median=statistics.median(ordered),
        p10=_percentile(ordered, 10.0),
        p90=_percentile(ordered, 90.0),
        std_dev=statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
    )


@dataclass
class MonteCarloResult:
    """Aggregated outcome of running one workflow across many seeds."""

    workflow_name: str
    num_runs: int
    seeds: list[int] = field(default_factory=list)
    metric_stats: dict[str, MetricStats] = field(default_factory=dict)


@dataclass
class MonteCarloComparisonResult:
    """Aggregated outcome of comparing a before/after workflow pair across many seeds."""

    before_name: str
    after_name: str
    num_runs: int
    seeds: list[int] = field(default_factory=list)
    metric_stats: dict[str, MetricStats] = field(default_factory=dict)


def _run_kpi(
    build_workflow: Callable[[], Workflow],
    seed: int,
    num_cases: int,
    arrival_interval_minutes: float | None,
    arrival_model: ArrivalModel | None,
    engine: str,
):
    workflow = build_workflow()
    result = SimulationRunner(seed=seed).run(
        workflow,
        num_cases,
        arrival_interval_minutes=arrival_interval_minutes,
        arrival_model=arrival_model,
        engine=engine,
    )
    return workflow.name, result.kpi


def run_monte_carlo(
    build_workflow: Callable[[], Workflow],
    num_cases: int,
    seeds: Sequence[int],
    arrival_interval_minutes: float | None = None,
    arrival_model: ArrivalModel | None = None,
    engine: str = "simple",
) -> MonteCarloResult:
    """Simulate `build_workflow()` once per seed and summarize KPI variability.

    Args:
        build_workflow: Zero-argument callable returning a fresh `Workflow`
            (called once per seed).
        num_cases: Number of cases to simulate per run.
        seeds: Random seeds to run; one simulation per seed.
        arrival_interval_minutes: Optional fixed arrival spacing, applied
            identically to every run.
        arrival_model: Optional richer arrival pattern, applied
            identically to every run. Mutually exclusive with
            `arrival_interval_minutes`.
        engine: Simulation engine to use for every run ("simple" or
            "discrete").

    Returns:
        A `MonteCarloResult` with one `MetricStats` per entry in
        `KPI_METRICS`.
    """
    if not seeds:
        raise ValueError("seeds must contain at least one seed")
    if num_cases <= 0:
        raise ValueError("num_cases must be a positive integer")

    samples: dict[str, list[float]] = {metric: [] for metric in KPI_METRICS}
    workflow_name = ""
    for seed in seeds:
        workflow_name, kpi = _run_kpi(
            build_workflow, seed, num_cases, arrival_interval_minutes, arrival_model, engine
        )
        samples["completion_rate"].append(kpi.completion_rate)
        samples["avg_cycle_time_minutes"].append(kpi.avg_cycle_time_minutes)
        samples["avg_wait_time_minutes"].append(kpi.avg_wait_time_minutes)
        samples["total_cost"].append(kpi.total_cost)
        samples["avg_cost_per_case"].append(kpi.avg_cost_per_case)

    return MonteCarloResult(
        workflow_name=workflow_name,
        num_runs=len(seeds),
        seeds=list(seeds),
        metric_stats={name: compute_metric_stats(values) for name, values in samples.items()},
    )


def run_monte_carlo_comparison(
    build_before: Callable[[], Workflow],
    build_after: Callable[[], Workflow],
    num_cases: int,
    seeds: Sequence[int],
    arrival_interval_minutes: float | None = None,
    arrival_model: ArrivalModel | None = None,
    implementation_cost: float | None = None,
    engine: str = "simple",
) -> MonteCarloComparisonResult:
    """Simulate a before/after workflow pair once per seed and summarize ROI variability.

    Each seed drives both the "before" and "after" simulation, so results
    stay comparable within a run while varying across seeds. Arguments
    mirror `run_monte_carlo`; `implementation_cost` is applied identically
    to every run's ROI calculation.
    """
    if not seeds:
        raise ValueError("seeds must contain at least one seed")
    if num_cases <= 0:
        raise ValueError("num_cases must be a positive integer")

    samples: dict[str, list[float]] = {metric: [] for metric in COMPARISON_METRICS}
    before_name = after_name = ""

    for seed in seeds:
        before_name, before_kpi = _run_kpi(
            build_before, seed, num_cases, arrival_interval_minutes, arrival_model, engine
        )
        after_name, after_kpi = _run_kpi(
            build_after, seed, num_cases, arrival_interval_minutes, arrival_model, engine
        )
        diff = compare_workflows(before_kpi, after_kpi, implementation_cost)

        samples["completion_rate_before"].append(diff.completion_rate.before)
        samples["completion_rate_after"].append(diff.completion_rate.after)
        samples["cycle_time_minutes_before"].append(diff.cycle_time_minutes.before)
        samples["cycle_time_minutes_after"].append(diff.cycle_time_minutes.after)
        samples["wait_time_minutes_before"].append(diff.wait_time_minutes.before)
        samples["wait_time_minutes_after"].append(diff.wait_time_minutes.after)
        samples["cost_per_case_before"].append(diff.cost_per_case.before)
        samples["cost_per_case_after"].append(diff.cost_per_case.after)
        samples["total_cost_savings"].append(diff.roi.total_cost_savings)
        samples["cost_savings_per_case"].append(diff.roi.cost_savings_per_case)
        if diff.roi.roi_percentage is not None:
            samples["roi_percentage"].append(diff.roi.roi_percentage)
        if diff.roi.payback_feasible and diff.roi.payback_in_cases is not None:
            samples["payback_in_cases"].append(diff.roi.payback_in_cases)

    return MonteCarloComparisonResult(
        before_name=before_name,
        after_name=after_name,
        num_runs=len(seeds),
        seeds=list(seeds),
        metric_stats={name: compute_metric_stats(values) for name, values in samples.items()},
    )


__all__ = [
    "KPI_METRICS",
    "COMPARISON_METRICS",
    "MetricStats",
    "MonteCarloResult",
    "MonteCarloComparisonResult",
    "compute_metric_stats",
    "run_monte_carlo",
    "run_monte_carlo_comparison",
]
