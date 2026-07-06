"""Tests proving org structure influences restructuring scenario evaluation."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.org_model import Department, Organization, Role, Team
from b2b_workflow_simulator.restructuring import (
    ADD_SHARED_SERVICES,
    CENTRALIZE_TEAM,
    CREATE_AI_OPS_TEAM,
    DECENTRALIZE_TEAM,
    HIRE_ADDITIONAL_STAFF,
    OUTSOURCE_STAGE,
    REDUCE_APPROVAL_LAYERS,
    RestructuringScenario,
    evaluate_restructuring,
)
from b2b_workflow_simulator.simulation import SimulationRunner


def _make_kpis():
    runner = SimulationRunner(seed=42)
    r1 = runner.run(sales_lead_qualification.build_before_workflow(), 100)
    r2 = runner.run(invoice_processing.build_before_workflow(), 100)
    return {"slq": r1.kpi, "inv": r2.kpi}


def _small_org() -> Organization:
    """A compact 1-dept, 1-team, 3-role org."""
    org = Organization(org_id="small", name="Small Co")
    org.add_department(Department(dept_id="d1", name="D1"))
    org.add_team(Team(team_id="t1", name="T1", department_id="d1"))
    for i in range(3):
        org.add_role(Role(role_id=f"r{i}", name=f"R{i}", actor_id=f"a{i}", department_id="d1"))
    return org


def _large_org() -> Organization:
    """A larger 5-dept, 8-team, 25-role org."""
    org = Organization(org_id="large", name="Large Co")
    for i in range(5):
        org.add_department(Department(dept_id=f"d{i}", name=f"Dept {i}"))
    for d in range(5):
        for t in range(2 if d < 3 else 1):
            tid = f"t{d}{t}"
            org.add_team(Team(team_id=tid, name=f"Team {d}{t}", department_id=f"d{d}"))
            for r in range(3 if d < 2 else 2):
                rid = f"r{d}{t}{r}"
                org.add_role(Role(
                    role_id=rid, name=rid, actor_id=rid, department_id=f"d{d}",
                    team_id=tid,
                ))
    return org


def _ai_heavy_org() -> Organization:
    """An org where 80% of roles are AI agents."""
    org = Organization(org_id="ai-co", name="AI-Heavy Co")
    org.add_department(Department(dept_id="d1", name="D1"))
    for i in range(8):
        org.add_role(Role(
            role_id=f"ai{i}", name=f"AI {i}", actor_id=f"a{i}",
            department_id="d1", is_ai_agent=True,
        ))
    for i in range(2):
        org.add_role(Role(
            role_id=f"h{i}", name=f"Human {i}", actor_id=f"h{i}", department_id="d1",
        ))
    return org


def _manager_heavy_org() -> Organization:
    """An org where 50% of roles are managers."""
    org = Organization(org_id="mgr-co", name="Manager-Heavy Co")
    org.add_department(Department(dept_id="d1", name="D1"))
    for i in range(5):
        org.add_role(Role(
            role_id=f"m{i}", name=f"Mgr {i}", actor_id=f"m{i}",
            department_id="d1", is_manager=True,
        ))
    for i in range(5):
        org.add_role(Role(
            role_id=f"e{i}", name=f"Employee {i}", actor_id=f"e{i}", department_id="d1",
        ))
    return org


# ---------------------------------------------------------------------------
# CENTRALIZE_TEAM: larger org benefits more
# ---------------------------------------------------------------------------


def test_centralize_team_larger_org_greater_savings():
    kpis = _make_kpis()
    s = RestructuringScenario("s", CENTRALIZE_TEAM, "Centralize")
    impact_small = evaluate_restructuring(_small_org(), kpis, s)
    impact_large = evaluate_restructuring(_large_org(), kpis, s)
    # Large org has more duplication to eliminate → more cost savings
    assert impact_large.cost_impact < impact_small.cost_impact, (
        f"Large org savings ({impact_large.cost_impact:.0f}) should be greater than "
        f"small org ({impact_small.cost_impact:.0f})"
    )


def test_centralize_team_summary_mentions_dept_and_team_count():
    kpis = _make_kpis()
    s = RestructuringScenario("s", CENTRALIZE_TEAM, "Centralize")
    impact = evaluate_restructuring(_large_org(), kpis, s)
    assert "team" in impact.summary.lower()
    assert "department" in impact.summary.lower()


# ---------------------------------------------------------------------------
# ADD_SHARED_SERVICES: more departments → higher cost fraction
# ---------------------------------------------------------------------------


def test_shared_services_more_depts_higher_savings():
    kpis = _make_kpis()
    s = RestructuringScenario("s", ADD_SHARED_SERVICES, "Shared services")
    impact_small = evaluate_restructuring(_small_org(), kpis, s)
    impact_large = evaluate_restructuring(_large_org(), kpis, s)
    assert impact_large.cost_impact <= impact_small.cost_impact, (
        "More departments should produce equal or greater shared-services savings"
    )


# ---------------------------------------------------------------------------
# CREATE_AI_OPS_TEAM: diminishing returns for AI-heavy orgs
# ---------------------------------------------------------------------------


def test_create_ai_ops_diminishing_returns_for_ai_heavy_org():
    kpis = _make_kpis()
    s = RestructuringScenario("s", CREATE_AI_OPS_TEAM, "AI Ops")
    impact_normal = evaluate_restructuring(_small_org(), kpis, s)
    impact_ai = evaluate_restructuring(_ai_heavy_org(), kpis, s)
    # AI-heavy org already has AI; creating AI ops team yields less marginal benefit
    assert impact_ai.cost_impact > impact_normal.cost_impact, (
        "AI-heavy org should see less cost savings from creating AI ops team "
        f"({impact_ai.cost_impact:.0f} vs {impact_normal.cost_impact:.0f})"
    )


def test_create_ai_ops_summary_mentions_ai_fraction():
    kpis = _make_kpis()
    s = RestructuringScenario("s", CREATE_AI_OPS_TEAM, "AI Ops")
    impact = evaluate_restructuring(_ai_heavy_org(), kpis, s)
    assert "%" in impact.summary  # AI fraction mentioned as percentage


# ---------------------------------------------------------------------------
# REDUCE_APPROVAL_LAYERS: higher manager ratio → more risk
# ---------------------------------------------------------------------------


def test_reduce_approvals_higher_risk_for_manager_heavy_org():
    kpis = _make_kpis()
    s = RestructuringScenario("s", REDUCE_APPROVAL_LAYERS, "Reduce approvals",
                              parameters={"approval_layers_removed": 1})
    impact_normal = evaluate_restructuring(_small_org(), kpis, s)
    impact_mgr = evaluate_restructuring(_manager_heavy_org(), kpis, s)
    assert impact_mgr.risk_delta >= impact_normal.risk_delta, (
        "Manager-heavy org should have equal or higher risk when removing approval layers"
    )


# ---------------------------------------------------------------------------
# HIRE_ADDITIONAL_STAFF: smaller orgs gain more proportional benefit
# ---------------------------------------------------------------------------


def test_hire_staff_risk_discount_for_large_org():
    kpis = _make_kpis()
    s = RestructuringScenario("s", HIRE_ADDITIONAL_STAFF, "Hire",
                              parameters={"headcount_delta": 1})
    impact_small = evaluate_restructuring(_small_org(), kpis, s)
    impact_large = evaluate_restructuring(_large_org(), kpis, s)
    # Smaller org has more SPOF risk to resolve via hiring
    assert impact_small.risk_delta <= impact_large.risk_delta, (
        "Smaller org should see greater risk reduction from adding one person"
    )


# ---------------------------------------------------------------------------
# OUTSOURCE_STAGE: more departments → higher compliance risk
# ---------------------------------------------------------------------------


def test_outsource_risk_scales_with_dept_count():
    kpis = _make_kpis()
    s = RestructuringScenario("s", OUTSOURCE_STAGE, "Outsource")
    impact_small = evaluate_restructuring(_small_org(), kpis, s)
    impact_large = evaluate_restructuring(_large_org(), kpis, s)
    assert impact_large.risk_delta >= impact_small.risk_delta, (
        "Larger org (more depts) should have equal or greater compliance risk when outsourcing"
    )


# ---------------------------------------------------------------------------
# Smoke test: all scenario types run without error for all org shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_type", [
    CENTRALIZE_TEAM, DECENTRALIZE_TEAM, ADD_SHARED_SERVICES, OUTSOURCE_STAGE,
    CREATE_AI_OPS_TEAM, HIRE_ADDITIONAL_STAFF, REDUCE_APPROVAL_LAYERS,
])
@pytest.mark.parametrize("org_fn", [_small_org, _large_org, _ai_heavy_org, _manager_heavy_org])
def test_all_scenarios_all_org_shapes(scenario_type, org_fn):
    kpis = _make_kpis()
    scenario = RestructuringScenario("s", scenario_type, scenario_type)
    impact = evaluate_restructuring(org_fn(), kpis, scenario)
    assert isinstance(impact.summary, str)
    assert len(impact.summary) > 0
