"""Capacity-aware scheduling: models actors as single-server queues with daily limits.

Each actor is treated as a resource that can only work on one task at a
time and only for `available_hours_per_day` hours within any given
calendar day (a fixed 1,440-minute window). When a task arrives while the
actor is busy, or would push the actor past its daily capacity, the task
waits -- either for the actor to finish its current work, or until the
start of the next day. This is a deliberately simple model (a FIFO
single-server queue per actor, no cross-day carryover of partial tasks)
chosen to keep the simulator's queueing behavior easy to reason about
and stdlib-only.
"""

from __future__ import annotations

from dataclasses import dataclass

MINUTES_PER_DAY = 24 * 60


@dataclass
class _ActorState:
    """Mutable scheduling state tracked for a single actor across a run."""

    free_at: float = 0.0
    current_day_index: int = 0
    minutes_used_today: float = 0.0
    total_busy_minutes: float = 0.0
    days_active: int = 1


@dataclass
class ScheduledTask:
    """The outcome of scheduling one task against an actor's capacity."""

    start: float
    wait_minutes: float
    end: float


class ActorScheduler:
    """Tracks per-actor availability and enforces daily capacity limits.

    Usage:
        scheduler = ActorScheduler()
        result = scheduler.schedule("ae", ready_time=120.0, duration=30.0,
                                     available_hours_per_day=8.0)
    """

    def __init__(self) -> None:
        self._states: dict[str, _ActorState] = {}

    def schedule(
        self,
        actor_id: str,
        ready_time: float,
        duration: float,
        available_hours_per_day: float,
    ) -> ScheduledTask:
        """Reserve `duration` minutes of `actor_id`'s time no earlier than `ready_time`.

        Returns the actual start time, how long the task waited before
        starting, and when it finished. Updates the actor's internal
        state so subsequent calls see this task's effect on availability.
        """
        state = self._states.setdefault(actor_id, _ActorState())
        available_minutes_per_day = available_hours_per_day * 60.0

        start = max(ready_time, state.free_at)
        day_index = int(start // MINUTES_PER_DAY)
        if day_index != state.current_day_index:
            state.current_day_index = day_index
            state.minutes_used_today = 0.0

        if state.minutes_used_today + duration > available_minutes_per_day:
            day_index += 1
            start = day_index * MINUTES_PER_DAY
            state.current_day_index = day_index
            state.minutes_used_today = 0.0

        state.minutes_used_today += duration
        state.total_busy_minutes += duration
        state.free_at = start + duration
        state.days_active = max(state.days_active, day_index + 1)

        wait_minutes = start - ready_time
        return ScheduledTask(start=start, wait_minutes=wait_minutes, end=start + duration)

    def peek_free_at(self, actor_id: str) -> float:
        """Return when `actor_id` next becomes free, without reserving any time.

        Returns 0.0 for an actor that has not been scheduled yet. Used by
        multi-resource task scheduling to find the earliest time every
        required actor could start together before committing any of
        their reservations.
        """
        state = self._states.get(actor_id)
        return state.free_at if state else 0.0

    def utilization(self, actor_id: str, available_hours_per_day: float) -> float:
        """Return busy time as a fraction of total capacity across active days.

        Capacity is `available_hours_per_day` multiplied by the number of
        distinct calendar days this actor did any work during the run.
        Returns 0.0 for actors that never received work.
        """
        state = self._states.get(actor_id)
        if state is None:
            return 0.0
        total_capacity_minutes = available_hours_per_day * 60.0 * state.days_active
        if total_capacity_minutes <= 0:
            return 0.0
        return state.total_busy_minutes / total_capacity_minutes

    def busy_minutes(self, actor_id: str) -> float:
        state = self._states.get(actor_id)
        return state.total_busy_minutes if state else 0.0

    def days_active(self, actor_id: str) -> int:
        state = self._states.get(actor_id)
        return state.days_active if state else 0

    def known_actor_ids(self) -> list[str]:
        return list(self._states)


__all__ = ["ActorScheduler", "ScheduledTask", "MINUTES_PER_DAY"]
