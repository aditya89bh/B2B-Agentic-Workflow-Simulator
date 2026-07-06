"""Tests for config_diff module."""

from __future__ import annotations

import json

import pytest

from b2b_workflow_simulator.config_diff import (
    build_config_diff,
    config_diff_to_json,
    config_diff_to_text,
)
from b2b_workflow_simulator.scenario_config import (
    ActorOverride,
    EdgeOverride,
    NodeOverride,
    ScenarioConfig,
    WorkflowMetadataOverride,
)


def _config(**kwargs) -> ScenarioConfig:
    return ScenarioConfig(
        base_scenario_slug="healthcare-prior-authorization",
        configured_slug="test",
        configured_name="Test",
        **kwargs,
    )


def test_no_changes_triggers_warning():
    config = _config()
    diff = build_config_diff(config)
    assert any("No meaningful overrides" in w for w in diff.warnings)


def test_actor_change_detected():
    config = _config(actor_overrides=[
        ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)
    ])
    diff = build_config_diff(config)
    assert len(diff.actor_changes) >= 1
    change = next(c for c in diff.actor_changes if c.field == "hourly_cost")
    assert change.actor_id == "clinical_reviewer"
    assert change.new_value == pytest.approx(60.0)


def test_node_duration_change_detected():
    config = _config(node_overrides=[
        NodeOverride(node_id="pa_intake", base_duration_minutes=30.0)
    ])
    diff = build_config_diff(config)
    assert len(diff.node_changes) >= 1
    change = next(c for c in diff.node_changes if c.field == "base_duration_minutes")
    assert change.new_value == pytest.approx(30.0)


def test_edge_change_detected():
    config = _config(edge_overrides=[
        EdgeOverride(source="pa_intake", target="clinical_review", probability=0.88),
        EdgeOverride(source="pa_intake", target="incomplete_return", probability=0.12),
    ])
    diff = build_config_diff(config)
    assert len(diff.edge_changes) >= 1


def test_metadata_change_detected():
    config = _config(workflow_metadata=WorkflowMetadataOverride(
        workflow_name_before="Custom Before"
    ))
    diff = build_config_diff(config)
    assert len(diff.metadata_changes) >= 1
    change = next(c for c in diff.metadata_changes if c.field == "workflow_name_before")
    assert change.new_value == "Custom Before"


def test_high_risk_ai_error_reduction():
    from b2b_workflow_simulator.examples import healthcare_prior_authorization as h
    wf = h.build_after_workflow()
    ai_actor_id = next(
        aid for aid, a in wf.actors.items()
        if hasattr(a, "error_rate") and a.error_rate > 0 and hasattr(a, "cost_per_execution")
    )
    actor = wf.get_actor(ai_actor_id)
    very_low = actor.error_rate * 0.3  # 70% reduction → high risk
    config = _config(actor_overrides=[
        ActorOverride(actor_id=ai_actor_id, error_rate=very_low)
    ])
    diff = build_config_diff(config)
    risky = [c for c in diff.actor_changes if c.is_high_risk]
    assert len(risky) >= 1
    assert any("error_rate" in c.field for c in risky)


def test_high_risk_duration_reduction():
    config = _config(node_overrides=[
        NodeOverride(node_id="pa_intake", base_duration_minutes=1.0)  # 95% reduction
    ])
    diff = build_config_diff(config)
    risky = [c for c in diff.node_changes if c.is_high_risk]
    assert len(risky) >= 1


def test_has_high_risk_changes_property():
    config = _config(node_overrides=[
        NodeOverride(node_id="pa_intake", base_duration_minutes=1.0)
    ])
    diff = build_config_diff(config)
    assert diff.has_high_risk_changes


def test_total_changes_count():
    config = _config(
        actor_overrides=[ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)],
        node_overrides=[NodeOverride(node_id="pa_intake", base_duration_minutes=25.0)],
    )
    diff = build_config_diff(config)
    assert diff.total_changes >= 2


def test_text_output_contains_changes():
    config = _config(actor_overrides=[
        ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)
    ])
    diff = build_config_diff(config)
    text = config_diff_to_text(diff)
    assert "clinical_reviewer" in text
    assert "hourly_cost" in text


def test_text_deterministic():
    config = _config(actor_overrides=[
        ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)
    ])
    diff = build_config_diff(config)
    assert config_diff_to_text(diff) == config_diff_to_text(diff)


def test_json_output_valid():
    config = _config(actor_overrides=[
        ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)
    ])
    diff = build_config_diff(config)
    data = json.loads(config_diff_to_json(diff))
    assert "base_scenario_slug" in data
    assert "actor_changes" in data


def test_json_deterministic():
    config = _config(actor_overrides=[
        ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)
    ])
    diff = build_config_diff(config)
    assert config_diff_to_json(diff) == config_diff_to_json(diff)
