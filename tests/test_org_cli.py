"""Tests for Phase 6 CLI commands: run-org, org-health, org-budget-analysis, etc."""

from __future__ import annotations

from pathlib import Path

import pytest

from b2b_workflow_simulator.cli import main

# ---------------------------------------------------------------------------
# run-org
# ---------------------------------------------------------------------------


def test_run_org_exits_zero():
    assert main(["run-org", "--cases", "30", "--seed", "1"]) == 0


def test_run_org_output_contains_org_name(capsys):
    main(["run-org", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "Acme B2B SaaS" in out


def test_run_org_output_contains_completion_rate(capsys):
    main(["run-org", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "%" in out


def test_run_org_output_contains_three_workflows(capsys):
    main(["run-org", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "sales-lead-qualification" in out
    assert "invoice-processing" in out
    assert "customer-support-ticket-resolution" in out


def test_run_org_with_arrival_interval(capsys):
    ret = main(["run-org", "--cases", "20", "--seed", "2", "--arrival-interval", "5"])
    assert ret == 0


# ---------------------------------------------------------------------------
# org-health
# ---------------------------------------------------------------------------


def test_org_health_exits_zero():
    assert main(["org-health", "--cases", "30", "--seed", "1"]) == 0


def test_org_health_output_contains_grade(capsys):
    main(["org-health", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "Grade:" in out


def test_org_health_output_contains_overall_score(capsys):
    main(["org-health", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "Overall score" in out


def test_org_health_html_output(tmp_path):
    out_file = str(tmp_path / "health.html")
    ret = main(["org-health", "--cases", "20", "--seed", "1", "--html-output", out_file])
    assert ret == 0
    content = Path(out_file).read_text()
    assert "<!DOCTYPE html>" in content
    assert "Acme B2B SaaS" in content


# ---------------------------------------------------------------------------
# org-budget-analysis
# ---------------------------------------------------------------------------


def test_org_budget_analysis_exits_zero():
    assert main(["org-budget-analysis"]) == 0


def test_org_budget_analysis_output_contains_total_budget(capsys):
    main(["org-budget-analysis"])
    out = capsys.readouterr().out
    assert "Total annual budget" in out


def test_org_budget_analysis_output_contains_departments(capsys):
    main(["org-budget-analysis"])
    out = capsys.readouterr().out
    assert "Sales" in out
    assert "Finance" in out


def test_org_budget_analysis_html_output(tmp_path):
    out_file = str(tmp_path / "budget.html")
    ret = main(["org-budget-analysis", "--html-output", out_file])
    assert ret == 0
    assert "<!DOCTYPE html>" in Path(out_file).read_text()


# ---------------------------------------------------------------------------
# org-resource-contention
# ---------------------------------------------------------------------------


def test_org_resource_contention_exits_zero():
    assert main(["org-resource-contention"]) == 0


def test_org_resource_contention_output_contains_resources(capsys):
    main(["org-resource-contention"])
    out = capsys.readouterr().out
    assert "Legal Counsel" in out


def test_org_resource_contention_days_option():
    ret = main(["org-resource-contention", "--days", "5"])
    assert ret == 0


def test_org_resource_contention_shows_non_zero_ratios(capsys):
    main(["org-resource-contention", "--cases", "100", "--seed", "1", "--days", "22"])
    out = capsys.readouterr().out
    ratios = [float(tok) for tok in out.split() if tok.replace(".", "", 1).isdigit()]
    assert any(r > 0.0 for r in ratios), "Expected at least one non-zero contention ratio"


def test_org_resource_contention_accepts_cases_and_seed():
    ret = main(["org-resource-contention", "--cases", "50", "--seed", "7", "--days", "1"])
    assert ret == 0


# ---------------------------------------------------------------------------
# org-growth-projection
# ---------------------------------------------------------------------------


def test_org_growth_projection_exits_zero():
    assert main(["org-growth-projection"]) == 0


def test_org_growth_projection_output_contains_months(capsys):
    main(["org-growth-projection"])
    out = capsys.readouterr().out
    assert "Month" in out


def test_org_growth_projection_custom_growth_rate(capsys):
    main(["org-growth-projection", "--monthly-growth-rate", "0.10"])
    out = capsys.readouterr().out
    assert "10.0%" in out


def test_org_growth_projection_html_output(tmp_path):
    out_file = str(tmp_path / "growth.html")
    ret = main(["org-growth-projection", "--html-output", out_file])
    assert ret == 0
    assert "<!DOCTYPE html>" in Path(out_file).read_text()


# ---------------------------------------------------------------------------
# org-restructure-scenario
# ---------------------------------------------------------------------------


def test_org_restructure_scenario_create_ai_ops_exits_zero():
    assert main(["org-restructure-scenario", "create_ai_ops_team", "--cases", "30"]) == 0


def test_org_restructure_scenario_hire_staff_exits_zero():
    assert main(["org-restructure-scenario", "hire_additional_staff", "--cases", "30"]) == 0


def test_org_restructure_scenario_reduce_approval_exits_zero():
    assert main(["org-restructure-scenario", "reduce_approval_layers", "--cases", "30"]) == 0


def test_org_restructure_scenario_unknown_type_exits_nonzero():
    with pytest.raises(SystemExit) as exc_info:
        main(["org-restructure-scenario", "no-such-type", "--cases", "30"])
    assert exc_info.value.code != 0


def test_org_restructure_scenario_output_contains_cost_impact(capsys):
    main(["org-restructure-scenario", "centralize_team", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "Cost impact" in out


def test_org_restructure_all_scenario_types():
    from b2b_workflow_simulator.restructuring import SCENARIO_TYPES
    for stype in SCENARIO_TYPES:
        ret = main(["org-restructure-scenario", stype, "--cases", "20", "--seed", "1"])
        assert ret == 0, f"Expected exit 0 for scenario type '{stype}'"


# ---------------------------------------------------------------------------
# org-executive-report
# ---------------------------------------------------------------------------


def test_org_executive_report_exits_zero():
    assert main(["org-executive-report", "--cases", "30", "--seed", "1"]) == 0


def test_org_executive_report_output_contains_org_name(capsys):
    main(["org-executive-report", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "Acme B2B SaaS" in out


def test_org_executive_report_output_contains_budget_section(capsys):
    main(["org-executive-report", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "BUDGET" in out


def test_org_executive_report_output_contains_health_section(capsys):
    main(["org-executive-report", "--cases", "30", "--seed", "1"])
    out = capsys.readouterr().out
    assert "ORGANIZATIONAL HEALTH" in out


def test_org_executive_report_html_output(tmp_path):
    out_file = str(tmp_path / "org_exec.html")
    ret = main(["org-executive-report", "--cases", "20", "--seed", "1", "--html-output", out_file])
    assert ret == 0
    content = Path(out_file).read_text()
    assert "<!DOCTYPE html>" in content
    assert "Acme B2B SaaS" in content


def test_org_executive_report_html_no_xss(tmp_path):
    out_file = str(tmp_path / "org_exec_xss.html")
    main(["org-executive-report", "--cases", "20", "--seed", "1", "--html-output", out_file])
    content = Path(out_file).read_text()
    assert "<script>" not in content
