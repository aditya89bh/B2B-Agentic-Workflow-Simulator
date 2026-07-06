"""Tests for scenario_config: ScenarioConfig model, validation, and apply."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from b2b_workflow_simulator.scenario_config import (
    ActorOverride,
    ConfigValidationError,
    EdgeOverride,
    NodeOverride,
    ScenarioConfig,
    WorkflowMetadataOverride,
    apply_scenario_config,
    load_scenario_config,
    save_scenario_config,
    validate_scenario_config,
)
from b2b_workflow_simulator.scenarios import get_scenario
from b2b_workflow_simulator.simulation import SimulationRunner


def _base_config() -> ScenarioConfig:
    return ScenarioConfig(
        base_scenario_slug="healthcare-prior-authorization",
        configured_slug="test-config",
        configured_name="Test Config",
        client_name="Test Client",
    )


def _scenario():
    return get_scenario("healthcare-prior-authorization")


# ---------------------------------------------------------------------------
# Load / save round trip
# ---------------------------------------------------------------------------


def test_load_save_round_trip():
    config = _base_config()
    config.actor_overrides = [ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.json"
        save_scenario_config(config, path)
        loaded = load_scenario_config(path)
    assert loaded.configured_slug == config.configured_slug
    assert loaded.actor_overrides[0].hourly_cost == 60.0


def test_save_creates_parent_directory(tmp_path):
    config = _base_config()
    path = tmp_path / "nested" / "dir" / "config.json"
    save_scenario_config(config, path)
    assert path.exists()


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_scenario_config("/nonexistent/path.json")


def test_load_invalid_json_raises():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.json"
        path.write_text("{not json")
        with pytest.raises(ConfigValidationError):
            load_scenario_config(path)


def test_load_missing_required_field_raises():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "incomplete.json"
        path.write_text(json.dumps({"configured_slug": "x"}))
        with pytest.raises(ConfigValidationError):
            load_scenario_config(path)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_valid_config_returns_warnings():
    config = _base_config()
    warnings = validate_scenario_config(config)
    assert isinstance(warnings, list)


def test_no_overrides_warning():
    config = _base_config()
    warnings = validate_scenario_config(config)
    assert any("No overrides" in w for w in warnings)


def test_unknown_base_scenario_raises():
    config = ScenarioConfig(
        base_scenario_slug="no-such-scenario",
        configured_slug="x",
        configured_name="x",
    )
    with pytest.raises(ConfigValidationError, match="no-such-scenario"):
        validate_scenario_config(config)


def test_unknown_actor_id_raises():
    config = _base_config()
    config.actor_overrides = [ActorOverride(actor_id="no_such_actor", hourly_cost=50.0)]
    with pytest.raises(ConfigValidationError, match="actor_id"):
        validate_scenario_config(config)


def test_unknown_node_id_raises():
    config = _base_config()
    config.node_overrides = [NodeOverride(node_id="no_such_node", base_duration_minutes=10.0)]
    with pytest.raises(ConfigValidationError, match="node_id"):
        validate_scenario_config(config)


def test_unknown_edge_raises():
    config = _base_config()
    config.edge_overrides = [EdgeOverride(source="no_such", target="node", probability=0.5)]
    with pytest.raises(ConfigValidationError, match="edge"):
        validate_scenario_config(config)


def test_invalid_error_rate_raises():
    config = _base_config()
    config.actor_overrides = [ActorOverride(actor_id="clinical_reviewer", error_rate=1.5)]
    with pytest.raises(ConfigValidationError, match="error_rate"):
        validate_scenario_config(config)


def test_invalid_edge_probability_sum_raises():
    config = _base_config()
    config.edge_overrides = [
        EdgeOverride(source="pa_intake", target="clinical_review", probability=0.50),
    ]
    with pytest.raises(ConfigValidationError, match="sum"):
        validate_scenario_config(config)


def test_valid_edge_probability_set():
    config = _base_config()
    config.edge_overrides = [
        EdgeOverride(source="pa_intake", target="clinical_review", probability=0.80),
        EdgeOverride(source="pa_intake", target="incomplete_return", probability=0.20),
    ]
    warnings = validate_scenario_config(config)
    assert isinstance(warnings, list)


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def test_apply_actor_override():
    config = _base_config()
    config.actor_overrides = [ActorOverride(actor_id="clinical_reviewer", hourly_cost=60.0)]
    before_wf, _ = apply_scenario_config(config)
    actor = before_wf.get_actor("clinical_reviewer")
    assert actor.hourly_cost == pytest.approx(60.0)


def test_apply_node_override():
    config = _base_config()
    config.node_overrides = [NodeOverride(node_id="pa_intake", base_duration_minutes=30.0)]
    before_wf, _ = apply_scenario_config(config)
    node = before_wf.get_node("pa_intake")
    assert node.base_duration_minutes == pytest.approx(30.0)


def test_apply_edge_override():
    config = _base_config()
    config.edge_overrides = [
        EdgeOverride(source="pa_intake", target="clinical_review", probability=0.88),
        EdgeOverride(source="pa_intake", target="incomplete_return", probability=0.12),
    ]
    before_wf, _ = apply_scenario_config(config)
    edges = {(e.source, e.target): e.probability for e in before_wf.edges}
    assert edges[("pa_intake", "clinical_review")] == pytest.approx(0.88)
    assert edges[("pa_intake", "incomplete_return")] == pytest.approx(0.12)


def test_apply_metadata_override():
    config = _base_config()
    config.workflow_metadata = WorkflowMetadataOverride(
        workflow_name_before="Custom Before Name",
        workflow_name_after="Custom After Name",
    )
    before_wf, after_wf = apply_scenario_config(config)
    assert before_wf.name == "Custom Before Name"
    assert after_wf.name == "Custom After Name"


def test_original_workflow_not_mutated():
    scenario = _scenario()
    original_before = scenario.before_builder()
    original_actor = original_before.get_actor("clinical_reviewer")
    original_cost = original_actor.hourly_cost

    config = _base_config()
    config.actor_overrides = [ActorOverride(actor_id="clinical_reviewer", hourly_cost=1.0)]
    apply_scenario_config(config, scenario)

    fresh = scenario.before_builder().get_actor("clinical_reviewer")
    assert fresh.hourly_cost == pytest.approx(original_cost)


def test_configured_workflow_validates():
    config = _base_config()
    config.actor_overrides = [ActorOverride(actor_id="clinical_reviewer", hourly_cost=65.0)]
    before_wf, after_wf = apply_scenario_config(config)
    before_wf.validate()
    after_wf.validate()


def test_overrides_produce_different_kpis():
    config_base = _base_config()
    config_overridden = _base_config()
    config_overridden.actor_overrides = [
        ActorOverride(actor_id="clinical_reviewer", error_rate=0.15),
    ]
    bwf1, awf1 = apply_scenario_config(config_base)
    bwf2, awf2 = apply_scenario_config(config_overridden)

    kpi1 = SimulationRunner(seed=42).run(bwf1, 200, collect_events=False).kpi
    kpi2 = SimulationRunner(seed=42).run(bwf2, 200, collect_events=False).kpi
    assert kpi1.failed_cases != kpi2.failed_cases or kpi1.total_cost != kpi2.total_cost
