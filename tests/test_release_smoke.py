"""Release smoke tests: external user experience from install through all major commands.

These tests simulate what a new user or CI system would exercise on a
fresh install.  They are intentionally lightweight and fast.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from b2b_workflow_simulator.cli import main

_CONFIGS_DIR = (
    Path(__file__).parent.parent
    / "src/b2b_workflow_simulator/examples/data/configs"
)
_SAMPLE_CONFIG = str(_CONFIGS_DIR / "it-support-triage-managed-service.json")


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


def test_version_flag():
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Scenario exploration
# ---------------------------------------------------------------------------


def test_list_scenarios_exits_zero():
    assert main(["list-scenarios"]) == 0


def test_list_scenarios_json_has_11_entries(capsys):
    main(["list-scenarios", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 11


def test_scenario_matrix_exits_zero():
    assert main(["scenario-matrix"]) == 0


def test_scenario_matrix_json_valid(capsys):
    main(["scenario-matrix", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 11
    assert "slug" in data[0]
    assert "total_cost_savings" in data[0]


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------


def test_executive_snapshot_healthcare(capsys):
    ret = main(["executive-snapshot", "healthcare-prior-authorization", "--cases", "50"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "EXECUTIVE SNAPSHOT" in out


def test_run_example_invoice_processing():
    assert main(["run-example", "invoice-processing", "--cases", "50", "--seed", "1"]) == 0


def test_compare_example_it_support():
    assert main(["compare-example", "it-support-triage", "--cases", "50"]) == 0


# ---------------------------------------------------------------------------
# Consultant packet
# ---------------------------------------------------------------------------


def test_consultant_packet_invoice_processing(tmp_path):
    ret = main([
        "consultant-packet", "invoice-processing",
        "--cases", "50", "--output-dir", str(tmp_path),
    ])
    assert ret == 0
    assert (tmp_path / "executive_snapshot.txt").exists()
    assert (tmp_path / "roi_waterfall.svg").exists()
    assert (tmp_path / "kpi_summary.json").exists()


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def test_calibration_template_legal():
    assert main(["calibration-template", "legal-contract-review"]) == 0


def test_calibration_template_json_format(capsys):
    main(["calibration-template", "legal-contract-review", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "scenario_slug" in data
    assert len(data["sections"]) == 8


# ---------------------------------------------------------------------------
# Config commands
# ---------------------------------------------------------------------------


def test_validate_config_sample():
    assert main(["validate-config", _SAMPLE_CONFIG]) == 0


def test_run_config_sample():
    assert main(["run-config", _SAMPLE_CONFIG]) == 0


def test_config_diff_sample():
    assert main(["config-diff", _SAMPLE_CONFIG]) == 0


def test_config_case_study_sample(tmp_path):
    ret = main(["config-case-study", _SAMPLE_CONFIG, "--output-dir", str(tmp_path)])
    assert ret == 0
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "config_diff.txt").exists()
    assert (tmp_path / "kpi_summary.json").exists()


# ---------------------------------------------------------------------------
# Generate release examples
# ---------------------------------------------------------------------------


def test_generate_release_examples(tmp_path):
    ret = main(["generate-release-examples", "--output-dir", str(tmp_path)])
    assert ret == 0
    expected = [
        "healthcare_executive_snapshot.txt",
        "healthcare_workflow_before.mmd",
        "healthcare_workflow_after.mmd",
        "healthcare_roi_waterfall.svg",
        "healthcare_bottleneck_heatmap.svg",
        "scenario_matrix_base.json",
        "scenario_matrix_conservative.json",
        "calibration_healthcare.md",
        "config_diff_healthcare_small_plan.txt",
        "configured_case_study_readme_sample.md",
    ]
    for filename in expected:
        assert (tmp_path / filename).exists(), f"Missing: {filename}"


def test_generate_release_examples_deterministic(tmp_path):
    d1 = tmp_path / "r1"
    d2 = tmp_path / "r2"
    main(["generate-release-examples", "--output-dir", str(d1)])
    main(["generate-release-examples", "--output-dir", str(d2)])
    snap1 = (d1 / "healthcare_executive_snapshot.txt").read_text()
    snap2 = (d2 / "healthcare_executive_snapshot.txt").read_text()
    assert snap1 == snap2


def test_release_output_json_valid(tmp_path):
    main(["generate-release-examples", "--output-dir", str(tmp_path)])
    data = json.loads((tmp_path / "scenario_matrix_base.json").read_text())
    assert isinstance(data, list) and len(data) == 11


def test_release_output_mermaid_valid(tmp_path):
    main(["generate-release-examples", "--output-dir", str(tmp_path)])
    assert (tmp_path / "healthcare_workflow_before.mmd").read_text().startswith("flowchart LR")


def test_release_output_svg_valid(tmp_path):
    main(["generate-release-examples", "--output-dir", str(tmp_path)])
    svg = (tmp_path / "healthcare_roi_waterfall.svg").read_text()
    assert "<svg" in svg and "</svg>" in svg
