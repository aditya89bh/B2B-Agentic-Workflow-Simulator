"""Event primitive: an immutable log entry describing something that happened."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    """Categories of events emitted by the simulation runner."""

    CASE_STARTED = "case_started"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_ESCALATED = "task_escalated"
    CASE_COMPLETED = "case_completed"
    CASE_FAILED = "case_failed"


@dataclass(frozen=True)
class Event:
    """A single, immutable record in the simulation's audit trail.

    Events form the raw timeline that KPI aggregation and bottleneck
    detection are built on top of. They are intentionally simple and
    serializable so they can be logged, exported, or replayed.

    Attributes:
        event_type: What kind of occurrence this event represents.
        timestamp_minutes: Simulated time, in minutes, since the run started.
        case_id: The case this event pertains to.
        node_id: The node involved, if any.
        actor_id: The actor involved, if any.
        details: Free-form extension bag for event-specific data.
    """

    event_type: EventType
    timestamp_minutes: float
    case_id: str
    node_id: str = ""
    actor_id: str = ""
    details: dict = field(default_factory=dict)
