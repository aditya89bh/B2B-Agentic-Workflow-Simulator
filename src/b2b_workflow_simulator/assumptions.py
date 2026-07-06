"""Assumption profiles: reproducible, shareable simulation configurations.

An ``AssumptionProfile`` captures every assumption that affects a simulation
run in one JSON-serializable object.  Users can share profiles with clients,
store them in version control, or swap between "conservative", "base", and
"aggressive" scenarios without re-typing CLI flags.

The profile also records adjustments (multipliers) for AI error rates, AI
costs, and human hourly costs so a single workflow definition can be stress-
tested across different economic assumptions without modifying the workflow.

Note: multiplier adjustments are *reported in the profile* but the CLI
currently applies them by description only (the actual adjustment requires
building modified workflow copies, which is handled at the call site that
consumes the profile).  This is intentional: the simulation engine takes
complete ``Workflow`` objects, not partial overrides.

Usage::

    from b2b_workflow_simulator.assumptions import (
        AssumptionProfile, load_assumption_profile, save_assumption_profile
    )

    profile = AssumptionProfile(
        num_cases=500, seed=1, implementation_cost=10_000.0,
        description="Conservative estimate for board presentation"
    )
    save_assumption_profile(profile, "conservative.json")

    loaded = load_assumption_profile("conservative.json")
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from b2b_workflow_simulator.simulation import ENGINES


@dataclass
class AssumptionProfile:
    """All simulation assumptions in one serializable object.

    Attributes:
        num_cases: Number of cases to simulate per variant.
        seed: Random seed for reproducible results.
        arrival_interval_minutes: If set, enables capacity-aware queueing.
        implementation_cost: One-time cost of implementing the redesign.
        engine: Simulation engine (``"simple"`` or ``"discrete"``).
        collect_events: Whether to collect the full event log.
        currency_label: Currency symbol shown in reports (e.g. ``"$"``, ``"€"``).
        description: Free-text description of what this profile represents.
        ai_error_rate_multiplier: Multiplier applied to AI actor error rates
            (1.0 = no change; 2.0 = double the error rate).
        ai_cost_multiplier: Multiplier applied to AI actor per-execution costs.
        human_hourly_cost_multiplier: Multiplier applied to human actor hourly
            costs.
    """

    num_cases: int = 200
    seed: int = 42
    arrival_interval_minutes: float | None = None
    implementation_cost: float | None = None
    engine: str = "simple"
    collect_events: bool = False
    currency_label: str = "$"
    description: str = ""
    ai_error_rate_multiplier: float = 1.0
    ai_cost_multiplier: float = 1.0
    human_hourly_cost_multiplier: float = 1.0

    def __post_init__(self) -> None:
        errors: list[str] = []
        if self.num_cases <= 0:
            errors.append(f"num_cases must be positive, got {self.num_cases}")
        if self.engine not in ENGINES:
            errors.append(
                f"engine must be one of {ENGINES}, got {self.engine!r}"
            )
        if self.arrival_interval_minutes is not None and self.arrival_interval_minutes < 0:
            errors.append(
                f"arrival_interval_minutes cannot be negative, "
                f"got {self.arrival_interval_minutes}"
            )
        if self.implementation_cost is not None and self.implementation_cost < 0:
            errors.append(
                f"implementation_cost cannot be negative, "
                f"got {self.implementation_cost}"
            )
        for name, val in [
            ("ai_error_rate_multiplier", self.ai_error_rate_multiplier),
            ("ai_cost_multiplier", self.ai_cost_multiplier),
            ("human_hourly_cost_multiplier", self.human_hourly_cost_multiplier),
        ]:
            if val <= 0:
                errors.append(f"{name} must be positive, got {val}")
        if errors:
            raise ValueError(
                "Invalid AssumptionProfile:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    def to_dict(self) -> dict:
        """Serialize to a plain dict (suitable for JSON)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AssumptionProfile:
        """Deserialize from a dict, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


def save_assumption_profile(profile: AssumptionProfile, path: str | Path) -> None:
    """Serialize an ``AssumptionProfile`` to a JSON file.

    Args:
        profile: The profile to save.
        path: Destination file path.  Parent directories are created if
            they do not exist.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(profile.to_dict(), indent=2) + "\n")


def load_assumption_profile(path: str | Path) -> AssumptionProfile:
    """Load an ``AssumptionProfile`` from a JSON file.

    Args:
        path: Path to a JSON file previously written by
            :func:`save_assumption_profile` or crafted manually.

    Returns:
        A validated :class:`AssumptionProfile`.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains invalid values.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    data = json.loads(Path(path).read_text())
    return AssumptionProfile.from_dict(data)


__all__ = [
    "AssumptionProfile",
    "load_assumption_profile",
    "save_assumption_profile",
]
