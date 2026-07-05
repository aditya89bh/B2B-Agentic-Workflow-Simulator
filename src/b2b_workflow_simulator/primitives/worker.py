"""Worker primitive: one interchangeable member of an `ActorPool`."""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.shift import Shift


@dataclass
class Worker:
    """An individual team member who can pick up work routed to their pool.

    Unlike `HumanActor`, a `Worker` is never referenced directly from a
    `Node`; it only exists as a member of an `ActorPool`, which is what
    nodes reference and what the simulation engines schedule against. A
    pool typically holds several workers with similar but not identical
    performance characteristics, reflecting real teams where tenure and
    skill vary member to member.

    Attributes:
        worker_id: Stable, unique identifier within the pool.
        name: Human-readable name, e.g. "Agent - Priya".
        hourly_cost: Fully-loaded cost per hour.
        speed_multiplier: Multiplier applied to a node's base duration,
            analogous to `HumanActor.speed_multiplier`.
        error_rate: Probability (0.0-1.0) this worker's execution of a
            task fails and requires escalation or rework.
        shifts: The recurring working windows this worker is scheduled
            for. An empty list means the worker follows the pool's
            default availability rather than a personal schedule.
        available: Whether this worker can currently be assigned work at
            all, independent of shift timing (e.g. on leave, resigned).
            Set to `False` to model attrition or planned absence.
    """

    worker_id: str
    name: str
    hourly_cost: float = 0.0
    speed_multiplier: float = 1.0
    error_rate: float = 0.0
    shifts: list[Shift] = field(default_factory=list)
    available: bool = True

    def __post_init__(self) -> None:
        if not self.worker_id:
            raise ValueError("worker_id must be a non-empty string")
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if self.hourly_cost < 0:
            raise ValueError("hourly_cost cannot be negative")
        if self.speed_multiplier <= 0:
            raise ValueError("speed_multiplier must be positive")
        if not 0.0 <= self.error_rate <= 1.0:
            raise ValueError("error_rate must be between 0.0 and 1.0")

    def cost_for_duration(self, minutes: float) -> float:
        """Return the labor cost of occupying this worker for `minutes`."""
        return (minutes / 60.0) * self.hourly_cost

    def is_scheduled_on(self, weekday: int) -> bool:
        """Return whether any of this worker's shifts covers `weekday`.

        A worker with no shifts defined is treated as always scheduled,
        deferring entirely to the pool's own availability window.
        """
        if not self.shifts:
            return True
        return any(shift.is_active_on(weekday) for shift in self.shifts)


__all__ = ["Worker"]
