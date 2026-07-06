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


def apply_profile_to_workflow(workflow, profile: AssumptionProfile):
    """Return a new ``Workflow`` with actor parameters scaled by profile multipliers.

    The **original workflow is never mutated**.  A new ``Workflow`` instance is
    returned with the following transformations applied to each actor:

    - ``AIAgentActor``: ``error_rate *= ai_error_rate_multiplier``,
      ``cost_per_execution *= ai_cost_multiplier``.
      ``error_rate`` is capped at 1.0.
    - ``HumanActor``: ``hourly_cost *= human_hourly_cost_multiplier``.
    - ``ActorPool`` workers: each ``Worker.hourly_cost *= human_hourly_cost_multiplier``.
    - All other actor types: copied unchanged.

    When all three multipliers are 1.0, the original workflow is returned as-is
    (identity fast-path — no allocation).

    Args:
        workflow: A validated ``Workflow`` to copy and scale.
        profile: The assumption profile whose multipliers to apply.

    Returns:
        A new ``Workflow`` with scaled actor parameters, or the original if all
        multipliers are 1.0.
    """
    from dataclasses import replace as dc_replace

    from b2b_workflow_simulator.pool import ActorPool
    from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
    from b2b_workflow_simulator.primitives.human import HumanActor
    from b2b_workflow_simulator.workflow import Workflow

    ai_err = profile.ai_error_rate_multiplier
    ai_cost = profile.ai_cost_multiplier
    human_cost = profile.human_hourly_cost_multiplier

    if ai_err == 1.0 and ai_cost == 1.0 and human_cost == 1.0:
        return workflow

    new_wf = Workflow(
        workflow_id=workflow.workflow_id,
        name=workflow.name,
        entry_node_id=workflow.entry_node_id,
        description=workflow.description,
    )

    for actor in workflow.actors.values():
        if isinstance(actor, AIAgentActor):
            new_actor = dc_replace(
                actor,
                error_rate=min(1.0, actor.error_rate * ai_err),
                cost_per_execution=actor.cost_per_execution * ai_cost,
            )
        elif isinstance(actor, HumanActor):
            new_actor = dc_replace(actor, hourly_cost=actor.hourly_cost * human_cost)
        elif isinstance(actor, ActorPool):
            scaled_workers = [
                dc_replace(w, hourly_cost=w.hourly_cost * human_cost)
                for w in actor.workers
            ]
            new_actor = dc_replace(actor, workers=scaled_workers)
        else:
            new_actor = actor
        new_wf.add_actor(new_actor)

    for node in workflow.nodes.values():
        new_wf.add_node(node)

    for edge in workflow.edges:
        new_wf.add_edge(edge)

    return new_wf


__all__ = [
    "AssumptionProfile",
    "apply_profile_to_workflow",
    "load_assumption_profile",
    "save_assumption_profile",
]
