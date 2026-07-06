"""Tests for Phase 9 CLI commands."""

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
# list-configs
# ---------------------------------------------------------------------------


def test_list_configs_exits_zero():
    assert main(["list-configs"]) == 0


def test_list_configs_json_exits_zero(capsys):
    assert main(["list-configs", "--format", "json"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 6


def test_list_configs_json_has_expected_fields(capsys):
    main(["list-configs", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    for item in data:
        assert "configured_slug" in item
        assert "base_scenario_slug" in item
        assert "client_name" in item


# ---------------------------------------------------------------------------
# validate-config
# ---------------------------------------------------------------------------


def test_validate_config_valid_exits_zero():
    assert main(["validate-config", _SAMPLE_CONFIG]) == 0


def test_validate_config_invalid_exits_one(tmp_path):
    bad_path = str(tmp_path / "bad.json")
    bad_data = {
        "base_scenario_slug": "no-such-scenario", "configured_slug": "x", "configured_name": "x"
    }
    Path(bad_path).write_text(json.dumps(bad_data))
    assert main(["validate-config", bad_path]) == 1


def test_validate_config_missing_file_exits_nonzero():
    with pytest.raises(SystemExit) as exc_info:
        main(["validate-config", "/nonexistent/config.json"])
    assert exc_info.value.code != 0


def test_validate_config_outputs_overrides(capsys):
    main(["validate-config", _SAMPLE_CONFIG])
    out = capsys.readouterr().out
    assert "Actor overrides" in out or "actor" in out.lower()


# ---------------------------------------------------------------------------
# run-config
# ---------------------------------------------------------------------------


def test_run_config_exits_zero():
    assert main(["run-config", _SAMPLE_CONFIG]) == 0


def test_run_config_shows_kpi_table(capsys):
    main(["run-config", _SAMPLE_CONFIG])
    out = capsys.readouterr().out
    assert "Completion" in out or "completion" in out.lower()


def test_run_config_all_sample_configs():
    for path in sorted(_CONFIGS_DIR.glob("*.json")):
        ret = main(["run-config", str(path)])
        assert ret == 0, f"run-config failed for {path.name}"


# ---------------------------------------------------------------------------
# compare-config
# ---------------------------------------------------------------------------


def test_compare_config_exits_zero():
    assert main(["compare-config", _SAMPLE_CONFIG]) == 0


def test_compare_config_shows_roi(capsys):
    main(["compare-config", _SAMPLE_CONFIG])
    out = capsys.readouterr().out
    assert "ROI" in out or "savings" in out.lower() or "cost" in out.lower()


# ---------------------------------------------------------------------------
# config-snapshot
# ---------------------------------------------------------------------------


def test_config_snapshot_exits_zero():
    assert main(["config-snapshot", _SAMPLE_CONFIG]) == 0


def test_config_snapshot_html_output(tmp_path):
    out_file = str(tmp_path / "snap.html")
    ret = main(["config-snapshot", _SAMPLE_CONFIG, "--html-output", out_file])
    assert ret == 0
    assert "<!DOCTYPE html>" in Path(out_file).read_text()


# ---------------------------------------------------------------------------
# config-packet
# ---------------------------------------------------------------------------


def test_config_packet_exits_zero(tmp_path):
    ret = main(["config-packet", _SAMPLE_CONFIG, "--output-dir", str(tmp_path)])
    assert ret == 0


def test_config_packet_creates_files(tmp_path):
    main(["config-packet", _SAMPLE_CONFIG, "--output-dir", str(tmp_path)])
    files = {f.name for f in tmp_path.iterdir()}
    assert "README.md" in files
    assert "executive_snapshot.txt" in files


# ---------------------------------------------------------------------------
# config-case-study
# ---------------------------------------------------------------------------


def test_config_case_study_exits_zero(tmp_path):
    ret = main(["config-case-study", _SAMPLE_CONFIG, "--output-dir", str(tmp_path)])
    assert ret == 0


def test_config_case_study_creates_expected_files(tmp_path):
    main(["config-case-study", _SAMPLE_CONFIG, "--output-dir", str(tmp_path)])
    files = {f.name for f in tmp_path.iterdir() if f.is_file()}
    assert "config.json" in files
    assert "config_diff.txt" in files
    assert "kpi_summary.json" in files
    assert "README.md" in files


def test_config_case_study_deterministic(tmp_path):
    d1 = tmp_path / "r1"
    d2 = tmp_path / "r2"
    main(["config-case-study", _SAMPLE_CONFIG, "--output-dir", str(d1)])
    main(["config-case-study", _SAMPLE_CONFIG, "--output-dir", str(d2)])
    kpi1 = json.loads((d1 / "kpi_summary.json").read_text())
    kpi2 = json.loads((d2 / "kpi_summary.json").read_text())
    assert kpi1 == kpi2


# ---------------------------------------------------------------------------
# config-diff
# ---------------------------------------------------------------------------


def test_config_diff_exits_zero():
    assert main(["config-diff", _SAMPLE_CONFIG]) == 0


def test_config_diff_json_output(capsys, tmp_path):
    out_file = str(tmp_path / "diff.json")
    ret = main(["config-diff", _SAMPLE_CONFIG, "--format", "json", "--output", out_file])
    assert ret == 0
    data = json.loads(Path(out_file).read_text())
    assert "base_scenario_slug" in data


# ---------------------------------------------------------------------------
# calibration-template
# ---------------------------------------------------------------------------


def test_calibration_template_exits_zero():
    assert main(["calibration-template", "it-support-triage"]) == 0


def test_calibration_template_json_format(capsys):
    main(["calibration-template", "it-support-triage", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["scenario_slug"] == "it-support-triage"


def test_calibration_template_output_file(tmp_path):
    out_file = str(tmp_path / "cal.md")
    ret = main(["calibration-template", "it-support-triage", "--output", out_file])
    assert ret == 0
    assert "Calibration" in Path(out_file).read_text()


# ---------------------------------------------------------------------------
# Backward compatibility: Phase 1-8 commands still work
# ---------------------------------------------------------------------------


def test_run_example_still_works():
    assert main(["run-example", "invoice-processing", "--cases", "30", "--seed", "1"]) == 0


def test_executive_snapshot_still_works():
    assert main(["executive-snapshot", "invoice-processing", "--cases", "30"]) == 0


def test_list_scenarios_still_works():
    assert main(["list-scenarios"]) == 0
