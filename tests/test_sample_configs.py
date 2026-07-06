"""Tests for sample scenario configuration files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from b2b_workflow_simulator.scenario_config import (
    apply_scenario_config,
    load_scenario_config,
    validate_scenario_config,
)
from b2b_workflow_simulator.simulation import SimulationRunner

_CONFIGS_DIR = (
    Path(__file__).parent.parent
    / "src/b2b_workflow_simulator/examples/data/configs"
)
_SAMPLE_SLUGS = [
    "healthcare-prior-auth-small-plan",
    "insurance-claims-high-volume-carrier",
    "hr-recruiting-startup",
    "procurement-vendor-onboarding-enterprise",
    "legal-contract-review-midmarket",
    "it-support-triage-managed-service",
]


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_file_exists(slug):
    assert (_CONFIGS_DIR / f"{slug}.json").exists()


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_is_valid_json(slug):
    data = json.loads((_CONFIGS_DIR / f"{slug}.json").read_text())
    assert isinstance(data, dict)
    assert "base_scenario_slug" in data


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_loads(slug):
    config = load_scenario_config(_CONFIGS_DIR / f"{slug}.json")
    assert config.configured_slug == slug


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_validates(slug):
    config = load_scenario_config(_CONFIGS_DIR / f"{slug}.json")
    warnings = validate_scenario_config(config)
    assert isinstance(warnings, list)


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_applies_to_valid_workflows(slug):
    config = load_scenario_config(_CONFIGS_DIR / f"{slug}.json")
    before_wf, after_wf = apply_scenario_config(config)
    before_wf.validate()
    after_wf.validate()


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_produces_different_kpis_than_base(slug):
    from b2b_workflow_simulator.scenarios import get_scenario

    config = load_scenario_config(_CONFIGS_DIR / f"{slug}.json")
    before_configured, _ = apply_scenario_config(config)

    scenario = get_scenario(config.base_scenario_slug)
    base_profile = scenario.default_assumption_profile
    before_base = scenario.before_builder()

    from b2b_workflow_simulator.assumptions import apply_profile_to_workflow
    before_base_with_profile = apply_profile_to_workflow(before_base, base_profile)

    kpi_configured = SimulationRunner(seed=42).run(
        before_configured, 100, collect_events=False
    ).kpi
    kpi_base = SimulationRunner(seed=42).run(
        before_base_with_profile, 100, collect_events=False
    ).kpi
    differs = (
        kpi_configured.total_cost != kpi_base.total_cost
        or kpi_configured.avg_cycle_time_minutes != kpi_base.avg_cycle_time_minutes
    )
    assert differs, f"{slug}: configured KPIs should differ from base"


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_has_meaningful_overrides(slug):
    config = load_scenario_config(_CONFIGS_DIR / f"{slug}.json")
    total = (
        len(config.actor_overrides)
        + len(config.node_overrides)
        + len(config.edge_overrides)
    )
    assert total > 0, f"{slug}: should have at least one override"


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_has_limitations(slug):
    config = load_scenario_config(_CONFIGS_DIR / f"{slug}.json")
    assert len(config.limitations) >= 1


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_sample_config_has_client_name(slug):
    config = load_scenario_config(_CONFIGS_DIR / f"{slug}.json")
    assert config.client_name, f"{slug}: should have a client_name"
