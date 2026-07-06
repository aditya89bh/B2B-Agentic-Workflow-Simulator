"""Tests for the configured case study export."""

from __future__ import annotations

import json
from pathlib import Path

from b2b_workflow_simulator.configured_case_study import generate_configured_case_study
from b2b_workflow_simulator.scenario_config import (
    ActorOverride,
    ScenarioConfig,
    load_scenario_config,
)

_CONFIGS_DIR = (
    Path(__file__).parent.parent
    / "src/b2b_workflow_simulator/examples/data/configs"
)

_EXPECTED_FILES = {
    "README.md",
    "executive_snapshot.txt",
    "executive_snapshot.html",
    "workflow_before.mmd",
    "workflow_after.mmd",
    "roi_waterfall.svg",
    "bottleneck_heatmap.svg",
    "assumptions.json",
    "config.json",
    "config_diff.txt",
    "config_diff.json",
    "kpi_summary.json",
    "recommendations.txt",
}


def _config():
    return ScenarioConfig(
        base_scenario_slug="it-support-triage",
        configured_slug="it-test",
        configured_name="IT Test",
        client_name="Test Corp",
        actor_overrides=[ActorOverride(actor_id="l1_agent", hourly_cost=22.0)],
    )


def test_creates_all_expected_files(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    created = {f.name for f in tmp_path.iterdir() if f.is_file()}
    for expected in _EXPECTED_FILES:
        assert expected in created, f"Missing: {expected}"


def test_config_json_is_valid(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    data = json.loads((tmp_path / "config.json").read_text())
    assert data["configured_slug"] == "it-test"


def test_kpi_summary_json_is_valid(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    data = json.loads((tmp_path / "kpi_summary.json").read_text())
    assert "before" in data and "after" in data


def test_config_diff_json_is_valid(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    data = json.loads((tmp_path / "config_diff.json").read_text())
    assert "base_scenario_slug" in data


def test_readme_has_validation_warning(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    readme = (tmp_path / "README.md").read_text()
    assert "validate" in readme.lower() or "real" in readme.lower()


def test_mermaid_files_start_with_flowchart(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    for fname in ("workflow_before.mmd", "workflow_after.mmd"):
        assert (tmp_path / fname).read_text().startswith("flowchart LR")


def test_svg_files_are_valid(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    for fname in ("roi_waterfall.svg", "bottleneck_heatmap.svg"):
        content = (tmp_path / fname).read_text()
        assert "<svg" in content and "</svg>" in content


def test_html_is_valid(tmp_path):
    generate_configured_case_study(_config(), tmp_path)
    html = (tmp_path / "executive_snapshot.html").read_text()
    assert "<!DOCTYPE html>" in html


def test_no_unsafe_filenames(tmp_path):
    files = generate_configured_case_study(_config(), tmp_path)
    for filename in files:
        assert "/" not in filename and ".." not in filename


def test_deterministic(tmp_path):
    d1 = tmp_path / "r1"
    d2 = tmp_path / "r2"
    generate_configured_case_study(_config(), d1)
    generate_configured_case_study(_config(), d2)
    kpi1 = json.loads((d1 / "kpi_summary.json").read_text())
    kpi2 = json.loads((d2 / "kpi_summary.json").read_text())
    assert kpi1 == kpi2


def test_sample_config_generates_case_study(tmp_path):
    config = load_scenario_config(_CONFIGS_DIR / "it-support-triage-managed-service.json")
    files = generate_configured_case_study(config, tmp_path)
    assert "README.md" in files
    assert "config_diff.txt" in files
