"""Team pools: model a group of interchangeable workers as one schedulable actor.

`ActorPool` extends the single-worker `HumanActor`/`AIAgentActor` model to
organizational teams: several `Worker`s who can each pick up work routed
to the pool, each with their own cost, speed, error rate, shift schedule,
and availability. `PoolScheduler` is the pool-aware counterpart to
`ActorScheduler`: instead of tracking one queue for a single resource, it
tracks one queue per worker and, for every task, routes it to whichever
available worker can start soonest ("least-loaded" routing), respecting
each worker's shift days/hours, any overtime capacity, and workers who
are currently marked unavailable.

An `ActorPool` is registered and referenced exactly like any other
`Actor` (`workflow.add_actor(pool)`, then `Node(..., actor_id=pool.actor_id)`);
the simulation engines detect pools via `isinstance` and delegate
scheduling to `PoolScheduler` instead of `ActorScheduler`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.actor import Actor
from b2b_workflow_simulator.primitives.shift import Shift
from b2b_workflow_simulator.primitives.worker import Worker

MINUTES_PER_DAY = 24 * 60


@dataclass
class ActorPool(Actor):
    """A team of interchangeable workers, scheduled as a single actor.

    Attributes:
        workers: The team's members. Must contain at least one `Worker`
            with a unique `worker_id`.
        available_hours_per_day (inherited): Fallback daily capacity, in
            hours, used for any worker that has no `Shift`s of their own.
    """

    workers: list[Worker] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.workers:
            raise ValueError("workers must contain at least one Worker")
        worker_ids = [worker.worker_id for worker in self.workers]
        if len(worker_ids) != len(set(worker_ids)):
            raise ValueError("worker_id values within a pool must be unique")

    @property
    def kind(self) -> str:
        return "actor_pool"

    def get_worker(self, worker_id: str) -> Worker:
        for worker in self.workers:
            if worker.worker_id == worker_id:
                return worker
        raise KeyError(f"pool '{self.actor_id}' has no worker '{worker_id}'")


@dataclass
class PoolScheduledTask:
    """The outcome of routing one task to a specific worker within a pool."""

    worker_id: str
    start: float
    end: float
    wait_minutes: float
    duration: float
    cost: float
    used_overtime: bool = False


@dataclass
class _WorkerState:
    free_at: float = 0.0
    current_day_index: int = 0
    minutes_used_today: float = 0.0
    total_busy_minutes: float = 0.0
    days_active: int = 0


def _shift_for_weekday(worker: Worker, weekday: int) -> Shift | None:
    for shift in worker.shifts:
        if shift.is_active_on(weekday):
            return shift
    return None


def _earliest_slot(
    worker: Worker,
    current_day_index: int,
    minutes_used_today: float,
    free_at: float,
    ready_time: float,
    duration: float,
    pool_default_hours: float,
) -> tuple[float, int, bool]:
    """Return `(start, day_index, used_overtime)` for a worker's next open slot.

    Pure function: does not mutate any scheduling state, so it is safe to
    call once per candidate worker while comparing options.
    """
    t = max(ready_time, free_at)
    day_index = int(t // MINUTES_PER_DAY)
    used_minutes_today = minutes_used_today if day_index == current_day_index else 0.0

    while True:
        weekday = day_index % 7
        if worker.shifts:
            shift = _shift_for_weekday(worker, weekday)
            if shift is None:
                day_index += 1
                t = day_index * MINUTES_PER_DAY
                used_minutes_today = 0.0
                continue
            window_start = day_index * MINUTES_PER_DAY + shift.start_hour * 60.0
            regular_capacity = shift.regular_hours * 60.0
            total_capacity = shift.hours_with_overtime * 60.0
        else:
            window_start = day_index * MINUTES_PER_DAY
            regular_capacity = pool_default_hours * 60.0
            total_capacity = regular_capacity

        candidate_start = max(t, window_start)
        remaining = total_capacity - used_minutes_today
        if duration > remaining:
            day_index += 1
            t = day_index * MINUTES_PER_DAY
            used_minutes_today = 0.0
            continue

        used_overtime = (used_minutes_today + duration) > regular_capacity
        return candidate_start, day_index, used_overtime


class PoolScheduler:
    """Tracks per-worker availability across every pool it is asked to schedule.

    Usage:
        scheduler = PoolScheduler()
        outcome = scheduler.schedule(pool, ready_time=120.0, sampled_base_duration=30.0)
    """

    def __init__(self) -> None:
        self._states: dict[tuple[str, str], _WorkerState] = {}

    def schedule(
        self, pool: ActorPool, ready_time: float, sampled_base_duration: float
    ) -> PoolScheduledTask:
        """Route one task to the pool's least-loaded available worker.

        `sampled_base_duration` is the node's duration before any
        per-worker speed adjustment; each candidate's actual duration is
        `sampled_base_duration * worker.speed_multiplier`.
        """
        candidates = [worker for worker in pool.workers if worker.available]
        if not candidates:
            raise ValueError(f"pool '{pool.actor_id}' has no available workers")

        best_rank: tuple[float, float, str] | None = None
        best: tuple[Worker, _WorkerState, float, float, int, bool] | None = None

        for worker in candidates:
            state = self._states.setdefault((pool.actor_id, worker.worker_id), _WorkerState())
            duration = sampled_base_duration * worker.speed_multiplier
            start, day_index, used_overtime = _earliest_slot(
                worker,
                state.current_day_index,
                state.minutes_used_today,
                state.free_at,
                ready_time,
                duration,
                pool.available_hours_per_day,
            )
            rank = (start, state.total_busy_minutes, worker.worker_id)
            if best_rank is None or rank < best_rank:
                best_rank = rank
                best = (worker, state, duration, start, day_index, used_overtime)

        assert best is not None
        worker, state, duration, start, day_index, used_overtime = best

        if day_index != state.current_day_index:
            state.current_day_index = day_index
            state.minutes_used_today = 0.0
        state.minutes_used_today += duration
        state.total_busy_minutes += duration
        state.free_at = start + duration
        state.days_active = max(state.days_active, day_index + 1)

        return PoolScheduledTask(
            worker_id=worker.worker_id,
            start=start,
            end=start + duration,
            wait_minutes=start - ready_time,
            duration=duration,
            cost=worker.cost_for_duration(duration),
            used_overtime=used_overtime,
        )

    def worker_busy_minutes(self, pool_id: str, worker_id: str) -> float:
        state = self._states.get((pool_id, worker_id))
        return state.total_busy_minutes if state else 0.0

    def worker_days_active(self, pool_id: str, worker_id: str) -> int:
        state = self._states.get((pool_id, worker_id))
        return state.days_active if state else 0

    def worker_utilization(self, pool: ActorPool, worker_id: str) -> float:
        """Busy time as a fraction of the worker's capacity across their active days."""
        state = self._states.get((pool.actor_id, worker_id))
        if state is None or state.days_active == 0:
            return 0.0
        worker = pool.get_worker(worker_id)
        hours_per_day = worker.shifts[0].regular_hours if worker.shifts else (
            pool.available_hours_per_day
        )
        capacity_minutes = hours_per_day * 60.0 * state.days_active
        if capacity_minutes <= 0:
            return 0.0
        return state.total_busy_minutes / capacity_minutes

    def pool_utilization(self, pool: ActorPool) -> float:
        """Busy time as a fraction of capacity, aggregated across every worker."""
        total_busy = 0.0
        total_capacity = 0.0
        for worker in pool.workers:
            state = self._states.get((pool.actor_id, worker.worker_id))
            if state is None or state.days_active == 0:
                continue
            hours_per_day = worker.shifts[0].regular_hours if worker.shifts else (
                pool.available_hours_per_day
            )
            total_busy += state.total_busy_minutes
            total_capacity += hours_per_day * 60.0 * state.days_active
        return total_busy / total_capacity if total_capacity > 0 else 0.0

    def known_worker_ids(self, pool_id: str) -> list[str]:
        return [worker_id for (pid, worker_id) in self._states if pid == pool_id]

    def known_pool_ids(self) -> list[str]:
        return sorted({pool_id for (pool_id, _worker_id) in self._states})


__all__ = ["ActorPool", "PoolScheduler", "PoolScheduledTask"]
