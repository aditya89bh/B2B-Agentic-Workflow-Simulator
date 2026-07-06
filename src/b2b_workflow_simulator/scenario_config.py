"""Scenario configuration: adapt registered scenarios to specific organizations.

A ``ScenarioConfig`` is a JSON-serializable set of overrides applied on top of
a registered base scenario.  Users can change actor costs, node durations,
branch probabilities, and workflow names without editing Python code.

Design principles
-----------------
- Overrides are *sparse*: only changed fields need to be specified.
- The original scenario workflows are never mutated.
- Unknown actor/node/edge IDs raise :class:`ConfigValidationError`.
- After applying edge-probability overrides, outgoing probabilities from
  every node must still sum to 1.0.
- Configured workflows are validated before being returned.

All outputs produced from a configured scenario should clearly state that
they reflect user-provided calibrated assumptions, not validated truth.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


class ConfigValidationError(ValueError):
    """Raised when a :class:`ScenarioConfig` is structurally invalid."""


# ---------------------------------------------------------------------------
# Override dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ActorOverride:
    """Override for one actor's parameters.

    Attributes:
        actor_id: ID of the actor to override (must exist in the workflow).
        name: Optional new display name.
        hourly_cost: Replaces ``HumanActor.hourly_cost`` (non-negative).
        cost_per_execution: Replaces ``AIAgentActor.cost_per_execution``.
        speed_multiplier: Replaces the actor's speed multiplier (> 0).
        error_rate: Replaces the actor's error rate (0–1).
        escalation_rate: Replaces ``AIAgentActor.escalation_rate`` (0–1).
        available_hours_per_day: Replaces the actor's daily capacity (> 0).
    """

    actor_id: str
    name: str | None = None
    hourly_cost: float | None = None
    cost_per_execution: float | None = None
    speed_multiplier: float | None = None
    error_rate: float | None = None
    escalation_rate: float | None = None
    available_hours_per_day: float | None = None


@dataclass
class NodeOverride:
    """Override for one node's parameters.

    Attributes:
        node_id: ID of the node to override (must exist in the workflow).
        name: Optional new display name.
        base_duration_minutes: Replaces the node's base duration (≥ 0).
        actor_id: Reassigns the node to a different actor.
        is_terminal: Override terminal flag.
    """

    node_id: str
    name: str | None = None
    base_duration_minutes: float | None = None
    actor_id: str | None = None
    is_terminal: bool | None = None


@dataclass
class EdgeOverride:
    """Override for one edge's probability.

    Attributes:
        source: Source node ID.
        target: Target node ID.
        probability: New probability (0–1).  All outgoing edges from
            ``source`` must still sum to 1.0 after all overrides.
    """

    source: str
    target: str
    probability: float


@dataclass
class WorkflowMetadataOverride:
    """Override for workflow display names and descriptions.

    Attributes:
        workflow_name_before: New name for the "before" workflow.
        workflow_name_after: New name for the "after" workflow.
        description_before: New description for the "before" workflow.
        description_after: New description for the "after" workflow.
    """

    workflow_name_before: str | None = None
    workflow_name_after: str | None = None
    description_before: str | None = None
    description_after: str | None = None


# ---------------------------------------------------------------------------
# ScenarioConfig
# ---------------------------------------------------------------------------


@dataclass
class ScenarioConfig:
    """User-defined customization applied on top of a registered scenario.

    Attributes:
        base_scenario_slug: Slug of the registered scenario to customize.
        configured_slug: Unique slug for this configured variant.
        configured_name: Human-readable name for this configuration.
        client_name: Name of the client or organization this is built for.
        description: One-sentence description of what this config represents.
        profile_name: ``"base"``, ``"conservative"``, or ``"aggressive"``.
        actor_overrides: Actor parameter changes.
        node_overrides: Node parameter changes.
        edge_overrides: Edge probability changes.
        workflow_metadata: Optional workflow name/description overrides.
        notes: Free-text notes visible in reports.
        limitations: Explicit limitations of this configuration.
        created_by: Author identifier (e.g. consultant name).
        version: Config schema version (default ``"1.0"``).
    """

    base_scenario_slug: str
    configured_slug: str
    configured_name: str
    client_name: str = ""
    description: str = ""
    profile_name: str = "base"
    actor_overrides: list[ActorOverride] = field(default_factory=list)
    node_overrides: list[NodeOverride] = field(default_factory=list)
    edge_overrides: list[EdgeOverride] = field(default_factory=list)
    workflow_metadata: WorkflowMetadataOverride | None = None
    notes: str = ""
    limitations: list[str] = field(default_factory=list)
    created_by: str = ""
    version: str = "1.0"

    def to_dict(self) -> dict:
        """Serialize to a plain JSON-serializable dict."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ScenarioConfig:
        """Deserialize from a dict produced by :meth:`to_dict`."""
        actor_overrides = [ActorOverride(**a) for a in data.get("actor_overrides", [])]
        node_overrides = [NodeOverride(**n) for n in data.get("node_overrides", [])]
        edge_overrides = [EdgeOverride(**e) for e in data.get("edge_overrides", [])]
        wm_raw = data.get("workflow_metadata")
        workflow_metadata = WorkflowMetadataOverride(**wm_raw) if wm_raw else None
        return cls(
            base_scenario_slug=data["base_scenario_slug"],
            configured_slug=data["configured_slug"],
            configured_name=data["configured_name"],
            client_name=data.get("client_name", ""),
            description=data.get("description", ""),
            profile_name=data.get("profile_name", "base"),
            actor_overrides=actor_overrides,
            node_overrides=node_overrides,
            edge_overrides=edge_overrides,
            workflow_metadata=workflow_metadata,
            notes=data.get("notes", ""),
            limitations=data.get("limitations", []),
            created_by=data.get("created_by", ""),
            version=data.get("version", "1.0"),
        )


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def save_scenario_config(config: ScenarioConfig, path: str | Path) -> None:
    """Serialize a ``ScenarioConfig`` to a JSON file.

    Args:
        config: The configuration to save.
        path: Destination file path.  Parent directories are created if absent.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(config.to_dict(), indent=2) + "\n")


def load_scenario_config(path: str | Path) -> ScenarioConfig:
    """Load a ``ScenarioConfig`` from a JSON file.

    Args:
        path: Path to a JSON file previously written by
            :func:`save_scenario_config` or hand-crafted.

    Returns:
        A :class:`ScenarioConfig` instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        ConfigValidationError: If required fields are missing.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(
            f"Config file is not valid JSON: {exc}"
        ) from exc
    try:
        return ScenarioConfig.from_dict(data)
    except (KeyError, TypeError) as exc:
        raise ConfigValidationError(
            f"Config file is missing required fields: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_scenario_config(config: ScenarioConfig, scenario=None) -> list[str]:
    """Validate a ``ScenarioConfig`` and return a list of warning strings.

    If any violation is fatal, :class:`ConfigValidationError` is raised.
    Non-fatal warnings are collected and returned.

    Args:
        config: The configuration to validate.
        scenario: Optional pre-loaded scenario definition.  When ``None``,
            the scenario is looked up from the registry.

    Returns:
        A (possibly empty) list of warning strings.

    Raises:
        ConfigValidationError: For any structural violation.
    """
    from b2b_workflow_simulator.scenarios import get_scenario, scenario_exists

    errors: list[str] = []
    warnings: list[str] = []

    if not scenario_exists(config.base_scenario_slug):
        raise ConfigValidationError(
            f"base_scenario_slug {config.base_scenario_slug!r} is not a registered scenario."
        )
    if scenario is None:
        scenario = get_scenario(config.base_scenario_slug)

    valid_profiles = {"base", "conservative", "aggressive"}
    if config.profile_name not in valid_profiles:
        errors.append(
            f"profile_name {config.profile_name!r} is not valid "
            f"(must be one of: {', '.join(sorted(valid_profiles))})."
        )

    # Collect all actor/node/edge IDs from both workflows
    before_wf = scenario.before_builder()
    after_wf = scenario.after_builder()
    all_actor_ids = set(before_wf.actors) | set(after_wf.actors)
    all_node_ids = set(before_wf.nodes) | set(after_wf.nodes)
    all_edges_before = {(e.source, e.target) for e in before_wf.edges}
    all_edges_after = {(e.source, e.target) for e in after_wf.edges}
    all_edges = all_edges_before | all_edges_after

    # Validate actor overrides
    for ao in config.actor_overrides:
        if ao.actor_id not in all_actor_ids:
            errors.append(f"actor_id {ao.actor_id!r} not found in {config.base_scenario_slug}.")
        if ao.error_rate is not None and not 0.0 <= ao.error_rate <= 1.0:
            errors.append(f"actor {ao.actor_id!r}: error_rate {ao.error_rate} must be 0–1.")
        if ao.escalation_rate is not None and not 0.0 <= ao.escalation_rate <= 1.0:
            errors.append(
                f"actor {ao.actor_id!r}: escalation_rate {ao.escalation_rate} must be 0–1."
            )
        if ao.hourly_cost is not None and ao.hourly_cost < 0:
            errors.append(f"actor {ao.actor_id!r}: hourly_cost must be non-negative.")
        if ao.cost_per_execution is not None and ao.cost_per_execution < 0:
            errors.append(f"actor {ao.actor_id!r}: cost_per_execution must be non-negative.")
        if ao.speed_multiplier is not None and ao.speed_multiplier <= 0:
            errors.append(f"actor {ao.actor_id!r}: speed_multiplier must be positive.")
        if ao.available_hours_per_day is not None and ao.available_hours_per_day <= 0:
            errors.append(
                f"actor {ao.actor_id!r}: available_hours_per_day must be positive."
            )

    # Validate node overrides
    for no in config.node_overrides:
        if no.node_id not in all_node_ids:
            errors.append(f"node_id {no.node_id!r} not found in {config.base_scenario_slug}.")
        if no.base_duration_minutes is not None and no.base_duration_minutes < 0:
            errors.append(
                f"node {no.node_id!r}: base_duration_minutes must be non-negative."
            )
        if no.actor_id is not None and no.actor_id not in all_actor_ids:
            errors.append(
                f"node {no.node_id!r}: reassigned actor_id {no.actor_id!r} not found."
            )

    # Validate edge overrides
    for eo in config.edge_overrides:
        key = (eo.source, eo.target)
        if key not in all_edges:
            errors.append(
                f"edge ({eo.source!r} → {eo.target!r}) not found in {config.base_scenario_slug}."
            )
        if not 0.0 <= eo.probability <= 1.0:
            errors.append(
                f"edge ({eo.source!r} → {eo.target!r}): probability {eo.probability} must be 0–1."
            )

    if errors:
        raise ConfigValidationError(
            "ScenarioConfig validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    # Check edge probability sums after overrides (per workflow)
    for wf in (before_wf, after_wf):
        edge_probs_by_source: dict[str, dict[str, float]] = {}
        for edge in wf.edges:
            edge_probs_by_source.setdefault(edge.source, {})[edge.target] = edge.probability
        # Apply overrides
        eo_map = {(eo.source, eo.target): eo.probability for eo in config.edge_overrides}
        for (src, tgt), prob in eo_map.items():
            if src in edge_probs_by_source and tgt in edge_probs_by_source.get(src, {}):
                edge_probs_by_source[src][tgt] = prob
        # Check sums
        for src, targets in edge_probs_by_source.items():
            total = sum(targets.values())
            if abs(total - 1.0) > 1e-6:
                raise ConfigValidationError(
                    f"After edge overrides, outgoing probabilities from node {src!r} "
                    f"sum to {total:.4f} (expected 1.0) in workflow {wf.workflow_id!r}."
                )

    # Warnings
    if not config.actor_overrides and not config.node_overrides and not config.edge_overrides:
        warnings.append(
            "No overrides specified; this config will produce the same "
            "results as the base scenario."
        )
    if not config.client_name:
        warnings.append("client_name is empty; consider adding a client name for report clarity.")

    return warnings


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def apply_scenario_config(config: ScenarioConfig, scenario=None):
    """Build configured (before, after) workflows from a ``ScenarioConfig``.

    Applies overrides in this order:
    1. Assumption profile multipliers (``apply_profile_to_workflow``).
    2. Actor overrides (cost, error rate, etc.).
    3. Node overrides (duration, actor reassignment, etc.).
    4. Edge probability overrides.
    5. Workflow metadata overrides (names, descriptions).

    The original scenario workflows are **never mutated**.

    Args:
        config: A validated :class:`ScenarioConfig`.
        scenario: Optional pre-loaded scenario definition.

    Returns:
        A ``(before_workflow, after_workflow)`` tuple of new ``Workflow``
        instances that have been validated.

    Raises:
        ConfigValidationError: If applying the config fails validation.
    """
    from dataclasses import replace as dc_replace

    from b2b_workflow_simulator.assumptions import apply_profile_to_workflow
    from b2b_workflow_simulator.pool import ActorPool
    from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
    from b2b_workflow_simulator.primitives.human import HumanActor
    from b2b_workflow_simulator.scenarios import get_scenario
    from b2b_workflow_simulator.workflow import Workflow

    if scenario is None:
        scenario = get_scenario(config.base_scenario_slug)

    profiles = {
        "base": scenario.default_assumption_profile,
        "conservative": scenario.conservative_assumption_profile,
        "aggressive": scenario.aggressive_assumption_profile,
    }
    if config.profile_name not in profiles:
        raise ConfigValidationError(
            f"profile_name {config.profile_name!r} is not valid."
        )
    profile = profiles[config.profile_name]

    actor_overrides = {ao.actor_id: ao for ao in config.actor_overrides}
    node_overrides = {no.node_id: no for no in config.node_overrides}
    edge_overrides = {(eo.source, eo.target): eo.probability for eo in config.edge_overrides}

    def _apply_to_wf(raw_wf: Workflow, name_override: str | None, desc_override: str | None):
        # Step 1: apply profile multipliers
        wf = apply_profile_to_workflow(raw_wf, profile)

        new_name = name_override if name_override else wf.name
        new_desc = desc_override if desc_override else wf.description

        new_wf = Workflow(
            workflow_id=wf.workflow_id,
            name=new_name,
            entry_node_id=wf.entry_node_id,
            description=new_desc,
        )

        # Step 2: actors
        for actor_id, actor in wf.actors.items():
            ao = actor_overrides.get(actor_id)
            if ao is not None:
                kwargs: dict = {}
                if ao.name is not None:
                    kwargs["name"] = ao.name
                if ao.available_hours_per_day is not None:
                    kwargs["available_hours_per_day"] = ao.available_hours_per_day
                if isinstance(actor, HumanActor):
                    if ao.hourly_cost is not None:
                        kwargs["hourly_cost"] = ao.hourly_cost
                    if ao.speed_multiplier is not None:
                        kwargs["speed_multiplier"] = ao.speed_multiplier
                    if ao.error_rate is not None:
                        kwargs["error_rate"] = ao.error_rate
                elif isinstance(actor, AIAgentActor):
                    if ao.cost_per_execution is not None:
                        kwargs["cost_per_execution"] = ao.cost_per_execution
                    if ao.speed_multiplier is not None:
                        kwargs["speed_multiplier"] = ao.speed_multiplier
                    if ao.error_rate is not None:
                        kwargs["error_rate"] = ao.error_rate
                    if ao.escalation_rate is not None:
                        kwargs["escalation_rate"] = ao.escalation_rate
                elif isinstance(actor, ActorPool):
                    pass  # Pool-level overrides not supported; apply at worker level separately
                new_actor = dc_replace(actor, **kwargs) if kwargs else actor
            else:
                new_actor = actor
            new_wf.add_actor(new_actor)

        # Step 3: nodes
        for node_id, node in wf.nodes.items():
            no = node_overrides.get(node_id)
            if no is not None:
                kwargs = {}
                if no.name is not None:
                    kwargs["name"] = no.name
                if no.base_duration_minutes is not None:
                    kwargs["base_duration_minutes"] = no.base_duration_minutes
                if no.actor_id is not None:
                    kwargs["actor_id"] = no.actor_id
                if no.is_terminal is not None:
                    kwargs["is_terminal"] = no.is_terminal
                new_node = dc_replace(node, **kwargs) if kwargs else node
            else:
                new_node = node
            new_wf.add_node(new_node)

        # Step 4: edges
        for edge in wf.edges:
            key = (edge.source, edge.target)
            if key in edge_overrides:
                new_edge = dc_replace(edge, probability=edge_overrides[key])
            else:
                new_edge = edge
            new_wf.add_edge(new_edge)

        try:
            new_wf.validate()
        except ValueError as exc:
            raise ConfigValidationError(
                f"Configured workflow {wf.workflow_id!r} failed validation: {exc}"
            ) from exc
        return new_wf

    meta = config.workflow_metadata
    before_name = meta.workflow_name_before if meta else None
    before_desc = meta.description_before if meta else None
    after_name = meta.workflow_name_after if meta else None
    after_desc = meta.description_after if meta else None

    before_wf = _apply_to_wf(scenario.before_builder(), before_name, before_desc)
    after_wf = _apply_to_wf(scenario.after_builder(), after_name, after_desc)
    return before_wf, after_wf


__all__ = [
    "ActorOverride",
    "ConfigValidationError",
    "EdgeOverride",
    "NodeOverride",
    "ScenarioConfig",
    "WorkflowMetadataOverride",
    "apply_scenario_config",
    "load_scenario_config",
    "save_scenario_config",
    "validate_scenario_config",
]
