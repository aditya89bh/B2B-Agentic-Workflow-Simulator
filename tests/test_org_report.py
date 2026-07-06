"""Tests for org_report: OrgDigitalTwinReport, generate_org_digital_twin_report."""

from __future__ import annotations

from b2b_workflow_simulator.budget import OrgBudget
from b2b_workflow_simulator.examples import (
    invoice_processing,
    sales_lead_qualification,
)
from b2b_workflow_simulator.growth import GrowthConfig, project_growth
from b2b_workflow_simulator.org_health import compute_org_health
from b2b_workflow_simulator.org_model import Department, Organization, Role, Team
from b2b_workflow_simulator.org_report import (
    OrgDigitalTwinReport,
    generate_org_digital_twin_report,
)
from b2b_workflow_simulator.restructuring import (
    CREATE_AI_OPS_TEAM,
    RestructuringScenario,
    evaluate_restructuring,
)
from b2b_workflow_simulator.shared_resources import (
    SharedResourcePool,
)
from b2b_workflow_simulator.simulation import SimulationRunner


def _make_org() -> Organization:
    org = Organization(org_id="co", name="Report Co")
    org.add_department(Department(dept_id="sales", name="Sales"))
    org.add_department(Department(dept_id="finance", name="Finance"))
    org.add_team(Team(team_id="t1", name="Sales Team", department_id="sales"))
    org.add_role(Role(role_id="r1", name="Rep", actor_id="a1", department_id="sales", team_id="t1"))
    org.add_workflow_id("wf-1")
    org.add_workflow_id("wf-2")
    return org


def _make_kpis() -> dict:
    runner = SimulationRunner(seed=7)
    r1 = runner.run(sales_lead_qualification.build_before_workflow(), 50)
    r2 = runner.run(invoice_processing.build_before_workflow(), 50)
    return {"wf-1": r1.kpi, "wf-2": r2.kpi}


# ---------------------------------------------------------------------------
# OrgDigitalTwinReport
# ---------------------------------------------------------------------------


def test_report_minimal_construction():
    org = _make_org()
    report = OrgDigitalTwinReport(org=org)
    assert report.org is org
    assert report.kpi_results == {}
    assert report.health_score is None
    assert report.growth_projection is None


def test_report_with_all_fields():
    org = _make_org()
    kpis = _make_kpis()
    ob = OrgBudget(org_id="co")
    pool = SharedResourcePool(org_id="co")
    hs = compute_org_health(org, ob, pool, kpis)
    cfg = GrowthConfig(base_cases_per_month=50)
    gp = project_growth(org, ob, cfg)
    scenario = RestructuringScenario(
        scenario_id="s1", scenario_type=CREATE_AI_OPS_TEAM, description="AI Ops"
    )
    impacts = [evaluate_restructuring(org, kpis, scenario)]
    report = OrgDigitalTwinReport(
        org=org, kpi_results=kpis, org_budget=ob, shared_resources=pool,
        health_score=hs, growth_projection=gp, restructuring_impacts=impacts,
    )
    assert report.org_budget is ob
    assert report.health_score is hs
    assert len(report.restructuring_impacts) == 1


# ---------------------------------------------------------------------------
# generate_org_digital_twin_report
# ---------------------------------------------------------------------------


def test_report_contains_org_name():
    org = _make_org()
    report = OrgDigitalTwinReport(org=org)
    text = generate_org_digital_twin_report(report)
    assert "Report Co" in text


def test_report_contains_structure_section():
    org = _make_org()
    report = OrgDigitalTwinReport(org=org)
    text = generate_org_digital_twin_report(report)
    assert "ORGANIZATIONAL STRUCTURE" in text


def test_report_contains_workflow_section():
    org = _make_org()
    kpis = _make_kpis()
    report = OrgDigitalTwinReport(org=org, kpi_results=kpis)
    text = generate_org_digital_twin_report(report)
    assert "WORKFLOW SIMULATION RESULTS" in text


def test_report_contains_budget_section():
    org = _make_org()
    ob = OrgBudget(org_id="co")
    report = OrgDigitalTwinReport(org=org, org_budget=ob)
    text = generate_org_digital_twin_report(report)
    assert "BUDGET ANALYSIS" in text


def test_report_contains_resource_section():
    org = _make_org()
    pool = SharedResourcePool(org_id="co")
    report = OrgDigitalTwinReport(org=org, shared_resources=pool)
    text = generate_org_digital_twin_report(report)
    assert "SHARED RESOURCE CONTENTION" in text


def test_report_contains_health_section_when_present():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    report = OrgDigitalTwinReport(org=org, kpi_results=kpis, health_score=hs)
    text = generate_org_digital_twin_report(report)
    assert "ORGANIZATIONAL HEALTH" in text


def test_report_omits_health_section_when_absent():
    org = _make_org()
    report = OrgDigitalTwinReport(org=org)
    text = generate_org_digital_twin_report(report)
    assert "ORGANIZATIONAL HEALTH" not in text


def test_report_contains_restructuring_section_when_present():
    org = _make_org()
    kpis = _make_kpis()
    scenario = RestructuringScenario(
        scenario_id="s1", scenario_type=CREATE_AI_OPS_TEAM, description="AI Ops"
    )
    impacts = [evaluate_restructuring(org, kpis, scenario)]
    report = OrgDigitalTwinReport(org=org, restructuring_impacts=impacts)
    text = generate_org_digital_twin_report(report)
    assert "RESTRUCTURING" in text


def test_report_contains_growth_section_when_present():
    org = _make_org()
    cfg = GrowthConfig(base_cases_per_month=50)
    gp = project_growth(org, None, cfg)
    report = OrgDigitalTwinReport(org=org, growth_projection=gp)
    text = generate_org_digital_twin_report(report)
    assert "GROWTH PROJECTION" in text


def test_report_contains_rollout_roadmap():
    org = _make_org()
    report = OrgDigitalTwinReport(org=org)
    text = generate_org_digital_twin_report(report)
    assert "ROLLOUT ROADMAP" in text


def test_report_department_names_appear():
    org = _make_org()
    report = OrgDigitalTwinReport(org=org)
    text = generate_org_digital_twin_report(report)
    assert "Sales" in text
    assert "Finance" in text


def test_report_no_budget_message():
    org = _make_org()
    report = OrgDigitalTwinReport(org=org)
    text = generate_org_digital_twin_report(report)
    assert "No budget data" in text


def test_report_kpi_workflow_ids_appear():
    org = _make_org()
    kpis = _make_kpis()
    report = OrgDigitalTwinReport(org=org, kpi_results=kpis)
    text = generate_org_digital_twin_report(report)
    assert "wf-1" in text
    assert "wf-2" in text
