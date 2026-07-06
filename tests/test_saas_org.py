"""Tests for the bundled B2B SaaS example organization."""

from __future__ import annotations

from b2b_workflow_simulator.budget import AI_TOOLING, OPERATING
from b2b_workflow_simulator.examples.saas_org import (
    build_saas_org,
    build_saas_org_budget,
    build_saas_shared_resources,
)

# ---------------------------------------------------------------------------
# build_saas_org
# ---------------------------------------------------------------------------


def test_saas_org_id_and_name():
    org = build_saas_org()
    assert org.org_id == "acme-saas"
    assert "Acme" in org.name


def test_saas_org_has_six_departments():
    org = build_saas_org()
    assert len(org.departments) == 6


def test_saas_org_expected_departments():
    org = build_saas_org()
    dept_names = {d.name for d in org.departments.values()}
    expected_depts = (
        "Sales", "Customer Success", "Finance",
        "Legal", "Operations", "AI Transformation Office",
    )
    for expected in expected_depts:
        assert expected in dept_names


def test_saas_org_has_six_teams():
    org = build_saas_org()
    assert len(org.teams) == 6


def test_saas_org_has_18_roles():
    org = build_saas_org()
    assert org.total_headcount() == 18


def test_saas_org_has_three_ai_agent_roles():
    org = build_saas_org()
    assert org.ai_agent_count() == 3


def test_saas_org_has_managers():
    org = build_saas_org()
    assert org.manager_count() > 0


def test_saas_org_has_three_workflows():
    org = build_saas_org()
    assert len(org.workflow_ids) == 3


def test_saas_org_workflow_ids_include_all_examples():
    org = build_saas_org()
    wf_ids = org.workflow_ids
    assert "sales-lead-qualification" in wf_ids
    assert "invoice-processing" in wf_ids
    assert "customer-support-ticket-resolution" in wf_ids


def test_saas_org_all_teams_belong_to_known_depts():
    org = build_saas_org()
    for team in org.teams.values():
        assert team.department_id in org.departments


def test_saas_org_all_roles_belong_to_known_depts():
    org = build_saas_org()
    for role in org.roles.values():
        assert role.department_id in org.departments


def test_saas_org_all_roles_team_ids_valid():
    org = build_saas_org()
    for role in org.roles.values():
        if role.team_id is not None:
            assert role.team_id in org.teams


def test_saas_org_has_reporting_lines():
    org = build_saas_org()
    assert len(org.reporting_lines) > 0


def test_saas_org_validates_without_error():
    org = build_saas_org()
    org.validate()


def test_saas_org_has_org_units():
    org = build_saas_org()
    units = org.org_units()
    types = {u.unit_type for u in units}
    assert "organization" in types
    assert "department" in types
    assert "team" in types


def test_saas_org_sales_team_has_sales_workflow():
    org = build_saas_org()
    sales_team = org.get_team("sales-dev")
    assert "sales-lead-qualification" in sales_team.workflow_ids


def test_saas_org_finance_team_has_invoice_workflow():
    org = build_saas_org()
    finance_team = org.get_team("finance-ops")
    assert "invoice-processing" in finance_team.workflow_ids


def test_saas_org_cs_team_has_support_workflow():
    org = build_saas_org()
    cs_team = org.get_team("cs-ops")
    assert "customer-support-ticket-resolution" in cs_team.workflow_ids


# ---------------------------------------------------------------------------
# build_saas_org_budget
# ---------------------------------------------------------------------------


def test_saas_budget_has_six_departments():
    ob = build_saas_org_budget()
    assert len(ob.dept_budgets) == 6


def test_saas_budget_total_is_positive():
    ob = build_saas_org_budget()
    assert ob.total_budget > 0


def test_saas_budget_all_depts_have_operating_allocation():
    ob = build_saas_org_budget()
    for dept_id, budget in ob.dept_budgets.items():
        if dept_id != "ai-transformation":
            assert budget.allocation(OPERATING) is not None


def test_saas_budget_ai_dept_has_ai_tooling():
    ob = build_saas_org_budget()
    ai_budget = ob.dept_budget("ai-transformation")
    assert ai_budget is not None
    assert ai_budget.allocation(AI_TOOLING) is not None


def test_saas_budget_no_overruns_initially():
    ob = build_saas_org_budget()
    assert ob.overrun_departments() == []


def test_saas_budget_utilization_zero_initially():
    ob = build_saas_org_budget()
    assert ob.overall_utilization == 0.0


# ---------------------------------------------------------------------------
# build_saas_shared_resources
# ---------------------------------------------------------------------------


def test_saas_shared_resources_has_resources():
    pool = build_saas_shared_resources()
    assert len(pool.resources) > 0


def test_saas_shared_resources_has_legal_reviewer():
    pool = build_saas_shared_resources()
    from b2b_workflow_simulator.shared_resources import LEGAL_REVIEWER
    assert any(r.resource_type == LEGAL_REVIEWER for r in pool.resources.values())


def test_saas_shared_resources_has_ai_agent():
    pool = build_saas_shared_resources()
    from b2b_workflow_simulator.shared_resources import AI_AGENT
    assert any(r.resource_type == AI_AGENT for r in pool.resources.values())


def test_saas_shared_resources_no_contention_with_no_usage():
    pool = build_saas_shared_resources()
    for c in pool.all_contentions():
        assert c.contention_ratio == 0.0


def test_saas_shared_resources_contention_after_usage():
    pool = build_saas_shared_resources()
    pool.record_usage("legal-counsel", "invoice-processing", "finance", 300.0)
    c = pool.compute_contention("legal-counsel")
    assert c.total_demand_minutes == 300.0
    assert c.contention_ratio > 0.0
