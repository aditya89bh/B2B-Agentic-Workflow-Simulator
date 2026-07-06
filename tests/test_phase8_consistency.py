"""Tests for Phase 8 consistency fixes:
1. Case study generator creates consultant_packet_<profile>/ directories.
2. Scenario matrix rejects invalid profile names.
"""

from __future__ import annotations

import json

import pytest

from b2b_workflow_simulator.case_studies import generate_case_study
from b2b_workflow_simulator.cli import main
from b2b_workflow_simulator.scenario_matrix import build_scenario_matrix
from b2b_workflow_simulator.scenarios import get_scenario

_PACKET_EXPECTED_FILES = {
    "README.md",
    "executive_snapshot.txt",
    "executive_snapshot.html",
    "assumptions.json",
    "kpi_summary.json",
    "workflow_before.mmd",
    "workflow_after.mmd",
    "roi_waterfall.svg",
    "bottleneck_heatmap.svg",
    "recommendations.txt",
}


def _scenario():
    return get_scenario("it-support-triage")


# ---------------------------------------------------------------------------
# Consultant packet directories
# ---------------------------------------------------------------------------


def test_consultant_packet_base_directory_created(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    assert (tmp_path / "consultant_packet_base").is_dir()


def test_consultant_packet_conservative_directory_created(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["conservative"])
    assert (tmp_path / "consultant_packet_conservative").is_dir()


def test_consultant_packet_aggressive_directory_created(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["aggressive"])
    assert (tmp_path / "consultant_packet_aggressive").is_dir()


def test_consultant_packet_not_created_for_unrequested_profiles(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    assert not (tmp_path / "consultant_packet_conservative").exists()
    assert not (tmp_path / "consultant_packet_aggressive").exists()


def test_consultant_packet_base_contains_all_expected_files(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    packet_dir = tmp_path / "consultant_packet_base"
    created = {f.name for f in packet_dir.iterdir() if f.is_file()}
    for expected in _PACKET_EXPECTED_FILES:
        assert expected in created, (
            f"consultant_packet_base is missing: {expected!r}"
        )


def test_consultant_packet_conservative_contains_all_expected_files(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["conservative"])
    packet_dir = tmp_path / "consultant_packet_conservative"
    created = {f.name for f in packet_dir.iterdir() if f.is_file()}
    for expected in _PACKET_EXPECTED_FILES:
        assert expected in created, (
            f"consultant_packet_conservative is missing: {expected!r}"
        )


def test_consultant_packet_assumptions_json_is_valid(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    data = json.loads((tmp_path / "consultant_packet_base" / "assumptions.json").read_text())
    assert "num_cases" in data


def test_consultant_packet_kpi_summary_json_is_valid(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    data = json.loads((tmp_path / "consultant_packet_base" / "kpi_summary.json").read_text())
    assert "before" in data and "after" in data


def test_consultant_packet_mermaid_files_start_with_flowchart(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    for fname in ("workflow_before.mmd", "workflow_after.mmd"):
        content = (tmp_path / "consultant_packet_base" / fname).read_text()
        assert content.startswith("flowchart LR"), fname


def test_consultant_packet_svg_files_are_valid(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    for fname in ("roi_waterfall.svg", "bottleneck_heatmap.svg"):
        content = (tmp_path / "consultant_packet_base" / fname).read_text()
        assert "<svg" in content and "</svg>" in content, fname


def test_consultant_packet_html_is_valid_html(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path, profiles=["base"])
    html = (tmp_path / "consultant_packet_base" / "executive_snapshot.html").read_text()
    assert "<!DOCTYPE html>" in html


def test_all_three_packets_generated_by_default(tmp_path):
    scenario = _scenario()
    generate_case_study(scenario, tmp_path)
    for profile_name in ("base", "conservative", "aggressive"):
        assert (tmp_path / f"consultant_packet_{profile_name}").is_dir(), (
            f"consultant_packet_{profile_name} not created"
        )


def test_packets_are_deterministic(tmp_path):
    scenario = _scenario()
    d1 = tmp_path / "r1"
    d2 = tmp_path / "r2"
    generate_case_study(scenario, d1, profiles=["base"])
    generate_case_study(scenario, d2, profiles=["base"])
    kpi1 = json.loads((d1 / "consultant_packet_base" / "kpi_summary.json").read_text())
    kpi2 = json.loads((d2 / "consultant_packet_base" / "kpi_summary.json").read_text())
    assert kpi1 == kpi2


def test_generate_case_studies_cli_creates_packets(tmp_path):
    ret = main([
        "generate-case-studies",
        "--scenario", "it-support-triage",
        "--output-dir", str(tmp_path),
        "--profiles", "base",
    ])
    assert ret == 0
    assert (tmp_path / "it-support-triage" / "consultant_packet_base").is_dir()


# ---------------------------------------------------------------------------
# Scenario matrix profile validation
# ---------------------------------------------------------------------------


def test_build_scenario_matrix_invalid_profile_raises():
    with pytest.raises(ValueError, match="Invalid profile name 'bad'"):
        build_scenario_matrix(profile_name="bad")


def test_build_scenario_matrix_empty_string_raises():
    with pytest.raises(ValueError, match="Invalid profile name"):
        build_scenario_matrix(profile_name="")


def test_build_scenario_matrix_case_sensitive():
    with pytest.raises(ValueError, match="Invalid profile name 'Base'"):
        build_scenario_matrix(profile_name="Base")


def test_build_scenario_matrix_valid_base_works():
    rows = build_scenario_matrix(
        profile_name="base",
        scenario_slugs=["it-support-triage"],
    )
    assert len(rows) == 1
    assert rows[0]["profile"] == "base"


def test_build_scenario_matrix_valid_conservative_works():
    rows = build_scenario_matrix(
        profile_name="conservative",
        scenario_slugs=["it-support-triage"],
    )
    assert rows[0]["profile"] == "conservative"


def test_build_scenario_matrix_valid_aggressive_works():
    rows = build_scenario_matrix(
        profile_name="aggressive",
        scenario_slugs=["it-support-triage"],
    )
    assert rows[0]["profile"] == "aggressive"


def test_cli_scenario_matrix_invalid_profile_exits_nonzero():
    """argparse rejects invalid choices before our code runs; exit code is non-zero."""
    with pytest.raises(SystemExit) as exc_info:
        main(["scenario-matrix", "--profile", "bad"])
    assert exc_info.value.code != 0


def test_cli_scenario_matrix_invalid_profile_prints_error(capsys):
    try:
        main(["scenario-matrix", "--profile", "bad"])
    except SystemExit:
        pass
    err = capsys.readouterr().err
    assert "bad" in err or "invalid choice" in err.lower()


def test_cli_scenario_matrix_valid_profiles_still_work():
    for profile in ("base", "conservative", "aggressive"):
        ret = main(["scenario-matrix", "--profile", profile])
        assert ret == 0, f"Expected 0 for --profile {profile!r}"
