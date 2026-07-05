"""Base actor primitive shared by human and AI agent actors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Actor:
    """Common identity fields shared by anyone or anything that performs work.

    `Actor` is not meant to be instantiated directly in normal use; use
    `HumanActor` or `AIAgentActor` instead. It exists so the simulation
    runner and reporting code can treat both kinds of workers uniformly
    wherever only identity (not execution behavior) matters.

    Attributes:
        actor_id: Stable, unique identifier referenced by nodes.
        name: Human-readable name or role label (e.g. "SDR", "Triage Agent").
    """

    actor_id: str
    name: str

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("actor_id must be a non-empty string")
        if not self.name:
            raise ValueError("name must be a non-empty string")

    @property
    def kind(self) -> str:
        """Return a short label identifying the actor category."""
        return "actor"
