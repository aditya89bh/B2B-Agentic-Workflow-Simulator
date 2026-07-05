"""Queue behavior analysis: derive queueing dynamics from a simulation's event log.

`SimulationResult.kpi` already reports aggregate wait time and
utilization. This module goes one level deeper by replaying the event
log (`TASK_QUEUED`, `TASK_STARTED`, `RESOURCE_RELEASED`) to reconstruct,
per actor:

    - how deep the queue got and how it moved over time
    - whether the queue was trending up (growing), down (collapsing), or
      holding steady across the run
    - how much of the run each actor spent idle
    - overall case throughput

This only produces meaningful queueing data for capacity-aware runs (an
`arrival_interval_minutes` or `arrival_model` was supplied); runs without
capacity constraints emit no `TASK_QUEUED`/`RESOURCE_RELEASED` events, so
every actor simply reports zero queue depth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.event import EventType
from b2b_workflow_simulator.simulation import SimulationResult

GROWING = "growing"
COLLAPSING = "collapsing"
STABLE = "stable"


def _time_weighted_halves(
    timeline: list[tuple[float, int]], span_start: float, span_end: float
) -> tuple[float, float]:
    """Split a step-function depth timeline into time-weighted first/second-half averages."""
    midpoint = (span_start + span_end) / 2.0
    boundary_points = [*timeline, (span_end, timeline[-1][1])]

    first_area = 0.0
    second_area = 0.0
    for (start, depth), (end, _) in zip(boundary_points, boundary_points[1:], strict=False):
        if end <= start:
            continue
        if end <= midpoint:
            first_area += depth * (end - start)
        elif start >= midpoint:
            second_area += depth * (end - start)
        else:
            first_area += depth * (midpoint - start)
            second_area += depth * (end - midpoint)

    first_duration = midpoint - span_start
    second_duration = span_end - midpoint
    first_avg = first_area / first_duration if first_duration > 0 else 0.0
    second_avg = second_area / second_duration if second_duration > 0 else 0.0
    return first_avg, second_avg


@dataclass
class QueueAnalysis:
    """Queueing dynamics reconstructed from one simulation's event log.

    Attributes:
        max_queue_depth: Highest number of cases simultaneously waiting
            for each actor, keyed by actor_id.
        queue_depth_timeline: For each actor, the sequence of
            `(timestamp_minutes, depth)` observations after every change
            in how many cases are waiting for it.
        actor_idle_minutes: Total minutes each actor spent with no case
            in progress, across the simulated span.
        throughput_per_hour: Completed cases per simulated hour.
        total_span_minutes: Simulated time from the first to the last
            recorded event.
    """

    max_queue_depth: dict[str, int] = field(default_factory=dict)
    queue_depth_timeline: dict[str, list[tuple[float, int]]] = field(default_factory=dict)
    actor_idle_minutes: dict[str, float] = field(default_factory=dict)
    throughput_per_hour: float = 0.0
    total_span_minutes: float = 0.0

    def queue_trend(self, actor_id: str) -> str:
        """Classify an actor's queue as "growing", "collapsing", or "stable".

        Compares the time-weighted average queue depth across the first
        and second halves of the actor's observed timeline (its first
        recorded change to its last), so a brief spike is not treated the
        same as a queue that stays deep for a long stretch. An actor with
        fewer than two recorded depth changes is "stable".
        """
        timeline = self.queue_depth_timeline.get(actor_id, [])
        if len(timeline) < 2:
            return STABLE

        span_start, span_end = timeline[0][0], timeline[-1][0]
        if span_end <= span_start:
            return STABLE

        first_half_avg, second_half_avg = _time_weighted_halves(timeline, span_start, span_end)

        if first_half_avg == 0 and second_half_avg == 0:
            return STABLE
        if second_half_avg > first_half_avg * 1.1:
            return GROWING
        if second_half_avg < first_half_avg * 0.9:
            return COLLAPSING
        return STABLE


def analyze_queue_behavior(result: SimulationResult) -> QueueAnalysis:
    """Reconstruct queue depth, idle time, and throughput from `result.events`."""
    events = sorted(result.events, key=lambda event: event.timestamp_minutes)
    if not events:
        return QueueAnalysis()

    depth: dict[str, int] = {}
    max_depth: dict[str, int] = {}
    timeline: dict[str, list[tuple[float, int]]] = {}
    pending_actor_by_case: dict[str, str] = {}

    last_free_at: dict[str, float] = {}
    busy_actors: set[str] = set()
    idle_minutes: dict[str, float] = {}

    def record_depth_change(actor_id: str, timestamp: float, delta: int) -> None:
        depth[actor_id] = depth.get(actor_id, 0) + delta
        max_depth[actor_id] = max(max_depth.get(actor_id, 0), depth[actor_id])
        timeline.setdefault(actor_id, []).append((timestamp, depth[actor_id]))

    for event in events:
        if event.event_type == EventType.TASK_QUEUED:
            record_depth_change(event.actor_id, event.timestamp_minutes, +1)
            pending_actor_by_case[event.case_id] = event.actor_id
        elif event.event_type == EventType.TASK_STARTED:
            queued_actor_id = pending_actor_by_case.pop(event.case_id, None)
            if queued_actor_id is not None:
                record_depth_change(queued_actor_id, event.timestamp_minutes, -1)
            actor_id = event.actor_id
            if actor_id not in busy_actors:
                idle_minutes[actor_id] = idle_minutes.get(actor_id, 0.0) + (
                    event.timestamp_minutes - last_free_at.get(actor_id, 0.0)
                )
            busy_actors.add(actor_id)
        elif event.event_type == EventType.RESOURCE_RELEASED:
            last_free_at[event.actor_id] = event.timestamp_minutes
            busy_actors.discard(event.actor_id)

    span_start = events[0].timestamp_minutes
    span_end = events[-1].timestamp_minutes
    total_span_minutes = span_end - span_start
    for actor_id, free_since in last_free_at.items():
        idle_minutes[actor_id] = idle_minutes.get(actor_id, 0.0) + (span_end - free_since)

    throughput_per_hour = (
        result.kpi.completed_cases / (total_span_minutes / 60.0) if total_span_minutes > 0 else 0.0
    )

    return QueueAnalysis(
        max_queue_depth=max_depth,
        queue_depth_timeline=timeline,
        actor_idle_minutes=idle_minutes,
        throughput_per_hour=throughput_per_hour,
        total_span_minutes=total_span_minutes,
    )


__all__ = ["QueueAnalysis", "analyze_queue_behavior", "GROWING", "COLLAPSING", "STABLE"]
