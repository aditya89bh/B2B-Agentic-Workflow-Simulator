"""Capacity planning: turn simulated utilization into staffing guidance.

Utilization percentages alone don't tell an operations leader what to do.
This module converts `KPIResult` utilization data into concrete headcount
recommendations against a target utilization band, flags actors and
pools that are overloaded or underutilized, and lets a planner simulate
the effect of hiring additional workers into a team pool before
committing to it.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from b2b_workflow_simulator.arrivals import ArrivalModel
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.primitives.worker import Worker
from b2b_workflow_simulator.queueing import analyze_queue_behavior
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow

DEFAULT_TARGET_UTILIZATION = 0.75
DEFAULT_OVERLOAD_THRESHOLD = 0.90
DEFAULT_UNDERUTILIZATION_THRESHOLD = 0.40

OVERLOADED = "overloaded"
UNDERUTILIZED = "underutilized"
BALANCED = "balanced"


def _status(
    utilization: float, overload_threshold: float, underutilization_threshold: float
) -> str:
    if utilization >= overload_threshold:
        return OVERLOADED
    if utilization <= underutilization_threshold:
        return UNDERUTILIZED
    return BALANCED


def _recommended_headcount(current: int, utilization: float, target_utilization: float) -> int:
    """Headcount that would bring `utilization` to `target_utilization`, given `current`.

    Rounds up when adding capacity (never under-provisions an overloaded
    resource) and rounds down when reducing it (never over-cuts an
    underutilized one), always keeping at least one worker.
    """
    if target_utilization <= 0 or current <= 0:
        return max(1, current)
    ideal = current * utilization / target_utilization
    if utilization > target_utilization:
        return max(current, math.ceil(ideal))
    return max(1, math.floor(ideal))


@dataclass(frozen=True)
class StaffingRecommendation:
    """A staffing suggestion for one actor or pool, derived from simulated utilization.

    Attributes:
        resource_id: The actor_id (single actor) or pool actor_id.
        resource_kind: "actor" for a single-worker `HumanActor`/`AIAgentActor`,
            "pool" for an `ActorPool`.
        current_headcount: Number of workers currently assigned (always 1
            for a single actor).
        current_utilization: Simulated utilization fraction (0.0-1.0+).
        status: One of `OVERLOADED`, `UNDERUTILIZED`, or `BALANCED`.
        recommended_headcount: Headcount that would bring utilization to
            the plan's target.
        rationale: Human-readable explanation of the recommendation.
    """

    resource_id: str
    resource_kind: str
    current_headcount: int
    current_utilization: float
    status: str
    recommended_headcount: int
    rationale: str

    @property
    def headcount_delta(self) -> int:
        """Positive means hire, negative means reduce, zero means no change."""
        return self.recommended_headcount - self.current_headcount


def _rationale(
    resource_id: str,
    resource_kind: str,
    utilization: float,
    status: str,
    current: int,
    recommended: int,
    target: float,
) -> str:
    label = "pool" if resource_kind == "pool" else "actor"
    if status == OVERLOADED:
        return (
            f"{label.capitalize()} '{resource_id}' is running at {utilization:.1%} "
            f"utilization, above a healthy target of {target:.0%}. Consider staffing up "
            f"from {current} to {recommended} worker(s) to relieve pressure."
        )
    if status == UNDERUTILIZED:
        return (
            f"{label.capitalize()} '{resource_id}' is running at {utilization:.1%} "
            f"utilization, below a healthy floor near {target:.0%}. Consider reducing "
            f"from {current} to {recommended} worker(s) or reallocating idle capacity."
        )
    return (
        f"{label.capitalize()} '{resource_id}' is running at {utilization:.1%} "
        f"utilization, close to the {target:.0%} target. No staffing change recommended."
    )


@dataclass
class CapacityPlan:
    """A full set of staffing recommendations for one simulated workflow."""

    workflow_name: str
    target_utilization: float
    recommendations: list[StaffingRecommendation] = field(default_factory=list)

    @property
    def overloaded(self) -> list[StaffingRecommendation]:
        return [rec for rec in self.recommendations if rec.status == OVERLOADED]

    @property
    def underutilized(self) -> list[StaffingRecommendation]:
        return [rec for rec in self.recommendations if rec.status == UNDERUTILIZED]

    @property
    def balanced(self) -> list[StaffingRecommendation]:
        return [rec for rec in self.recommendations if rec.status == BALANCED]


def analyze_capacity(
    kpi: KPIResult,
    pool_sizes: dict[str, int] | None = None,
    target_utilization: float = DEFAULT_TARGET_UTILIZATION,
    overload_threshold: float = DEFAULT_OVERLOAD_THRESHOLD,
    underutilization_threshold: float = DEFAULT_UNDERUTILIZATION_THRESHOLD,
) -> CapacityPlan:
    """Build a `CapacityPlan` from a simulated `KPIResult`.

    Args:
        kpi: A `KPIResult` from a capacity-aware run (i.e. simulated with
            `arrival_interval_minutes` or `arrival_model` set), so
            `actor_utilization` / `pool_utilization` are populated.
        pool_sizes: Current worker count for each pool actor_id, used to
            translate utilization into headcount recommendations. If
            omitted, the count of workers observed in
            `kpi.worker_utilization` is used instead.
        target_utilization: Desired steady-state utilization (e.g. 0.75
            means "busy 75% of available capacity").
        overload_threshold: Utilization at or above which a resource is
            flagged as overloaded.
        underutilization_threshold: Utilization at or below which a
            resource is flagged as underutilized.

    Returns:
        A `CapacityPlan` with one `StaffingRecommendation` per actor and
        pool that reported utilization.
    """
    pool_sizes = pool_sizes or {}
    recommendations: list[StaffingRecommendation] = []

    for actor_id, utilization in kpi.actor_utilization.items():
        current = 1
        recommended = _recommended_headcount(current, utilization, target_utilization)
        status = _status(utilization, overload_threshold, underutilization_threshold)
        recommendations.append(
            StaffingRecommendation(
                resource_id=actor_id,
                resource_kind="actor",
                current_headcount=current,
                current_utilization=utilization,
                status=status,
                recommended_headcount=recommended,
                rationale=_rationale(
                    actor_id, "actor", utilization, status, current, recommended, target_utilization
                ),
            )
        )

    for pool_id, utilization in kpi.pool_utilization.items():
        current = pool_sizes.get(pool_id) or len(kpi.worker_utilization.get(pool_id, {})) or 1
        recommended = _recommended_headcount(current, utilization, target_utilization)
        status = _status(utilization, overload_threshold, underutilization_threshold)
        recommendations.append(
            StaffingRecommendation(
                resource_id=pool_id,
                resource_kind="pool",
                current_headcount=current,
                current_utilization=utilization,
                status=status,
                recommended_headcount=recommended,
                rationale=_rationale(
                    pool_id, "pool", utilization, status, current, recommended, target_utilization
                ),
            )
        )

    return CapacityPlan(
        workflow_name=kpi.workflow_name,
        target_utilization=target_utilization,
        recommendations=recommendations,
    )


@dataclass(frozen=True)
class HiringSimulationResult:
    """Before/after comparison of simulating additional hires into a pool."""

    workflow_name: str
    pool_id: str
    baseline_worker_count: int
    proposed_worker_count: int
    baseline_utilization: float
    proposed_utilization: float
    baseline_max_queue_depth: int
    proposed_max_queue_depth: int
    baseline_avg_wait_minutes: float
    proposed_avg_wait_minutes: float

    @property
    def utilization_change(self) -> float:
        return self.proposed_utilization - self.baseline_utilization

    @property
    def queue_depth_change(self) -> int:
        return self.proposed_max_queue_depth - self.baseline_max_queue_depth

    @property
    def wait_time_change_minutes(self) -> float:
        return self.proposed_avg_wait_minutes - self.baseline_avg_wait_minutes


def simulate_hiring(
    build_workflow: Callable[[], Workflow],
    pool_actor_id: str,
    additional_workers: list[Worker],
    num_cases: int,
    seed: int | None = None,
    arrival_interval_minutes: float | None = None,
    arrival_model: ArrivalModel | None = None,
    engine: str = "simple",
) -> HiringSimulationResult:
    """Simulate the effect of hiring `additional_workers` into a pool.

    Runs `build_workflow()` twice with the same seed and arrival
    pattern: once as-is (the baseline) and once with `additional_workers`
    appended to the pool identified by `pool_actor_id`. Comparing the two
    results shows whether the hire would meaningfully relieve queueing
    and utilization pressure before committing to it.

    Args:
        build_workflow: Zero-argument callable returning a fresh
            `Workflow` containing an `ActorPool` with actor_id
            `pool_actor_id`.
        pool_actor_id: The pool to add workers to.
        additional_workers: One or more `Worker`s to add to the pool in
            the proposed scenario.
        num_cases, seed, arrival_interval_minutes, arrival_model, engine:
            Passed through to `SimulationRunner.run` for both scenarios.

    Returns:
        A `HiringSimulationResult` comparing utilization, queue depth,
        and wait time before and after the hire.
    """
    if not additional_workers:
        raise ValueError("additional_workers must contain at least one Worker")

    baseline_workflow = build_workflow()
    baseline_pool = baseline_workflow.get_actor(pool_actor_id)
    if not isinstance(baseline_pool, ActorPool):
        raise TypeError(f"actor '{pool_actor_id}' is not an ActorPool")

    baseline_result = SimulationRunner(seed=seed).run(
        baseline_workflow,
        num_cases,
        arrival_interval_minutes=arrival_interval_minutes,
        arrival_model=arrival_model,
        engine=engine,
    )
    baseline_queue = analyze_queue_behavior(baseline_result)

    proposed_workflow = build_workflow()
    proposed_pool = proposed_workflow.get_actor(pool_actor_id)
    proposed_pool.workers.extend(additional_workers)

    proposed_result = SimulationRunner(seed=seed).run(
        proposed_workflow,
        num_cases,
        arrival_interval_minutes=arrival_interval_minutes,
        arrival_model=arrival_model,
        engine=engine,
    )
    proposed_queue = analyze_queue_behavior(proposed_result)

    return HiringSimulationResult(
        workflow_name=baseline_workflow.name,
        pool_id=pool_actor_id,
        baseline_worker_count=len(baseline_pool.workers),
        proposed_worker_count=len(proposed_pool.workers),
        baseline_utilization=baseline_result.kpi.pool_utilization.get(pool_actor_id, 0.0),
        proposed_utilization=proposed_result.kpi.pool_utilization.get(pool_actor_id, 0.0),
        baseline_max_queue_depth=max(baseline_queue.max_queue_depth.values(), default=0),
        proposed_max_queue_depth=max(proposed_queue.max_queue_depth.values(), default=0),
        baseline_avg_wait_minutes=baseline_result.kpi.avg_wait_time_minutes,
        proposed_avg_wait_minutes=proposed_result.kpi.avg_wait_time_minutes,
    )


__all__ = [
    "DEFAULT_TARGET_UTILIZATION",
    "DEFAULT_OVERLOAD_THRESHOLD",
    "DEFAULT_UNDERUTILIZATION_THRESHOLD",
    "OVERLOADED",
    "UNDERUTILIZED",
    "BALANCED",
    "StaffingRecommendation",
    "CapacityPlan",
    "analyze_capacity",
    "HiringSimulationResult",
    "simulate_hiring",
]
