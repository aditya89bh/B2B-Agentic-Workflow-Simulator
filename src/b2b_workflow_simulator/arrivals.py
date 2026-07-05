"""Arrival models: how cases show up over time, beyond a single fixed interval.

`SimulationRunner` and `DiscreteEventEngine` already support a plain fixed
interval via `arrival_interval_minutes`. Real intake rarely looks like
that: leads trickle in with random gaps, invoices arrive in daily
batches, support tickets only appear during business hours, and most
systems see a "peak window" with a materially higher arrival rate than
the rest of the day. `ArrivalModel` captures those shapes explicitly
while keeping every simulation deterministic for a given seed.

Kinds:
    fixed: Cases arrive exactly `interval_minutes` apart. Equivalent to
        passing `arrival_interval_minutes` directly to a runner.
    uniform: Gaps between consecutive arrivals are drawn uniformly from
        `[min_interval_minutes, max_interval_minutes]`.
    batched: `batch_size` cases arrive simultaneously every
        `batch_interval_minutes` (e.g. a nightly invoice batch).
    business_hours: Cases arrive `interval_minutes` apart, but only
        within `business_start_hour`-`business_end_hour` on
        `business_days`; time outside that window is skipped entirely.
    peak_hours: Like `business_hours` but without a day/hour cutoff --
        arrivals use `peak_interval_minutes` spacing during
        `peak_start_hour`-`peak_end_hour` each day, and `interval_minutes`
        spacing the rest of the time.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

FIXED = "fixed"
UNIFORM = "uniform"
BATCHED = "batched"
BUSINESS_HOURS = "business_hours"
PEAK_HOURS = "peak_hours"

_VALID_KINDS = (FIXED, UNIFORM, BATCHED, BUSINESS_HOURS, PEAK_HOURS)

MINUTES_PER_DAY = 24 * 60
ALL_WEEKDAYS = frozenset({0, 1, 2, 3, 4, 5, 6})
MONDAY_TO_FRIDAY = frozenset({0, 1, 2, 3, 4})


def _next_business_moment(
    t: float, start_hour: float, end_hour: float, business_days: frozenset[int]
) -> float:
    """Return the earliest moment at or after `t` inside a business window."""
    window_start_minutes = start_hour * 60.0
    window_end_minutes = end_hour * 60.0
    day_index = int(t // MINUTES_PER_DAY)
    while True:
        day_start = day_index * MINUTES_PER_DAY
        if (day_index % 7) in business_days:
            window_start = day_start + window_start_minutes
            window_end = day_start + window_end_minutes
            if t <= window_start:
                return window_start
            if t < window_end:
                return t
        day_index += 1
        t = day_index * MINUTES_PER_DAY


@dataclass(frozen=True)
class ArrivalModel:
    """Describes how simulated cases are spaced out over time.

    Only the fields relevant to `kind` need to be set; unused fields are
    ignored. See the module docstring for what each `kind` means.
    """

    kind: str = FIXED
    interval_minutes: float | None = None
    min_interval_minutes: float | None = None
    max_interval_minutes: float | None = None
    batch_size: int = 1
    batch_interval_minutes: float | None = None
    business_start_hour: float = 9.0
    business_end_hour: float = 17.0
    business_days: frozenset[int] = field(default_factory=lambda: MONDAY_TO_FRIDAY)
    peak_start_hour: float = 9.0
    peak_end_hour: float = 11.0
    peak_interval_minutes: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"kind must be one of {_VALID_KINDS}, got {self.kind!r}")
        if not 0.0 <= self.business_start_hour < self.business_end_hour <= 24.0:
            raise ValueError("business_start_hour must be less than business_end_hour, in 0-24")
        if not 0.0 <= self.peak_start_hour < self.peak_end_hour <= 24.0:
            raise ValueError("peak_start_hour must be less than peak_end_hour, in 0-24")

        if self.kind in (FIXED, BUSINESS_HOURS, PEAK_HOURS):
            if self.interval_minutes is None or self.interval_minutes <= 0:
                raise ValueError(f"{self.kind} requires a positive interval_minutes")
        if self.kind == UNIFORM:
            if self.min_interval_minutes is None or self.max_interval_minutes is None:
                raise ValueError("uniform requires min_interval_minutes and max_interval_minutes")
            if self.min_interval_minutes < 0:
                raise ValueError("min_interval_minutes cannot be negative")
            if self.min_interval_minutes > self.max_interval_minutes:
                raise ValueError("min_interval_minutes cannot exceed max_interval_minutes")
        if self.kind == BATCHED:
            if self.batch_size < 1:
                raise ValueError("batch_size must be at least 1")
            if self.batch_interval_minutes is None or self.batch_interval_minutes < 0:
                raise ValueError("batched requires a non-negative batch_interval_minutes")
        if self.kind == PEAK_HOURS:
            if self.peak_interval_minutes is None or self.peak_interval_minutes <= 0:
                raise ValueError("peak_hours requires a positive peak_interval_minutes")

    def generate(self, num_cases: int, rng: random.Random) -> list[float]:
        """Return `num_cases` non-decreasing arrival timestamps, in minutes."""
        if num_cases <= 0:
            raise ValueError("num_cases must be a positive integer")
        if self.kind == FIXED:
            return [i * self.interval_minutes for i in range(num_cases)]
        if self.kind == UNIFORM:
            return self._generate_uniform(num_cases, rng)
        if self.kind == BATCHED:
            return [
                (i // self.batch_size) * self.batch_interval_minutes for i in range(num_cases)
            ]
        if self.kind == BUSINESS_HOURS:
            return self._generate_business_hours(num_cases)
        return self._generate_peak_hours(num_cases)

    def _generate_uniform(self, num_cases: int, rng: random.Random) -> list[float]:
        times = [0.0]
        for _ in range(num_cases - 1):
            gap = rng.uniform(self.min_interval_minutes, self.max_interval_minutes)
            times.append(times[-1] + gap)
        return times

    def _generate_business_hours(self, num_cases: int) -> list[float]:
        times = []
        t = 0.0
        for _ in range(num_cases):
            t = _next_business_moment(
                t, self.business_start_hour, self.business_end_hour, self.business_days
            )
            times.append(t)
            t += self.interval_minutes
        return times

    def _generate_peak_hours(self, num_cases: int) -> list[float]:
        peak_start_minutes = self.peak_start_hour * 60.0
        peak_end_minutes = self.peak_end_hour * 60.0
        times = []
        t = 0.0
        for _ in range(num_cases):
            times.append(t)
            time_of_day = t % MINUTES_PER_DAY
            in_peak = peak_start_minutes <= time_of_day < peak_end_minutes
            t += self.peak_interval_minutes if in_peak else self.interval_minutes
        return times


__all__ = [
    "ArrivalModel",
    "FIXED",
    "UNIFORM",
    "BATCHED",
    "BUSINESS_HOURS",
    "PEAK_HOURS",
    "ALL_WEEKDAYS",
    "MONDAY_TO_FRIDAY",
]
