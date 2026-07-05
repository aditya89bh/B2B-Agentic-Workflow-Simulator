"""Duration model primitive: seeded, reproducible sampling of task durations."""

from __future__ import annotations

import random
from dataclasses import dataclass

FIXED = "fixed"
UNIFORM = "uniform"
TRIANGULAR = "triangular"

_VALID_KINDS = (FIXED, UNIFORM, TRIANGULAR)


@dataclass(frozen=True)
class DurationModel:
    """Describes how a node's actual duration varies around its baseline.

    Real work rarely takes exactly the same amount of time twice. This
    model lets a `Node` express that variability explicitly while keeping
    simulations fully reproducible: all randomness flows through the
    `random.Random` instance passed in by the caller (normally the
    `SimulationRunner`'s seeded RNG), so the same seed always produces the
    same sampled durations.

    Kinds:
        fixed: Always returns the node's `base_duration_minutes` unchanged.
            This is the default and matches Phase 1 behavior exactly.
        uniform: Samples uniformly between `minimum` and `maximum`. If
            either bound is omitted, it defaults to 80%/120% of the base
            duration respectively.
        triangular: Samples from a triangular distribution with the given
            `minimum`, `mode`, and `maximum`. Triangular distributions are
            a common, simple choice for modeling task effort because they
            only require three intuitive estimates (best case, most
            likely, worst case) rather than a full statistical fit.

    Attributes:
        kind: One of "fixed", "uniform", or "triangular".
        minimum: Lower bound in minutes, for "uniform" and "triangular".
        maximum: Upper bound in minutes, for "uniform" and "triangular".
        mode: Most likely value in minutes, for "triangular" only.
    """

    kind: str = FIXED
    minimum: float | None = None
    maximum: float | None = None
    mode: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"kind must be one of {_VALID_KINDS}, got {self.kind!r}")
        if self.minimum is not None and self.minimum < 0:
            raise ValueError("minimum cannot be negative")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("minimum cannot be greater than maximum")

    def sample(self, rng: random.Random, base_duration_minutes: float) -> float:
        """Return one sampled duration in minutes, given a base duration.

        `base_duration_minutes` anchors the distribution: it is used
        directly for "fixed", and as a fallback for any bound left
        unspecified on "uniform" or "triangular".
        """
        if self.kind == FIXED:
            return base_duration_minutes

        low = self.minimum if self.minimum is not None else base_duration_minutes * 0.8
        high = self.maximum if self.maximum is not None else base_duration_minutes * 1.2

        if self.kind == UNIFORM:
            return rng.uniform(low, high)

        mode = self.mode if self.mode is not None else base_duration_minutes
        return rng.triangular(low, high, mode)


__all__ = ["DurationModel", "FIXED", "UNIFORM", "TRIANGULAR"]
