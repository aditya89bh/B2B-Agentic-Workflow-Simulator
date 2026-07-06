"""Assumption/configuration diff: explain how a configured scenario differs from base.

``build_config_diff`` compares a :class:`~b2b_workflow_simulator.scenario_config.ScenarioConfig`
against the base scenario and surfaces every meaningful change — actor cost
changes, node duration changes, edge probability shifts, and metadata
updates — in a structured, reportable form.

High-risk assumption warnings are raised when overrides push values beyond
thresholds that suggest the analysis may over-estimate benefits.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

_HIGH_RISK_AI_ERROR_REDUCTION = 0.50
_HIGH_RISK_AI_COST_REDUCTION = 0.70
_HIGH_RISK_HUMAN_COST_REDUCTION = 0.40
_HIGH_RISK_EDGE_CHANGE = 0.30
_HIGH_RISK_DURATION_REDUCTION = 0.60


@dataclass
class ActorChange:
    """One actor field that changed between base and configured scenario.

    Attributes:
        actor_id: Actor identifier.
        field: Name of the changed field.
        base_value: Original value.
        new_value: Overridden value.
        is_high_risk: Whether this change exceeds a high-risk threshold.
        warning: Human-readable warning when ``is_high_risk`` is True.
    """

    actor_id: str
    field: str
    base_value: float | str | None
    new_value: float | str | None
    is_high_risk: bool = False
    warning: str = ""


@dataclass
class NodeChange:
    """One node field that changed.

    Attributes:
        node_id: Node identifier.
        field: Name of the changed field.
        base_value: Original value.
        new_value: Overridden value.
        is_high_risk: Whether this change exceeds a high-risk threshold.
        warning: Human-readable warning.
    """

    node_id: str
    field: str
    base_value: float | str | None
    new_value: float | str | None
    is_high_risk: bool = False
    warning: str = ""


@dataclass
class EdgeChange:
    """One edge probability change.

    Attributes:
        source: Source node ID.
        target: Target node ID.
        base_probability: Original probability.
        new_probability: Overridden probability.
        delta: ``new_probability - base_probability``.
        is_high_risk: Whether the change exceeds the high-risk threshold.
        warning: Human-readable warning.
    """

    source: str
    target: str
    base_probability: float
    new_probability: float
    delta: float
    is_high_risk: bool = False
    warning: str = ""


@dataclass
class MetadataChange:
    """A workflow name or description change.

    Attributes:
        field: ``"workflow_name_before"``, ``"workflow_name_after"``, etc.
        base_value: Original value.
        new_value: Overridden value.
    """

    field: str
    base_value: str
    new_value: str


@dataclass
class ConfigDiff:
    """Complete diff between a base scenario and a configured variant.

    Attributes:
        base_scenario_slug: Slug of the base scenario.
        configured_slug: Slug of the configured variant.
        profile_name: Profile used.
        actor_changes: List of actor field changes.
        node_changes: List of node field changes.
        edge_changes: List of edge probability changes.
        metadata_changes: List of metadata changes.
        warnings: Non-fatal warnings (no-change, high-risk, etc.).
        has_high_risk_changes: ``True`` if any change exceeds a risk threshold.
    """

    base_scenario_slug: str
    configured_slug: str
    profile_name: str
    actor_changes: list[ActorChange] = field(default_factory=list)
    node_changes: list[NodeChange] = field(default_factory=list)
    edge_changes: list[EdgeChange] = field(default_factory=list)
    metadata_changes: list[MetadataChange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_high_risk_changes(self) -> bool:
        """``True`` when any change triggers a high-risk warning."""
        return (
            any(c.is_high_risk for c in self.actor_changes)
            or any(c.is_high_risk for c in self.node_changes)
            or any(c.is_high_risk for c in self.edge_changes)
        )

    @property
    def total_changes(self) -> int:
        """Total number of changed fields."""
        return (
            len(self.actor_changes) + len(self.node_changes)
            + len(self.edge_changes) + len(self.metadata_changes)
        )


def build_config_diff(config, scenario=None) -> ConfigDiff:
    """Build a :class:`ConfigDiff` from a ``ScenarioConfig``.

    Args:
        config: The :class:`~b2b_workflow_simulator.scenario_config.ScenarioConfig`
            to diff.
        scenario: Optional pre-loaded scenario definition.

    Returns:
        A :class:`ConfigDiff` describing every change.
    """
    from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
    from b2b_workflow_simulator.primitives.human import HumanActor
    from b2b_workflow_simulator.scenarios import get_scenario

    if scenario is None:
        scenario = get_scenario(config.base_scenario_slug)

    before_wf = scenario.before_builder()
    after_wf = scenario.after_builder()
    all_actors = {**before_wf.actors, **after_wf.actors}

    diff = ConfigDiff(
        base_scenario_slug=config.base_scenario_slug,
        configured_slug=config.configured_slug,
        profile_name=config.profile_name,
    )

    # Actor changes
    for ao in config.actor_overrides:
        actor = all_actors.get(ao.actor_id)
        if actor is None:
            continue
        if isinstance(actor, HumanActor):
            if ao.hourly_cost is not None and ao.hourly_cost != actor.hourly_cost:
                base = actor.hourly_cost
                reduction = (base - ao.hourly_cost) / max(base, 1e-9)
                risk = reduction > _HIGH_RISK_HUMAN_COST_REDUCTION
                diff.actor_changes.append(ActorChange(
                    actor_id=ao.actor_id, field="hourly_cost",
                    base_value=base, new_value=ao.hourly_cost,
                    is_high_risk=risk,
                    warning=(
                        f"hourly_cost reduced by {reduction:.0%} "
                        f"(threshold: {_HIGH_RISK_HUMAN_COST_REDUCTION:.0%})"
                    ) if risk else "",
                ))
            if ao.error_rate is not None and ao.error_rate != actor.error_rate:
                diff.actor_changes.append(ActorChange(
                    actor_id=ao.actor_id, field="error_rate",
                    base_value=actor.error_rate, new_value=ao.error_rate,
                ))
        elif isinstance(actor, AIAgentActor):
            if (ao.cost_per_execution is not None
                    and ao.cost_per_execution != actor.cost_per_execution):
                base = actor.cost_per_execution
                reduction = (base - ao.cost_per_execution) / max(base, 1e-9) if base > 0 else 0.0
                risk = reduction > _HIGH_RISK_AI_COST_REDUCTION
                diff.actor_changes.append(ActorChange(
                    actor_id=ao.actor_id, field="cost_per_execution",
                    base_value=base, new_value=ao.cost_per_execution,
                    is_high_risk=risk,
                    warning=(
                        f"AI cost reduced by {reduction:.0%} "
                        f"(threshold: {_HIGH_RISK_AI_COST_REDUCTION:.0%})"
                    ) if risk else "",
                ))
            if ao.error_rate is not None and ao.error_rate != actor.error_rate:
                base_er = actor.error_rate
                reduction = (base_er - ao.error_rate) / max(base_er, 1e-9) if base_er > 0 else 0.0
                risk = reduction > _HIGH_RISK_AI_ERROR_REDUCTION
                diff.actor_changes.append(ActorChange(
                    actor_id=ao.actor_id, field="error_rate",
                    base_value=base_er, new_value=ao.error_rate,
                    is_high_risk=risk,
                    warning=(
                        f"AI error_rate reduced by {reduction:.0%} "
                        f"(threshold: {_HIGH_RISK_AI_ERROR_REDUCTION:.0%})"
                    ) if risk else "",
                ))
            if ao.escalation_rate is not None and ao.escalation_rate != actor.escalation_rate:
                diff.actor_changes.append(ActorChange(
                    actor_id=ao.actor_id, field="escalation_rate",
                    base_value=actor.escalation_rate, new_value=ao.escalation_rate,
                ))
        base_sm = getattr(actor, "speed_multiplier", None)
        if ao.speed_multiplier is not None and ao.speed_multiplier != base_sm:
            diff.actor_changes.append(ActorChange(
                actor_id=ao.actor_id, field="speed_multiplier",
                base_value=getattr(actor, "speed_multiplier", None), new_value=ao.speed_multiplier,
            ))
        if ao.name is not None and ao.name != actor.name:
            diff.actor_changes.append(ActorChange(
                actor_id=ao.actor_id, field="name",
                base_value=actor.name, new_value=ao.name,
            ))

    # Node changes
    all_nodes = {**before_wf.nodes, **after_wf.nodes}
    for no in config.node_overrides:
        node = all_nodes.get(no.node_id)
        if node is None:
            continue
        if (no.base_duration_minutes is not None
                and no.base_duration_minutes != node.base_duration_minutes):
            base_dur = node.base_duration_minutes
            reduction = (base_dur - no.base_duration_minutes) / max(base_dur, 1e-9)
            risk = reduction > _HIGH_RISK_DURATION_REDUCTION
            diff.node_changes.append(NodeChange(
                node_id=no.node_id, field="base_duration_minutes",
                base_value=base_dur, new_value=no.base_duration_minutes,
                is_high_risk=risk,
                warning=(
                    f"duration reduced by {reduction:.0%} "
                    f"(threshold: {_HIGH_RISK_DURATION_REDUCTION:.0%})"
                ) if risk else "",
            ))
        if no.name is not None and no.name != node.name:
            diff.node_changes.append(NodeChange(
                node_id=no.node_id, field="name",
                base_value=node.name, new_value=no.name,
            ))
        if no.actor_id is not None and no.actor_id != node.actor_id:
            diff.node_changes.append(NodeChange(
                node_id=no.node_id, field="actor_id",
                base_value=node.actor_id, new_value=no.actor_id,
            ))

    # Edge changes
    all_edges_before = {(e.source, e.target): e.probability for e in before_wf.edges}
    all_edges_after = {(e.source, e.target): e.probability for e in after_wf.edges}
    all_edges = {**all_edges_before, **all_edges_after}
    for eo in config.edge_overrides:
        key = (eo.source, eo.target)
        base_prob = all_edges.get(key)
        if base_prob is None:
            continue
        delta = eo.probability - base_prob
        risk = abs(delta) > _HIGH_RISK_EDGE_CHANGE
        diff.edge_changes.append(EdgeChange(
            source=eo.source, target=eo.target,
            base_probability=base_prob, new_probability=eo.probability,
            delta=delta,
            is_high_risk=risk,
            warning=(
                f"probability changed by {delta:+.2f} "
                f"(threshold: ±{_HIGH_RISK_EDGE_CHANGE:.2f})"
            ) if risk else "",
        ))

    # Metadata changes
    if config.workflow_metadata:
        meta = config.workflow_metadata
        for field_name, base_name, new_name in [
            ("workflow_name_before", before_wf.name, meta.workflow_name_before),
            ("workflow_name_after", after_wf.name, meta.workflow_name_after),
            ("description_before", before_wf.description, meta.description_before),
            ("description_after", after_wf.description, meta.description_after),
        ]:
            if new_name is not None and new_name != base_name:
                diff.metadata_changes.append(MetadataChange(
                    field=field_name, base_value=base_name or "", new_value=new_name,
                ))

    # Warnings
    if diff.total_changes == 0:
        diff.warnings.append(
            "No meaningful overrides specified; results will match the base scenario."
        )
    for change in diff.actor_changes + diff.node_changes + diff.edge_changes:
        if change.is_high_risk:
            diff.warnings.append(f"High-risk assumption: {change.warning}")

    return diff


def config_diff_to_text(diff: ConfigDiff) -> str:
    """Render a :class:`ConfigDiff` as a plain-text report."""
    lines: list[str] = [
        "=" * 64,
        f"CONFIG DIFF: {diff.configured_slug}",
        f"Base scenario: {diff.base_scenario_slug}  Profile: {diff.profile_name}",
        "=" * 64,
        "",
    ]
    if diff.actor_changes:
        lines.append("Actor changes:")
        for c in diff.actor_changes:
            risk_flag = "  ⚠ HIGH RISK" if c.is_high_risk else ""
            lines.append(
                f"  {c.actor_id}.{c.field}: {c.base_value} → {c.new_value}{risk_flag}"
            )
        lines.append("")
    if diff.node_changes:
        lines.append("Node changes:")
        for c in diff.node_changes:
            risk_flag = "  ⚠ HIGH RISK" if c.is_high_risk else ""
            lines.append(
                f"  {c.node_id}.{c.field}: {c.base_value} → {c.new_value}{risk_flag}"
            )
        lines.append("")
    if diff.edge_changes:
        lines.append("Edge probability changes:")
        for c in diff.edge_changes:
            risk_flag = "  ⚠ HIGH RISK" if c.is_high_risk else ""
            lines.append(
                f"  {c.source} → {c.target}: {c.base_probability:.2f} → "
                f"{c.new_probability:.2f} ({c.delta:+.2f}){risk_flag}"
            )
        lines.append("")
    if diff.metadata_changes:
        lines.append("Metadata changes:")
        for c in diff.metadata_changes:
            lines.append(f"  {c.field}: {c.base_value!r} → {c.new_value!r}")
        lines.append("")
    if diff.warnings:
        lines.append("Warnings:")
        for w in diff.warnings:
            lines.append(f"  - {w}")
    if diff.total_changes == 0:
        lines.append("No changes detected (config matches base scenario).")
    return "\n".join(lines)


def config_diff_to_json(diff: ConfigDiff) -> str:
    """Serialize a :class:`ConfigDiff` to a JSON string."""
    from dataclasses import asdict
    return json.dumps(asdict(diff), indent=2)


__all__ = [
    "ActorChange",
    "ConfigDiff",
    "EdgeChange",
    "MetadataChange",
    "NodeChange",
    "build_config_diff",
    "config_diff_to_json",
    "config_diff_to_text",
]
