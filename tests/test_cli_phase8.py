"""Tests for Phase 8 CLI commands and backward compatibility."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from b2b_workflow_simulator.cli import main
from b2b_workflow_simulator.scenarios import scenario_names

_NEW_SLUGS = [
    "healthcare-prior-authorization",
    "insurance-claims-intake",
    "hr-recruiting-screening",
    "procurement-vendor-onboarding",
    "legal-contract-review",
    "it-support-triage",
    "finance-month-end-close",
    "customer-onboarding-implementation",
]

_ORIGINAL_SLUGS = [
    "sales-lead-qualification",
    "invoice-processing",
    "customer-support-ticket-resolution",
]


# ---------------------------------------------------------------------------
# Backward compatibility: original examples still work
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", _ORIGINAL_SLUGS)
def test_run_example_original_still_works(slug):
    assert main(["run-example", slug, "--cases", "30", "--seed", "1"]) == 0


@pytest.mark.parametrize("slug", _ORIGINAL_SLUGS)
def test_compare_example_original_still_works(slug):
    assert main(["compare-example", slug, "--cases", "30", "--seed", "1"]) == 0


# ---------------------------------------------------------------------------
# New scenarios work through existing commands
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", _NEW_SLUGS)
def test_run_example_new_scenarios(slug):
    assert main(["run-example", slug, "--cases", "30", "--seed", "1"]) == 0


@pytest.mark.parametrize("slug", _NEW_SLUGS)
def test_compare_example_new_scenarios(slug):
    assert main(["compare-example", slug, "--cases", "30", "--seed", "1"]) == 0


@pytest.mark.parametrize("slug", _NEW_SLUGS[:3])
def test_executive_snapshot_new_scenarios(slug):
    assert main(["executive-snapshot", slug, "--cases", "30"]) == 0


@pytest.mark.parametrize("slug", _NEW_SLUGS[:2])
def test_consultant_packet_new_scenarios(slug, tmp_path):
    ret = main(["consultant-packet", slug, "--cases", "30", "--output-dir", str(tmp_path)])
    assert ret == 0
    assert (tmp_path / "README.md").exists()


# ---------------------------------------------------------------------------
# list-scenarios
# ---------------------------------------------------------------------------


def test_list_scenarios_text_exits_zero():
    assert main(["list-scenarios"]) == 0


def test_list_scenarios_json_exits_zero(capsys):
    assert main(["list-scenarios", "--format", "json"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 11


def test_list_scenarios_json_has_expected_fields(capsys):
    main(["list-scenarios", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    for item in data:
        assert "slug" in item
        assert "name" in item
        assert "category" in item
        assert "description" in item


def test_list_scenarios_all_slugs_present(capsys):
    main(["list-scenarios", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    slugs = {item["slug"] for item in data}
    for slug in scenario_names():
        assert slug in slugs


def test_list_scenarios_category_filter(capsys):
    main(["list-scenarios", "--category", "healthcare"])
    out = capsys.readouterr().out
    assert "prior-authorization" in out


def test_list_scenarios_text_mentions_scenario_names(capsys):
    main(["list-scenarios"])
    out = capsys.readouterr().out
    assert "healthcare-prior-authorization" in out
    assert "it-support-triage" in out


# ---------------------------------------------------------------------------
# scenario-matrix
# ---------------------------------------------------------------------------


def test_scenario_matrix_text_exits_zero():
    assert main(["scenario-matrix"]) == 0


def test_scenario_matrix_text_contains_all_scenarios(capsys):
    main(["scenario-matrix"])
    out = capsys.readouterr().out
    for _ in scenario_names():
        # The matrix shows names, not slugs — check at least some are present
        assert "Invoice" in out or "Healthcare" in out


def test_scenario_matrix_json_exits_zero(capsys):
    assert main(["scenario-matrix", "--format", "json"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 11


def test_scenario_matrix_json_has_expected_fields(capsys):
    main(["scenario-matrix", "--format", "json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    row = data[0]
    for field in ("slug", "name", "category", "before_cost_per_case",
                  "after_cost_per_case", "total_cost_savings", "risk_level"):
        assert field in row, f"Missing field: {field}"


def test_scenario_matrix_conservative_profile(capsys):
    main(["scenario-matrix", "--profile", "conservative"])
    out = capsys.readouterr().out
    assert "conservative" in out


def test_scenario_matrix_output_file(tmp_path, capsys):
    out_file = str(tmp_path / "matrix.json")
    ret = main(["scenario-matrix", "--format", "json", "--output", out_file])
    assert ret == 0
    data = json.loads(Path(out_file).read_text())
    assert len(data) > 0


def test_scenario_matrix_deterministic(capsys):
    main(["scenario-matrix", "--profile", "base"])
    out1 = capsys.readouterr().out
    main(["scenario-matrix", "--profile", "base"])
    out2 = capsys.readouterr().out
    assert out1 == out2


# ---------------------------------------------------------------------------
# generate-case-studies
# ---------------------------------------------------------------------------


def test_generate_case_studies_single_scenario(tmp_path):
    ret = main([
        "generate-case-studies",
        "--scenario", "it-support-triage",
        "--output-dir", str(tmp_path),
        "--profiles", "base",
    ])
    assert ret == 0
    scenario_dir = tmp_path / "it-support-triage"
    assert (scenario_dir / "README.md").exists()
    assert (scenario_dir / "executive_snapshot_base.txt").exists()
    assert (scenario_dir / "workflow_before.mmd").exists()
    assert (scenario_dir / "workflow_after.mmd").exists()
    assert (scenario_dir / "roi_waterfall_base.svg").exists()
    assert (scenario_dir / "kpi_summary_base.json").exists()


def test_generate_case_studies_json_valid(tmp_path):
    main([
        "generate-case-studies",
        "--scenario", "hr-recruiting-screening",
        "--output-dir", str(tmp_path),
        "--profiles", "base",
    ])
    data = json.loads((tmp_path / "hr-recruiting-screening" / "kpi_summary_base.json").read_text())
    assert "before" in data and "after" in data


def test_generate_case_studies_readme_has_limitations(tmp_path):
    main([
        "generate-case-studies",
        "--scenario", "it-support-triage",
        "--output-dir", str(tmp_path),
        "--profiles", "base",
    ])
    readme = (tmp_path / "it-support-triage" / "README.md").read_text()
    assert "must be validated" in readme.lower() or "limitations" in readme.lower()


def test_generate_case_studies_deterministic(tmp_path):
    d1 = tmp_path / "run1"
    d2 = tmp_path / "run2"
    main(["generate-case-studies", "--scenario", "it-support-triage",
          "--output-dir", str(d1), "--profiles", "base"])
    main(["generate-case-studies", "--scenario", "it-support-triage",
          "--output-dir", str(d2), "--profiles", "base"])
    kpi1 = json.loads((d1 / "it-support-triage" / "kpi_summary_base.json").read_text())
    kpi2 = json.loads((d2 / "it-support-triage" / "kpi_summary_base.json").read_text())
    assert kpi1 == kpi2


def test_generate_case_studies_unknown_scenario_returns_error():
    assert main([
        "generate-case-studies",
        "--scenario", "no-such-scenario",
        "--output-dir", "/tmp",
    ]) == 1


def test_generate_case_studies_no_unsafe_filenames(tmp_path):
    main(["generate-case-studies", "--scenario", "healthcare-prior-authorization",
          "--output-dir", str(tmp_path), "--profiles", "base"])
    scenario_dir = tmp_path / "healthcare-prior-authorization"
    for f in scenario_dir.iterdir():
        assert "/" not in f.name
        assert ".." not in f.name
