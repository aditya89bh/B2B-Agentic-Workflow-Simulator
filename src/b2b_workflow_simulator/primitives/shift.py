"""Shift primitive: a recurring working window for a pooled worker."""

from __future__ import annotations

from dataclasses import dataclass, field

MONDAY_TO_FRIDAY = frozenset({0, 1, 2, 3, 4})
ALL_DAYS = frozenset({0, 1, 2, 3, 4, 5, 6})


@dataclass(frozen=True)
class Shift:
    """A recurring block of time during which a worker is on the clock.

    Days follow `datetime.weekday()` numbering: 0 is Monday, 6 is Sunday.
    A worker with no matching shift on a given day is treated as
    unavailable that day, which is how weekday/weekend coverage
    differences are expressed (e.g. a weekday-only support shift versus a
    weekend on-call shift with different hours).

    Attributes:
        name: Human-readable label, e.g. "Day shift" or "Weekend on-call".
        days: Which days of the week this shift is active on.
        start_hour: Shift start, in hours since midnight (0-24).
        end_hour: Shift end, in hours since midnight (0-24).
        overtime_hours: Additional hours beyond `end_hour` that can be
            worked on this shift before capacity is considered exhausted
            for the day. Zero means no overtime is available.
    """

    name: str
    days: frozenset[int] = field(default_factory=lambda: MONDAY_TO_FRIDAY)
    start_hour: float = 9.0
    end_hour: float = 17.0
    overtime_hours: float = 0.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if not self.days:
            raise ValueError("days must contain at least one weekday")
        if not all(0 <= day <= 6 for day in self.days):
            raise ValueError("days must be integers between 0 (Monday) and 6 (Sunday)")
        if not 0.0 <= self.start_hour < self.end_hour <= 24.0:
            raise ValueError("start_hour must be less than end_hour, both within 0-24")
        if self.overtime_hours < 0:
            raise ValueError("overtime_hours cannot be negative")

    @property
    def regular_hours(self) -> float:
        """Standard (non-overtime) hours available per active day."""
        return self.end_hour - self.start_hour

    @property
    def hours_with_overtime(self) -> float:
        """Total hours available per active day, including overtime."""
        return self.regular_hours + self.overtime_hours

    def is_active_on(self, weekday: int) -> bool:
        """Return whether this shift covers the given weekday (0=Monday)."""
        return weekday in self.days


__all__ = ["Shift", "MONDAY_TO_FRIDAY", "ALL_DAYS"]
