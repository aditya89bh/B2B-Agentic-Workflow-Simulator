"""Tests for Phase 6 production-readiness fixes: resource wiring, SPOF, edge cases."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.cross_workflow import (
    CrossWorkflowSimulator,
    WorkflowRunConfig,
    _actor_busy_minutes,
)
from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.examples.saas_org import (
    build_saas_org,
    build_saas_shared_resources,
)
from b2b_workflow_simulator.growth import GrowthConfig, project_growth
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.org_health import (
    CROSS_TEAM_DEPENDENCY,
    SINGLE_POINT_OF_FAILURE,
    compute_org_health,
)
from b2b_workflow_simulator.org_model import Department, Organization, Role
from b2b_workflow_simulator.shared_resources import (
    SOFTWARE_TOOL,
    SharedResource,
    SharedResourcePool,
)

# ---------------------------------------------------------------------------
# _actor_busy_minutes fallback
# ---------------------------------------------------------------------------


def test_actor_busy_minutes_uses_kpi_when_populated():
    wf = sales_lead_qualification.build_before_workflow()
    kpi = KPIResult(workflow_name="test", actor_busy_minutes={"ae": 120.0})
    result = _actor_busy_minutes(wf, kpi)
    assert result == {"ae": 120.0}


def test_actor_busy_minutes_falls_back_to_node_durations():
    wf = sales_lead_qualification.build_before_workflow()
    kpi = KPIResult(workflow_name="test")
    for node_id in wf.nodes:
        kpi.node_total_duration_minutes[node_id] = 30.0
    result = _actor_busy_minutes(wf, kpi)
    assert len(result) > 0
    for actor_id in result:
        assert actor_id in wf.actors


def test_actor_busy_minutes_fallback_returns_empty_for_no_durations():
    wf = sales_lead_qualification.build_before_workflow()
    kpi = KPIResult(workflow_name="test")
    result = _actor_busy_minutes(wf, kpi)
    assert all(v == 0.0 for v in result.values())


# ---------------------------------------------------------------------------
# SharedResourcePool.record_usage_from_kpi with actor_ids
# ---------------------------------------------------------------------------


def test_record_usage_from_kpi_populates_contention():
    pool = SharedResourcePool(org_id="test")
    pool.add_resource(SharedResource(
        resource_id="ai-plat",
        name="AI Platform",
        resource_type=SOFTWARE_TOOL,
        capacity_minutes_per_day=100.0,
        actor_ids=["ae"],
    ))
    pool.record_usage_from_kpi("wf-1", "sales", {"ae": 60.0, "sdr": 10.0})
    c = pool.compute_contention("ai-plat")
    assert c.total_demand_minutes == pytest.approx(60.0)
    assert c.contention_ratio == pytest.approx(0.6)


def test_record_usage_from_kpi_ignores_resource_with_no_actor_ids():
    pool = SharedResourcePool(org_id="test")
    pool.add_resource(SharedResource(
        resource_id="r1", name="R1",
        resource_type=SOFTWARE_TOOL, capacity_minutes_per_day=100.0,
        actor_ids=[],
    ))
    pool.record_usage_from_kpi("wf-1", "d1", {"ae": 50.0})
    assert pool.compute_contention("r1").total_demand_minutes == 0.0


def test_record_usage_from_kpi_skips_zero_usage():
    pool = SharedResourcePool(org_id="test")
    pool.add_resource(SharedResource(
        resource_id="r1", name="R1",
        resource_type=SOFTWARE_TOOL, capacity_minutes_per_day=100.0,
        actor_ids=["ae"],
    ))
    pool.record_usage_from_kpi("wf-1", "d1", {"sdr": 50.0})
    assert len(pool.usage_records) == 0


# ---------------------------------------------------------------------------
# CrossWorkflowSimulator + SharedResourcePool integration
# ---------------------------------------------------------------------------


def test_cross_workflow_simulator_records_usage_into_pool():
    org = Organization(org_id="o", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))

    pool = build_saas_shared_resources()
    wf = sales_lead_qualification.build_after_workflow()
    sim = CrossWorkflowSimulator(org, seed=42, shared_resource_pool=pool)
    sim.add_workflow(WorkflowRunConfig(workflow=wf, num_cases=100, dept_id="sales"))
    sim.run()

    ai_contention = pool.compute_contention("ai-platform")
    assert ai_contention.total_demand_minutes > 0.0


def test_cross_workflow_simulator_without_pool_does_not_crash():
    org = Organization(org_id="o", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))
    wf = sales_lead_qualification.build_after_workflow()
    sim = CrossWorkflowSimulator(org, seed=42)
    sim.add_workflow(WorkflowRunConfig(workflow=wf, num_cases=50))
    result = sim.run()
    assert result.total_cases == 50


def test_cross_workflow_pool_accessible_after_run():
    org = Organization(org_id="o", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))
    pool = SharedResourcePool(org_id="o")
    sim = CrossWorkflowSimulator(org, seed=1, shared_resource_pool=pool)
    assert sim.shared_resource_pool is pool


def test_saas_cross_workflow_gives_non_zero_contention():
    """End-to-end: SaaS simulation → resource pool shows real contention."""
    org = build_saas_org()
    pool = build_saas_shared_resources()
    sim = CrossWorkflowSimulator(org, seed=42, shared_resource_pool=pool)
    sim.add_workflow(WorkflowRunConfig(
        workflow=sales_lead_qualification.build_after_workflow(),
        num_cases=200, dept_id="sales",
    ))
    sim.add_workflow(WorkflowRunConfig(
        workflow=invoice_processing.build_after_workflow(),
        num_cases=200, dept_id="finance",
    ))
    sim.run()
    contentions = pool.all_contentions(days=22)
    non_zero = [c for c in contentions if c.total_demand_minutes > 0]
    assert len(non_zero) > 0, "Expected non-zero contention for at least one resource"


# ---------------------------------------------------------------------------
# SPOF score uses org structure
# ---------------------------------------------------------------------------


def _make_single_role_org() -> Organization:
    org = Organization(org_id="o", name="O")
    org.add_department(Department(dept_id="d1", name="D1 (single role)"))
    org.add_department(Department(dept_id="d2", name="D2 (two roles)"))
    org.add_role(Role(role_id="r1", name="Only Role", actor_id="a1", department_id="d1"))
    org.add_role(Role(role_id="r2", name="Role A", actor_id="a2", department_id="d2"))
    org.add_role(Role(role_id="r3", name="Role B", actor_id="a3", department_id="d2"))
    return org


def test_spof_score_penalises_single_role_departments():
    org_single = _make_single_role_org()
    org_full = Organization(org_id="o2", name="O2")
    org_full.add_department(Department(dept_id="d1", name="D1"))
    org_full.add_department(Department(dept_id="d2", name="D2"))
    for i in range(4):
        org_full.add_role(Role(
            role_id=f"r{i}", name=f"R{i}", actor_id=f"a{i}", department_id="d1" if i < 2 else "d2",
        ))

    hs_single = compute_org_health(org_single, None, None, {})
    hs_full = compute_org_health(org_full, None, None, {})

    spof_single = hs_single.factor(SINGLE_POINT_OF_FAILURE)
    spof_full = hs_full.factor(SINGLE_POINT_OF_FAILURE)
    assert spof_single is not None
    assert spof_full is not None
    assert spof_single.score <= spof_full.score


def test_spof_score_explanation_mentions_single_role_depts():
    org = _make_single_role_org()
    hs = compute_org_health(org, None, None, {})
    spof = hs.factor(SINGLE_POINT_OF_FAILURE)
    assert spof is not None
    assert "dept" in spof.explanation.lower()


# ---------------------------------------------------------------------------
# Workflow concentration factor
# ---------------------------------------------------------------------------


def test_cross_team_factor_name_updated():
    org = build_saas_org()
    hs = compute_org_health(org, None, None, {})
    wc = hs.factor(CROSS_TEAM_DEPENDENCY)
    assert wc is not None
    assert "Workflow" in wc.name or "Concentration" in wc.name


def test_cross_team_factor_explanation_mentions_workflows_per_team():
    org = build_saas_org()
    hs = compute_org_health(org, None, None, {})
    wc = hs.factor(CROSS_TEAM_DEPENDENCY)
    assert wc is not None
    assert "workflow" in wc.explanation.lower()
    assert "team" in wc.explanation.lower()


# ---------------------------------------------------------------------------
# Growth projection uses org headcount when base_headcount not set
# ---------------------------------------------------------------------------


def test_growth_projection_org_id_matches_org():
    org = build_saas_org()
    cfg = GrowthConfig(base_cases_per_month=100)
    proj = project_growth(org, None, cfg)
    assert proj.org_id == org.org_id
    assert proj.org_name == org.name


# ---------------------------------------------------------------------------
# SharedResource actor_ids field
# ---------------------------------------------------------------------------


def test_shared_resource_actor_ids_default_empty():
    res = SharedResource(
        resource_id="r1", name="R1",
        resource_type=SOFTWARE_TOOL, capacity_minutes_per_day=100.0,
    )
    assert res.actor_ids == []


def test_saas_shared_resources_actor_ids_wired():
    pool = build_saas_shared_resources()
    ai_platform = pool.resource("ai-platform")
    assert len(ai_platform.actor_ids) > 0
    assert "intake_agent" in ai_platform.actor_ids


def test_saas_shared_resources_resource_count_is_eight():
    pool = build_saas_shared_resources()
    assert len(pool.resources) == 8
