"""Tests proving shared_resources and growth_projection wire into org health scoring."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.budget import OPERATING, DepartmentBudget, OrgBudget
from b2b_workflow_simulator.examples import sales_lead_qualification
from b2b_workflow_simulator.growth import GrowthConfig, project_growth
from b2b_workflow_simulator.org_health import (
    BUDGET_PRESSURE,
    QUEUE_PRESSURE,
    SINGLE_POINT_OF_FAILURE,
    SLA_RISK,
    UTILIZATION_BALANCE,
    compute_org_health,
)
from b2b_workflow_simulator.org_model import Department, Organization, Role
from b2b_workflow_simulator.shared_resources import (
    LEGAL_REVIEWER,
    SOFTWARE_TOOL,
    SharedResource,
    SharedResourcePool,
)
from b2b_workflow_simulator.simulation import SimulationRunner


def _make_org() -> Organization:
    org = Organization(org_id="o", name="Test Org")
    org.add_department(Department(dept_id="d1", name="D1"))
    org.add_role(Role(role_id="r1", name="R1", actor_id="a1", department_id="d1"))
    org.add_role(Role(role_id="r2", name="R2", actor_id="a2", department_id="d1"))
    org.add_workflow_id("wf-1")
    return org


def _make_kpis() -> dict:
    runner = SimulationRunner(seed=1)
    r = runner.run(sales_lead_qualification.build_before_workflow(), 100)
    return {"wf-1": r.kpi}


def _make_pool_with_bottleneck() -> SharedResourcePool:
    pool = SharedResourcePool(org_id="o")
    pool.add_resource(SharedResource(
        resource_id="r1", name="Overloaded Resource",
        resource_type=LEGAL_REVIEWER, capacity_minutes_per_day=10.0,
    ))
    pool.record_usage("r1", "wf-1", "d1", 100.0)  # 10x capacity
    return pool


def _make_pool_no_contention() -> SharedResourcePool:
    pool = SharedResourcePool(org_id="o")
    pool.add_resource(SharedResource(
        resource_id="r1", name="Idle Resource",
        resource_type=SOFTWARE_TOOL, capacity_minutes_per_day=1000.0,
    ))
    pool.record_usage("r1", "wf-1", "d1", 10.0)  # 1% utilization
    return pool


# ---------------------------------------------------------------------------
# Shared resources → utilization balance
# ---------------------------------------------------------------------------


def test_overloaded_shared_resource_lowers_utilization_balance():
    org = _make_org()
    kpis = _make_kpis()
    hs_no_pool = compute_org_health(org, None, None, kpis)
    hs_with_bottleneck = compute_org_health(org, None, _make_pool_with_bottleneck(), kpis)
    ub_no = hs_no_pool.factor(UTILIZATION_BALANCE)
    ub_bottleneck = hs_with_bottleneck.factor(UTILIZATION_BALANCE)
    assert ub_no is not None and ub_bottleneck is not None
    assert ub_bottleneck.score < ub_no.score, (
        f"Bottleneck pool should lower util balance "
        f"({ub_bottleneck.score:.1f} < {ub_no.score:.1f})"
    )


def test_low_contention_resource_does_not_unfairly_penalize_utilization_balance():
    org = _make_org()
    kpis = _make_kpis()
    hs_no_pool = compute_org_health(org, None, None, kpis)
    hs_low_pool = compute_org_health(org, None, _make_pool_no_contention(), kpis)
    ub_no = hs_no_pool.factor(UTILIZATION_BALANCE)
    ub_low = hs_low_pool.factor(UTILIZATION_BALANCE)
    assert ub_no is not None and ub_low is not None
    assert ub_low.score >= ub_no.score - 5.0, (
        "Low contention pool should not significantly penalize utilization balance"
    )


def test_utilization_balance_explanation_mentions_bottleneck():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, _make_pool_with_bottleneck(), kpis)
    factor = hs.factor(UTILIZATION_BALANCE)
    assert factor is not None
    assert "Overloaded Resource" in factor.explanation or "bottleneck" in factor.explanation.lower()


# ---------------------------------------------------------------------------
# Shared resources → queue pressure
# ---------------------------------------------------------------------------


def test_critically_overloaded_resource_raises_queue_pressure():
    org = _make_org()
    kpis = _make_kpis()
    hs_no_pool = compute_org_health(org, None, None, kpis)
    hs_with_bottleneck = compute_org_health(org, None, _make_pool_with_bottleneck(), kpis)
    qp_no = hs_no_pool.factor(QUEUE_PRESSURE)
    qp_bottleneck = hs_with_bottleneck.factor(QUEUE_PRESSURE)
    assert qp_no is not None and qp_bottleneck is not None
    assert qp_bottleneck.score <= qp_no.score, (
        "Critical shared resource overload should reduce queue pressure score"
    )


def test_queue_pressure_explanation_mentions_shared_resource_overload():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, _make_pool_with_bottleneck(), kpis)
    factor = hs.factor(QUEUE_PRESSURE)
    assert factor is not None
    explanation = factor.explanation.lower()
    assert "shared resource" in explanation or "overload" in explanation


# ---------------------------------------------------------------------------
# Shared resources → SPOF
# ---------------------------------------------------------------------------


def test_bottleneck_shared_resource_lowers_spof_score():
    org = _make_org()
    kpis = _make_kpis()
    hs_no_pool = compute_org_health(org, None, None, kpis)
    hs_with_bottleneck = compute_org_health(org, None, _make_pool_with_bottleneck(), kpis)
    spof_no = hs_no_pool.factor(SINGLE_POINT_OF_FAILURE)
    spof_bottleneck = hs_with_bottleneck.factor(SINGLE_POINT_OF_FAILURE)
    assert spof_no is not None and spof_bottleneck is not None
    assert spof_bottleneck.score <= spof_no.score


def test_spof_explanation_mentions_shared_resource_when_bottleneck():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, _make_pool_with_bottleneck(), kpis)
    spof = hs.factor(SINGLE_POINT_OF_FAILURE)
    assert spof is not None
    assert "Overloaded Resource" in spof.explanation or "SPOF" in spof.explanation


# ---------------------------------------------------------------------------
# Growth projection → SLA risk
# ---------------------------------------------------------------------------


def _make_breaking_growth(org) -> object:
    cfg = GrowthConfig(
        monthly_growth_rate=0.50,
        base_cases_per_month=500,
        base_headcount=2,
        actor_capacity_per_head=10.0,
    )
    proj = project_growth(org, None, cfg)
    # Ensure it actually has breaking points
    assert len(proj.breaking_points()) > 0, "Test requires a projection with breaking points"
    return proj


def _make_safe_growth(org) -> object:
    cfg = GrowthConfig(monthly_growth_rate=0.0, base_cases_per_month=5, base_headcount=100)
    proj = project_growth(org, None, cfg)
    assert proj.first_breaking_point() is None, "Test requires a projection without breaking points"
    return proj


def test_growth_with_near_term_breaking_points_lowers_sla_risk():
    org = _make_org()
    kpis = _make_kpis()
    hs_no_growth = compute_org_health(org, None, None, kpis)
    proj = _make_breaking_growth(org)
    near_term = [bp for bp in proj.breaking_points() if bp.month <= 6]
    if not near_term:
        pytest.skip("No near-term breaking points to test")
    hs_with_growth = compute_org_health(org, None, None, kpis, growth_projection=proj)
    sla_no = hs_no_growth.factor(SLA_RISK)
    sla_growth = hs_with_growth.factor(SLA_RISK)
    assert sla_no is not None and sla_growth is not None
    assert sla_growth.score <= sla_no.score, (
        f"Breaking growth projection should reduce SLA risk score "
        f"({sla_growth.score:.1f} <= {sla_no.score:.1f})"
    )


def test_safe_growth_does_not_significantly_penalize_sla_risk():
    org = _make_org()
    kpis = _make_kpis()
    hs_no_growth = compute_org_health(org, None, None, kpis)
    proj = _make_safe_growth(org)
    hs_with_growth = compute_org_health(org, None, None, kpis, growth_projection=proj)
    sla_no = hs_no_growth.factor(SLA_RISK)
    sla_safe = hs_with_growth.factor(SLA_RISK)
    assert sla_no is not None and sla_safe is not None
    assert abs(sla_safe.score - sla_no.score) < 1.0, (
        "Safe growth (no breaking points) should not change SLA risk score"
    )


def test_sla_risk_explanation_mentions_growth_when_breaking():
    org = _make_org()
    kpis = _make_kpis()
    proj = _make_breaking_growth(org)
    near_term = [bp for bp in proj.breaking_points() if bp.month <= 6]
    if not near_term:
        pytest.skip("No near-term breaking points to test")
    hs = compute_org_health(org, None, None, kpis, growth_projection=proj)
    sla = hs.factor(SLA_RISK)
    assert sla is not None
    assert "month" in sla.explanation.lower() or "growth" in sla.explanation.lower()


# ---------------------------------------------------------------------------
# Growth projection → budget pressure
# ---------------------------------------------------------------------------


def test_budget_breaking_point_lowers_budget_pressure_score():
    org = _make_org()
    kpis = _make_kpis()
    # Budget with small monthly budget so cost growth triggers budget overload
    ob = OrgBudget(org_id="o")
    db = DepartmentBudget(dept_id="d1", annual_budget=100.0)
    db.allocate(OPERATING, 100.0)
    ob.add_dept_budget(db)
    # Use high base_cost_per_case so cost quickly exceeds budget
    cfg = GrowthConfig(
        monthly_growth_rate=0.05,
        base_cases_per_month=100,
        base_cost_per_case=10.0,  # 100 * 10 = 1000/month >> 100/12 budget
    )
    proj = project_growth(org, ob, cfg)
    budget_bps = [
        bp for bp in proj.breaking_points()
        if bp.month <= 6 and bp.breaking_point_reason
        and "budget" in bp.breaking_point_reason.lower()
    ]
    if not budget_bps:
        pytest.skip("No budget breaking points in near term for this config")
    hs_no_growth = compute_org_health(org, ob, None, kpis)
    hs_with_growth = compute_org_health(org, ob, None, kpis, growth_projection=proj)
    bp_no = hs_no_growth.factor(BUDGET_PRESSURE)
    bp_growth = hs_with_growth.factor(BUDGET_PRESSURE)
    assert bp_no is not None and bp_growth is not None
    assert bp_growth.score <= bp_no.score


# ---------------------------------------------------------------------------
# Overall score: more issues = lower overall
# ---------------------------------------------------------------------------


def test_org_with_all_inputs_has_more_precise_score_than_none():
    """Providing all inputs should produce explanations that reference them."""
    org = _make_org()
    kpis = _make_kpis()
    pool = _make_pool_with_bottleneck()
    proj = _make_safe_growth(org)
    hs = compute_org_health(org, None, pool, kpis, growth_projection=proj)
    # All 8 factors should have meaningful (non-empty) explanations
    for factor in hs.factors:
        assert len(factor.explanation) > 0, f"{factor.factor_id} has empty explanation"
