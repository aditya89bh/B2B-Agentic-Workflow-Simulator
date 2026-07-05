"""Multi-resource task scheduling: tasks that need several actors at once.

Most workflow steps need exactly one actor. Some do not: a contract needs
a Manager *and* Legal to sign off together, an AI agent's draft needs a
Human Reviewer before it goes out, a large payment needs Finance *and*
Procurement in the same review. `schedule_multi_resource_execution`
coordinates these cases by finding the earliest time every required
actor (or pool) can start together, then reserving that slot on each of
their calendars.

The additional wait this synchronization introduces beyond what any
single participant would have experienced alone is reported as
`coordination_delay_minutes`, so reports can distinguish ordinary queueing
from the extra cost of needing multiple resources in the same room.
"""

from __future__ import annotations

from dataclasses import dataclass

from b2b_workflow_simulator.capacity import ActorScheduler
from b2b_workflow_simulator.pool import ActorPool, PoolScheduler
from b2b_workflow_simulator.primitives.actor import Actor
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor


@dataclass(frozen=True)
class MultiResourceScheduledExecution:
    """The outcome of scheduling one task against every required actor.

    `duration` and `end` reflect the primary actor's (first in
    `participant_actor_ids`) execution time, matching the semantics of
    single-actor `ScheduledExecution`. Every participant's own calendar is
    still reserved for their own (possibly different) duration; only the
    primary actor's outcome determines the task's visible timing, cost
    contribution beyond the sum, and failure/escalation behavior.
    """

    start: float
    end: float
    wait_minutes: float
    duration: float
    cost: float
    error_rate: float
    escalation_rate: float
    checks_escalation: bool
    worker_id: str | None
    coordination_delay_minutes: float
    participant_actor_ids: tuple[str, ...]


def _peek_ready_time(
    actor: Actor,
    ready_time: float,
    sampled_base_duration: float,
    scheduler: ActorScheduler | None,
    pool_scheduler: PoolScheduler,
) -> float:
    if isinstance(actor, ActorPool):
        return pool_scheduler.peek_earliest_start(actor, ready_time, sampled_base_duration)
    if scheduler is not None:
        return max(ready_time, scheduler.peek_free_at(actor.actor_id))
    return ready_time


def schedule_multi_resource_execution(
    actors: list[Actor],
    sampled_base_duration: float,
    ready_time: float,
    scheduler: ActorScheduler | None,
    pool_scheduler: PoolScheduler,
) -> MultiResourceScheduledExecution:
    """Resolve timing, cost, and outcome rates for a task needing several actors.

    `actors[0]` is the primary actor (matches `Node.actor_id`); the rest
    are the node's `additional_actor_ids`, resolved to `Actor` instances.
    All participants are synchronized to start together: the joint start
    time is the latest of every participant's earliest availability, so
    no participant is double-booked.
    """
    if not actors:
        raise ValueError("actors must contain at least the primary actor")

    peeked_times = [
        _peek_ready_time(actor, ready_time, sampled_base_duration, scheduler, pool_scheduler)
        for actor in actors
    ]
    joint_ready = max(peeked_times)
    fastest_available = min(peeked_times)

    starts: list[float] = []
    total_cost = 0.0
    primary_worker_id: str | None = None
    primary_error_rate = 0.0
    primary_escalation_rate = 0.0
    primary_checks_escalation = False
    primary_duration = sampled_base_duration

    for index, actor in enumerate(actors):
        is_primary = index == 0
        if isinstance(actor, ActorPool):
            scheduled = pool_scheduler.schedule(actor, joint_ready, sampled_base_duration)
            starts.append(scheduled.start)
            total_cost += scheduled.cost
            if is_primary:
                worker = actor.get_worker(scheduled.worker_id)
                primary_worker_id = scheduled.worker_id
                primary_error_rate = worker.error_rate
                primary_duration = scheduled.duration
        else:
            duration = sampled_base_duration * actor.speed_multiplier
            if scheduler is not None:
                scheduled_task = scheduler.schedule(
                    actor.actor_id, joint_ready, duration, actor.available_hours_per_day
                )
                starts.append(scheduled_task.start)
            else:
                starts.append(joint_ready)
            total_cost += actor.cost_for_duration(duration)
            if is_primary:
                is_ai_agent = isinstance(actor, AIAgentActor)
                primary_error_rate = actor.error_rate
                primary_escalation_rate = actor.escalation_rate if is_ai_agent else 0.0
                primary_checks_escalation = is_ai_agent
                primary_duration = duration

    final_start = max(starts)
    final_end = final_start + primary_duration
    coordination_delay = final_start - fastest_available

    return MultiResourceScheduledExecution(
        start=final_start,
        end=final_end,
        wait_minutes=final_start - ready_time,
        duration=primary_duration,
        cost=total_cost,
        error_rate=primary_error_rate,
        escalation_rate=primary_escalation_rate,
        checks_escalation=primary_checks_escalation,
        worker_id=primary_worker_id,
        coordination_delay_minutes=max(0.0, coordination_delay),
        participant_actor_ids=tuple(actor.actor_id for actor in actors),
    )


__all__ = ["MultiResourceScheduledExecution", "schedule_multi_resource_execution"]
