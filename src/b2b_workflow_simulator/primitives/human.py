"""Human actor primitive."""

from __future__ import annotations

from dataclasses import dataclass

from b2b_workflow_simulator.primitives.actor import Actor


@dataclass
class HumanActor(Actor):
    """A person performing work in the workflow.

    Human performance is modeled with three levers commonly used in
    operations analysis: an hourly cost rate, a speed multiplier relative
    to a node's baseline duration, and an error rate representing rework
    or mistakes (e.g. missed follow-ups, data entry errors).

    Attributes:
        hourly_cost: Fully-loaded cost per hour in the workflow's currency.
        speed_multiplier: Multiplier applied to a node's base duration.
            1.0 means the human takes exactly the baseline time; 1.3 means
            30% slower than baseline; 0.8 means 20% faster.
        error_rate: Probability (0.0-1.0) that this actor's execution of a
            task fails and requires escalation or rework.
    """

    hourly_cost: float = 0.0
    speed_multiplier: float = 1.0
    error_rate: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.hourly_cost < 0:
            raise ValueError("hourly_cost cannot be negative")
        if self.speed_multiplier <= 0:
            raise ValueError("speed_multiplier must be positive")
        if not 0.0 <= self.error_rate <= 1.0:
            raise ValueError("error_rate must be between 0.0 and 1.0")

    @property
    def kind(self) -> str:
        return "human"

    def cost_for_duration(self, minutes: float) -> float:
        """Return the labor cost of occupying this actor for `minutes`."""
        return (minutes / 60.0) * self.hourly_cost
