"""Discrete-event simulation engine: chronologically-ordered alternative to the simple engine.

`SimulationRunner` (see `simulation.py`) resolves each case sequentially,
start to finish, before moving on to the next case. That is fast and
correct when cases do not contend for the same actors, but it is an
approximation once multiple cases share actors: a case that arrived later
but happens to be processed first in the loop can "cut in line" ahead of
a case that arrived earlier, because the loop order is case order, not
event-time order.

This module implements a genuine discrete-event engine instead: a single
global priority queue of events (arrivals and task completions) drives
the simulation, so work is always resolved in true chronological order
across every case at once. Each actor's capacity is still enforced by the
same `ActorScheduler` used by the simple engine, so daily-capacity
behavior is identical between engines; only the order in which
contending cases reach a shared actor can differ, which is exactly the
extra fidelity this engine exists to provide.

Event kinds on the internal queue:
    arrival: a case becomes ready to start its entry node.
    task_complete: a case finishes the task it was running, triggering
        outcome recording, a resource release, and (if not terminal or
        failed) an attempt to start the next node.

Every task start, queueing wait, and resource release is also recorded
in the returned `SimulationResult.events` log (see `EventType`), so
downstream analysis (queue depth, idle time, throughput) works the same
way regardless of which engine produced the result.
"""

from __future__ import annotations

import heapq
import itertools
import random
from dataclasses import dataclass
from typing import Any

from b2b_workflow_simulator.arrivals import ArrivalModel
from b2b_workflow_simulator.capacity import ActorScheduler
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.pool import PoolScheduler
from b2b_workflow_simulator.primitives.event import Event, EventType
from b2b_workflow_simulator.simulation import (
    SimulationResult,
    choose_next_node,
    record_actor_utilization,
    record_multi_resource_totals,
    record_pool_utilization,
    record_task_totals,
    resolve_arrival_times,
    resolve_task_schedule,
)
from b2b_workflow_simulator.workflow import Workflow

_ARRIVAL = "arrival"
_TASK_COMPLETE = "task_complete"

# Lower values are processed first when timestamps tie, so a task that
# finishes at time T releases its actor (and any downstream effects) before
# a case that happens to arrive at that same instant contends for capacity.
_PRIORITY = {_TASK_COMPLETE: 0, _ARRIVAL: 1}


@dataclass
class _QueuedEvent:
    """One entry on the engine's global event queue.

    Comparison is by `(timestamp, priority, sequence)` only, so events at
    the same simulated time are resolved deterministically by kind and
    then by insertion order, regardless of what their (unorderable)
    payload dictionaries contain.
    """

    timestamp: float
    priority: int
    sequence: int
    kind: str
    payload: dict[str, Any]

    def __lt__(self, other: _QueuedEvent) -> bool:
        return (self.timestamp, self.priority, self.sequence) < (
            other.timestamp,
            other.priority,
            other.sequence,
        )


class DiscreteEventEngine:
    """Runs a `Workflow` using a global, time-ordered event queue.

    See the module docstring for how this differs from `SimulationRunner`.
    Usage mirrors `SimulationRunner`:

        result = DiscreteEventEngine(seed=1).run(workflow, num_cases=200,
                                                   arrival_interval_minutes=15.0)
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._sequence = itertools.count()

    def run(
        self,
        workflow: Workflow,
        num_cases: int,
        arrival_interval_minutes: float | None = None,
        arrival_model: ArrivalModel | None = None,
    ) -> SimulationResult:
        """Simulate `num_cases` cases through `workflow` via the event queue.

        Arguments have the same meaning as `SimulationRunner.run`.
        """
        if num_cases <= 0:
            raise ValueError("num_cases must be a positive integer")
        if arrival_interval_minutes is not None and arrival_interval_minutes < 0:
            raise ValueError("arrival_interval_minutes cannot be negative")
        workflow.validate()
        arrival_times = resolve_arrival_times(
            num_cases, arrival_interval_minutes, arrival_model, self._rng
        )

        events: list[Event] = []
        kpi = KPIResult(workflow_name=workflow.name)
        scheduler = ActorScheduler() if arrival_times is not None else None
        pool_scheduler = PoolScheduler()
        queue: list[_QueuedEvent] = []

        for case_index in range(num_cases):
            case_id = f"case-{case_index + 1}"
            arrival_time = arrival_times[case_index] if arrival_times is not None else 0.0
            self._push(queue, arrival_time, _ARRIVAL, {"case_id": case_id})

        while queue:
            item = heapq.heappop(queue)
            if item.kind == _ARRIVAL:
                self._handle_arrival(workflow, item, events, kpi, scheduler, pool_scheduler, queue)
            else:
                self._handle_task_complete(
                    workflow, item, events, kpi, scheduler, pool_scheduler, queue
                )

        kpi.total_cases = num_cases
        if scheduler is not None:
            record_actor_utilization(workflow, kpi, scheduler)
        record_pool_utilization(workflow, kpi, pool_scheduler)

        events.sort(key=lambda event: event.timestamp_minutes)
        return SimulationResult(workflow_name=workflow.name, events=events, kpi=kpi)

    def _push(
        self, queue: list[_QueuedEvent], timestamp: float, kind: str, payload: dict[str, Any]
    ) -> None:
        heapq.heappush(
            queue,
            _QueuedEvent(timestamp, _PRIORITY[kind], next(self._sequence), kind, payload),
        )

    def _handle_arrival(
        self,
        workflow: Workflow,
        item: _QueuedEvent,
        events: list[Event],
        kpi: KPIResult,
        scheduler: ActorScheduler | None,
        pool_scheduler: PoolScheduler,
        queue: list[_QueuedEvent],
    ) -> None:
        case_id = item.payload["case_id"]
        events.append(Event(EventType.CASE_STARTED, item.timestamp, case_id))
        self._start_node(
            workflow,
            case_id,
            workflow.entry_node_id,
            ready_time=item.timestamp,
            arrival_time=item.timestamp,
            events=events,
            kpi=kpi,
            scheduler=scheduler,
            pool_scheduler=pool_scheduler,
            queue=queue,
        )

    def _start_node(
        self,
        workflow: Workflow,
        case_id: str,
        node_id: str,
        ready_time: float,
        arrival_time: float,
        events: list[Event],
        kpi: KPIResult,
        scheduler: ActorScheduler | None,
        pool_scheduler: PoolScheduler,
        queue: list[_QueuedEvent],
    ) -> None:
        node = workflow.get_node(node_id)
        actor = workflow.get_actor(node.actor_id)
        sampled_base = node.duration_model.sample(self._rng, node.base_duration_minutes)

        scheduled, tracks_capacity, details = resolve_task_schedule(
            workflow, node, sampled_base, ready_time, scheduler, pool_scheduler
        )
        start, end, wait = scheduled.start, scheduled.end, scheduled.wait_minutes
        duration, cost = scheduled.duration, scheduled.cost

        if node.is_multi_resource:
            record_multi_resource_totals(kpi, node.node_id, scheduled.coordination_delay_minutes)

        if tracks_capacity:
            kpi.total_wait_minutes += wait
            kpi.actor_wait_minutes[actor.actor_id] = (
                kpi.actor_wait_minutes.get(actor.actor_id, 0.0) + wait
            )
            if wait > 0:
                events.append(
                    Event(
                        EventType.TASK_QUEUED,
                        ready_time,
                        case_id,
                        node.node_id,
                        actor.actor_id,
                        {**details, "wait_minutes": wait},
                    )
                )

        kpi.node_visit_counts[node.node_id] = kpi.node_visit_counts.get(node.node_id, 0) + 1
        events.append(
            Event(EventType.TASK_STARTED, start, case_id, node.node_id, actor.actor_id, details)
        )

        failed = self._rng.random() < scheduled.error_rate
        escalated = (
            not failed
            and scheduled.checks_escalation
            and self._rng.random() < scheduled.escalation_rate
        )

        self._push(
            queue,
            end,
            _TASK_COMPLETE,
            {
                "case_id": case_id,
                "node_id": node.node_id,
                "actor_id": actor.actor_id,
                "duration": duration,
                "cost": cost,
                "failed": failed,
                "escalated": escalated,
                "is_terminal": node.is_terminal,
                "arrival_time": arrival_time,
                "tracks_capacity": tracks_capacity,
            },
        )

    def _handle_task_complete(
        self,
        workflow: Workflow,
        item: _QueuedEvent,
        events: list[Event],
        kpi: KPIResult,
        scheduler: ActorScheduler | None,
        pool_scheduler: PoolScheduler,
        queue: list[_QueuedEvent],
    ) -> None:
        payload = item.payload
        case_id = payload["case_id"]
        node_id = payload["node_id"]
        actor_id = payload["actor_id"]
        duration = payload["duration"]
        cost = payload["cost"]
        tracks_capacity = payload["tracks_capacity"]
        timestamp = item.timestamp

        if payload["failed"]:
            record_task_totals(kpi, node_id, duration, cost)
            kpi.node_failure_counts[node_id] = kpi.node_failure_counts.get(node_id, 0) + 1
            events.append(
                Event(
                    EventType.TASK_FAILED,
                    timestamp,
                    case_id,
                    node_id,
                    actor_id,
                    {"reason": "actor_error"},
                )
            )
            if tracks_capacity:
                events.append(
                    Event(EventType.RESOURCE_RELEASED, timestamp, case_id, node_id, actor_id)
                )
            events.append(Event(EventType.CASE_FAILED, timestamp, case_id))
            kpi.failed_cases += 1
            kpi.total_duration_minutes += timestamp - payload["arrival_time"]
            return

        if payload["escalated"]:
            kpi.total_escalations += 1
            events.append(Event(EventType.TASK_ESCALATED, timestamp, case_id, node_id, actor_id))
        else:
            events.append(Event(EventType.TASK_COMPLETED, timestamp, case_id, node_id, actor_id))

        record_task_totals(kpi, node_id, duration, cost)
        if tracks_capacity:
            events.append(
                Event(EventType.RESOURCE_RELEASED, timestamp, case_id, node_id, actor_id)
            )

        if payload["is_terminal"]:
            events.append(Event(EventType.CASE_COMPLETED, timestamp, case_id))
            kpi.completed_cases += 1
            kpi.total_duration_minutes += timestamp - payload["arrival_time"]
            return

        next_node_id = choose_next_node(workflow, node_id, self._rng)
        self._start_node(
            workflow,
            case_id,
            next_node_id,
            ready_time=timestamp,
            arrival_time=payload["arrival_time"],
            events=events,
            kpi=kpi,
            scheduler=scheduler,
            pool_scheduler=pool_scheduler,
            queue=queue,
        )


__all__ = ["DiscreteEventEngine"]
