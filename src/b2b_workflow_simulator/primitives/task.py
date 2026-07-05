"""Task primitive: a single unit of work executed at a node during simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    """Lifecycle states for a `Task` instance."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class Task:
    """A concrete execution of a node's work for a single case.

    Where `Node` describes a stage in the abstract workflow, `Task`
    represents one instance of that stage being carried out for one case
    (e.g. one specific sales lead) during a simulation run.

    Attributes:
        task_id: Unique identifier for this task instance.
        node_id: The node this task executes.
        actor_id: The actor that executed (or attempted) this task.
        case_id: Identifier of the case (e.g. lead, ticket) this task belongs to.
        status: Current lifecycle state of the task.
        duration_minutes: Actual time spent, once known.
        cost: Actual cost incurred, once known.
        metadata: Free-form extension bag, e.g. failure reason.
    """

    task_id: str
    node_id: str
    actor_id: str
    case_id: str
    status: TaskStatus = TaskStatus.PENDING
    duration_minutes: float = 0.0
    cost: float = 0.0
    metadata: dict = field(default_factory=dict)

    def mark_completed(self, duration_minutes: float, cost: float) -> None:
        """Transition the task to COMPLETED and record actuals."""
        self.status = TaskStatus.COMPLETED
        self.duration_minutes = duration_minutes
        self.cost = cost

    def mark_failed(self, duration_minutes: float, cost: float, reason: str = "") -> None:
        """Transition the task to FAILED and record actuals plus a reason."""
        self.status = TaskStatus.FAILED
        self.duration_minutes = duration_minutes
        self.cost = cost
        if reason:
            self.metadata["failure_reason"] = reason

    def mark_escalated(self, duration_minutes: float, cost: float, reason: str = "") -> None:
        """Transition the task to ESCALATED, e.g. an AI agent deferring to a human."""
        self.status = TaskStatus.ESCALATED
        self.duration_minutes = duration_minutes
        self.cost = cost
        if reason:
            self.metadata["escalation_reason"] = reason
