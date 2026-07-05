"""Node primitive: a single stage of work inside a business workflow."""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.duration import DurationModel


@dataclass
class Node:
    """A stage in a workflow, e.g. "Qualify Lead" or "Draft Proposal".

    A node represents *what* work happens at a point in the process. It does
    not know how it connects to other stages -- that is the job of `Edge`.
    Execution behavior (duration, cost, error rate) is derived from the
    actor assigned to the node at simulation time, but a node can define
    baseline effort that is independent of who performs it.

    Attributes:
        node_id: Stable, unique identifier used by edges and simulation events.
        name: Human-readable name shown in reports.
        description: Longer explanation of the work performed at this stage.
        actor_id: Identifier of the actor (human or AI agent) assigned to this node.
        base_duration_minutes: Expected effort in minutes before actor multipliers.
        duration_model: How actual duration varies around `base_duration_minutes`
            from one case to the next. Defaults to a fixed, non-random duration.
        is_terminal: Whether reaching this node ends the case successfully.
        metadata: Free-form extension bag for domain-specific attributes.
    """

    node_id: str
    name: str
    actor_id: str
    description: str = ""
    base_duration_minutes: float = 0.0
    duration_model: DurationModel = field(default_factory=DurationModel)
    is_terminal: bool = False
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must be a non-empty string")
        if not self.actor_id:
            raise ValueError("actor_id must be a non-empty string")
        if self.base_duration_minutes < 0:
            raise ValueError("base_duration_minutes cannot be negative")
