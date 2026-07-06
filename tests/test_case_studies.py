"""Tests for the case_studies module."""

from __future__ import annotations

import json

from b2b_workflow_simulator.case_studies import generate_all_case_studies, generate_case_study
from b2b_workflow_simulator.scenarios import get_scenario

_EXPECTED_BASE_FILES = {
    "README.md",
    "workflow_before.mmd",
    "workflow_after.mmd",
    "roi_waterfall_base.svg",
    "bottleneck_heatmap_base.svg",
    "executive_snapshot_base.txt",
    "assumptions_base.json",
    "kpi_summary_base.json",
}


def _get_scenario():
    return get_scenario("it-support-triage")


def test_generate_case_study_creates_directory(tmp_path):
    scenario = _get_scenario()
    generate_case_study(scenario, tmp_path / "output", profiles=["base"])
    assert (tmp_path / "output").is_dir()


def test_generate_case_study_creates_expected_files(tmp_path):
    scenario = _get_scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    created = {f.name for f in tmp_path.iterdir()}
    for expected in _EXPECTED_BASE_FILES:
        assert expected in created, f"Missing file: {expected}"


def test_generate_case_study_returns_file_mapping(tmp_path):
    scenario = _get_scenario()
    files = generate_case_study(scenario, tmp_path, profiles=["base"])
    assert "README.md" in files
    assert files["README.md"].exists()


def test_mermaid_files_start_with_flowchart(tmp_path):
    scenario = _get_scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    for fname in ("workflow_before.mmd", "workflow_after.mmd"):
        assert (tmp_path / fname).read_text().startswith("flowchart LR")


def test_svg_files_are_valid(tmp_path):
    scenario = _get_scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    for fname in ("roi_waterfall_base.svg", "bottleneck_heatmap_base.svg"):
        content = (tmp_path / fname).read_text()
        assert "<svg" in content and "</svg>" in content


def test_kpi_summary_json_valid(tmp_path):
    scenario = _get_scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    data = json.loads((tmp_path / "kpi_summary_base.json").read_text())
    assert "before" in data and "after" in data
    assert "completion_rate" in data["before"]


def test_assumptions_json_valid(tmp_path):
    scenario = _get_scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    data = json.loads((tmp_path / "assumptions_base.json").read_text())
    assert "num_cases" in data


def test_readme_contains_limitations(tmp_path):
    scenario = _get_scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    readme = (tmp_path / "README.md").read_text()
    assert any(lim[:30] in readme for lim in scenario.limitations)


def test_three_profiles_generate_three_sets(tmp_path):
    scenario = _get_scenario()
    files = generate_case_study(scenario, tmp_path, profiles=["base", "conservative", "aggressive"])
    for profile_name in ("base", "conservative", "aggressive"):
        assert f"executive_snapshot_{profile_name}.txt" in files
        assert f"kpi_summary_{profile_name}.json" in files
        assert f"assumptions_{profile_name}.json" in files


def test_deterministic_output(tmp_path):
    scenario = _get_scenario()
    d1 = tmp_path / "r1"
    d2 = tmp_path / "r2"
    generate_case_study(scenario, d1, profiles=["base"])
    generate_case_study(scenario, d2, profiles=["base"])
    kpi1 = json.loads((d1 / "kpi_summary_base.json").read_text())
    kpi2 = json.loads((d2 / "kpi_summary_base.json").read_text())
    assert kpi1 == kpi2


def test_generate_all_case_studies_subset(tmp_path):
    results = generate_all_case_studies(
        tmp_path,
        scenario_slugs=["it-support-triage", "hr-recruiting-screening"],
        profiles=["base"],
    )
    assert set(results.keys()) == {"it-support-triage", "hr-recruiting-screening"}


def test_generate_all_case_studies_all_scenarios(tmp_path):
    results = generate_all_case_studies(tmp_path, profiles=["base"])
    from b2b_workflow_simulator.scenarios import scenario_names
    assert set(results.keys()) == set(scenario_names())
