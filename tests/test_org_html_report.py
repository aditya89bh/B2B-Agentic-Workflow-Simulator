"""Tests for Phase 6 HTML report renderers."""

from __future__ import annotations

from b2b_workflow_simulator.budget import DepartmentBudget, OrgBudget
from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.examples.saas_org import (
    build_saas_org,
    build_saas_org_budget,
    build_saas_shared_resources,
)
from b2b_workflow_simulator.growth import GrowthConfig, project_growth
from b2b_workflow_simulator.html_report import (
    render_org_budget_html,
    render_org_executive_html,
    render_org_growth_html,
    render_org_health_html,
)
from b2b_workflow_simulator.org_health import compute_org_health
from b2b_workflow_simulator.org_model import Department, Organization
from b2b_workflow_simulator.org_report import OrgDigitalTwinReport
from b2b_workflow_simulator.simulation import SimulationRunner


def _make_org():
    org = Organization(org_id="co", name="HTML Test Org <&>")
    org.add_department(Department(dept_id="d1", name="Sales <&>"))
    return org


def _make_kpis():
    runner = SimulationRunner(seed=3)
    r1 = runner.run(sales_lead_qualification.build_before_workflow(), 50)
    r2 = runner.run(invoice_processing.build_before_workflow(), 50)
    return {"wf-1": r1.kpi, "wf-2": r2.kpi}


# ---------------------------------------------------------------------------
# render_org_health_html
# ---------------------------------------------------------------------------


def test_org_health_html_is_valid_html():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    output = render_org_health_html(hs)
    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_org_health_html_contains_org_name():
    org = build_saas_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    output = render_org_health_html(hs)
    assert "Acme B2B SaaS" in output


def test_org_health_html_contains_overall_score():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    output = render_org_health_html(hs)
    assert "Overall score" in output


def test_org_health_html_escapes_special_chars():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    output = render_org_health_html(hs)
    assert "<&>" not in output
    assert "&lt;&amp;&gt;" in output


def test_org_health_html_contains_top_risks_section():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    output = render_org_health_html(hs)
    assert "Top Risks" in output


def test_org_health_html_contains_dimension_scores_table():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    output = render_org_health_html(hs)
    assert "<table>" in output


# ---------------------------------------------------------------------------
# render_org_budget_html
# ---------------------------------------------------------------------------


def test_org_budget_html_is_valid_html():
    org = build_saas_org()
    ob = build_saas_org_budget()
    output = render_org_budget_html(org, ob)
    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_org_budget_html_contains_org_name():
    org = build_saas_org()
    ob = build_saas_org_budget()
    output = render_org_budget_html(org, ob)
    assert "Acme B2B SaaS" in output


def test_org_budget_html_contains_total_budget():
    org = build_saas_org()
    ob = build_saas_org_budget()
    output = render_org_budget_html(org, ob)
    assert "2,950,000" in output


def test_org_budget_html_contains_department_rows():
    org = build_saas_org()
    ob = build_saas_org_budget()
    output = render_org_budget_html(org, ob)
    assert "Sales" in output
    assert "Finance" in output


def test_org_budget_html_escapes_dept_names():
    org = Organization(org_id="co", name="Co")
    org.add_department(Department(dept_id="d1", name="Dept <&>"))
    ob = OrgBudget(org_id="co")
    ob.add_dept_budget(DepartmentBudget(dept_id="d1", annual_budget=1000.0))
    output = render_org_budget_html(org, ob)
    assert "<&>" not in output


# ---------------------------------------------------------------------------
# render_org_growth_html
# ---------------------------------------------------------------------------


def test_org_growth_html_is_valid_html():
    org = build_saas_org()
    cfg = GrowthConfig(base_cases_per_month=100)
    projection = project_growth(org, None, cfg)
    output = render_org_growth_html(projection)
    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_org_growth_html_contains_org_name():
    org = build_saas_org()
    cfg = GrowthConfig(base_cases_per_month=100)
    projection = project_growth(org, None, cfg)
    output = render_org_growth_html(projection)
    assert "Acme B2B SaaS" in output


def test_org_growth_html_contains_12_rows():
    org = build_saas_org()
    cfg = GrowthConfig(base_cases_per_month=100)
    projection = project_growth(org, None, cfg)
    output = render_org_growth_html(projection)
    assert output.count("<tr>") >= 12


def test_org_growth_html_no_breaking_point_message():
    org = build_saas_org()
    cfg = GrowthConfig(monthly_growth_rate=0.01, base_cases_per_month=10, base_headcount=100)
    projection = project_growth(org, None, cfg)
    output = render_org_growth_html(projection)
    assert "No breaking points" in output


def test_org_growth_html_breaking_point_callout():
    org = build_saas_org()
    cfg = GrowthConfig(
        monthly_growth_rate=0.50,
        base_cases_per_month=500,
        base_headcount=2,
        actor_capacity_per_head=10.0,
    )
    projection = project_growth(org, None, cfg)
    if projection.breaking_points():
        output = render_org_growth_html(projection)
        assert "Breaking point" in output


# ---------------------------------------------------------------------------
# render_org_executive_html
# ---------------------------------------------------------------------------


def test_org_executive_html_is_valid_html():
    org = build_saas_org()
    report = OrgDigitalTwinReport(org=org)
    output = render_org_executive_html(report)
    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_org_executive_html_contains_org_name():
    org = build_saas_org()
    report = OrgDigitalTwinReport(org=org)
    output = render_org_executive_html(report)
    assert "Acme B2B SaaS" in output


def test_org_executive_html_contains_structure_section():
    org = build_saas_org()
    report = OrgDigitalTwinReport(org=org)
    output = render_org_executive_html(report)
    assert "Structure" in output


def test_org_executive_html_contains_workflow_section():
    org = build_saas_org()
    kpis = _make_kpis()
    report = OrgDigitalTwinReport(org=org, kpi_results=kpis)
    output = render_org_executive_html(report)
    assert "Workflow Results" in output


def test_org_executive_html_contains_health_section_when_present():
    org = build_saas_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    report = OrgDigitalTwinReport(org=org, kpi_results=kpis, health_score=hs)
    output = render_org_executive_html(report)
    assert "Organizational Health" in output


def test_org_executive_html_contains_budget_section_when_present():
    org = build_saas_org()
    ob = build_saas_org_budget()
    report = OrgDigitalTwinReport(org=org, org_budget=ob)
    output = render_org_executive_html(report)
    assert "Budget Summary" in output


def test_org_executive_html_contains_resource_section_when_present():
    org = build_saas_org()
    pool = build_saas_shared_resources()
    report = OrgDigitalTwinReport(org=org, shared_resources=pool)
    output = render_org_executive_html(report)
    assert "Shared Resource Contention" in output


def test_org_executive_html_escapes_special_chars():
    org = Organization(org_id="co", name="Org <script>alert(1)</script>")
    org.add_department(Department(dept_id="d1", name="D1"))
    report = OrgDigitalTwinReport(org=org)
    output = render_org_executive_html(report)
    assert "<script>" not in output
