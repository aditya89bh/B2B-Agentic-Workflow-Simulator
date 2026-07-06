"""Tests for cross_workflow: CrossWorkflowSimulator, CrossWorkflowResult, WorkflowRunConfig."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.cross_workflow import (
    CrossWorkflowResult,
    CrossWorkflowSimulator,
    WorkflowRunConfig,
)
from b2b_workflow_simulator.examples import (
    invoice_processing,
    sales_lead_qualification,
)
from b2b_workflow_simulator.org_model import Department, Organization


def _make_org() -> Organization:
    org = Organization(org_id="test-org", name="Test Org")
    org.add_department(Department(dept_id="sales", name="Sales"))
    org.add_department(Department(dept_id="finance", name="Finance"))
    return org


# ---------------------------------------------------------------------------
# WorkflowRunConfig validation
# ---------------------------------------------------------------------------


def test_run_config_invalid_num_cases_raises():
    wf = sales_lead_qualification.build_before_workflow()
    with pytest.raises(ValueError, match="positive"):
        WorkflowRunConfig(workflow=wf, num_cases=0)


def test_run_config_invalid_engine_raises():
    wf = sales_lead_qualification.build_before_workflow()
    with pytest.raises(ValueError, match="engine"):
        WorkflowRunConfig(workflow=wf, num_cases=10, engine="bad-engine")


def test_run_config_valid_fields():
    wf = sales_lead_qualification.build_before_workflow()
    cfg = WorkflowRunConfig(workflow=wf, num_cases=50, dept_id="sales", seed=7)
    assert cfg.num_cases == 50
    assert cfg.dept_id == "sales"
    assert cfg.seed == 7


# ---------------------------------------------------------------------------
# CrossWorkflowSimulator
# ---------------------------------------------------------------------------


def test_simulator_add_workflow():
    org = _make_org()
    sim = CrossWorkflowSimulator(org, seed=42)
    wf = sales_lead_qualification.build_before_workflow()
    sim.add_workflow(WorkflowRunConfig(workflow=wf, num_cases=50))
    assert sim.workflow_count == 1


def test_simulator_add_workflow_returns_self():
    org = _make_org()
    sim = CrossWorkflowSimulator(org, seed=42)
    wf = sales_lead_qualification.build_before_workflow()
    result = sim.add_workflow(WorkflowRunConfig(workflow=wf, num_cases=50))
    assert result is sim


def test_simulator_run_single_workflow():
    org = _make_org()
    sim = CrossWorkflowSimulator(org, seed=42)
    wf = sales_lead_qualification.build_before_workflow()
    sim.add_workflow(WorkflowRunConfig(workflow=wf, num_cases=50))
    result = sim.run()
    assert wf.workflow_id in result.workflow_ids
    assert result.total_cases == 50


def test_simulator_run_multiple_workflows():
    org = _make_org()
    sim = CrossWorkflowSimulator(org, seed=42)
    sim.add_workflow(WorkflowRunConfig(
        workflow=sales_lead_qualification.build_before_workflow(), num_cases=100
    ))
    sim.add_workflow(WorkflowRunConfig(
        workflow=invoice_processing.build_before_workflow(), num_cases=80
    ))
    result = sim.run()
    assert len(result.workflow_ids) == 2
    assert result.total_cases == 180


def test_simulator_organization_accessor():
    org = _make_org()
    sim = CrossWorkflowSimulator(org)
    assert sim.organization is org


def test_simulator_deterministic_with_seed():
    org = _make_org()
    wf = sales_lead_qualification.build_before_workflow()

    sim1 = CrossWorkflowSimulator(org, seed=7)
    sim1.add_workflow(WorkflowRunConfig(workflow=wf, num_cases=100))
    r1 = sim1.run()

    wf2 = sales_lead_qualification.build_before_workflow()
    sim2 = CrossWorkflowSimulator(org, seed=7)
    sim2.add_workflow(WorkflowRunConfig(workflow=wf2, num_cases=100))
    r2 = sim2.run()

    assert r1.kpi_for(wf.workflow_id).completed_cases == r2.kpi_for(wf2.workflow_id).completed_cases


def test_simulator_each_workflow_gets_own_runner():
    org = _make_org()
    wf_a = sales_lead_qualification.build_before_workflow()
    wf_b = invoice_processing.build_before_workflow()
    sim = CrossWorkflowSimulator(org, seed=42)
    sim.add_workflow(WorkflowRunConfig(workflow=wf_a, num_cases=50))
    sim.add_workflow(WorkflowRunConfig(workflow=wf_b, num_cases=50))
    result = sim.run()
    kpi_a = result.kpi_for(wf_a.workflow_id)
    kpi_b = result.kpi_for(wf_b.workflow_id)
    assert kpi_a.workflow_name != kpi_b.workflow_name


# ---------------------------------------------------------------------------
# CrossWorkflowResult
# ---------------------------------------------------------------------------


def _make_result() -> CrossWorkflowResult:
    org = _make_org()
    sim = CrossWorkflowSimulator(org, seed=1)
    sim.add_workflow(WorkflowRunConfig(
        workflow=sales_lead_qualification.build_before_workflow(), num_cases=100,
    ))
    sim.add_workflow(WorkflowRunConfig(
        workflow=invoice_processing.build_before_workflow(), num_cases=100,
    ))
    return sim.run()


def test_result_total_cost_positive():
    result = _make_result()
    assert result.total_cost > 0


def test_result_avg_completion_rate_between_0_and_1():
    result = _make_result()
    assert 0.0 <= result.avg_completion_rate <= 1.0


def test_result_avg_cost_per_case():
    result = _make_result()
    assert result.avg_cost_per_case == pytest.approx(result.total_cost / result.total_cases)


def test_result_kpi_for_unknown_raises():
    result = _make_result()
    with pytest.raises(KeyError):
        result.kpi_for("unknown-workflow-id")


def test_result_workflow_names():
    result = _make_result()
    names = result.workflow_names()
    assert len(names) == 2
    assert all(isinstance(n, str) for n in names)


def test_result_total_completed_le_total_cases():
    result = _make_result()
    assert result.total_completed <= result.total_cases


def test_result_empty_simulator():
    org = _make_org()
    sim = CrossWorkflowSimulator(org)
    result = sim.run()
    assert result.total_cases == 0
    assert result.avg_completion_rate == 0.0
    assert result.total_cost == 0.0
