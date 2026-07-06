"""Tests for restructuring: RestructuringScenario, evaluate_restructuring, compare scenarios."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.budget import DepartmentBudget, OrgBudget
from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.org_model import Department, Organization
from b2b_workflow_simulator.restructuring import (
    ADD_SHARED_SERVICES,
    CENTRALIZE_TEAM,
    CREATE_AI_OPS_TEAM,
    DECENTRALIZE_TEAM,
    HIRE_ADDITIONAL_STAFF,
    REDUCE_APPROVAL_LAYERS,
    SCENARIO_TYPE_LABELS,
    SCENARIO_TYPES,
    RestructuringImpact,
    RestructuringScenario,
    compare_restructuring_scenarios,
    evaluate_restructuring,
    generate_restructuring_report,
)
from b2b_workflow_simulator.simulation import SimulationRunner


def _make_org():
    org = Organization(org_id="co", name="Test Co")
    org.add_department(Department(dept_id="sales", name="Sales"))
    org.add_department(Department(dept_id="finance", name="Finance"))
    return org


def _make_kpis():
    runner = SimulationRunner(seed=42)
    r1 = runner.run(sales_lead_qualification.build_before_workflow(), 100)
    r2 = runner.run(invoice_processing.build_before_workflow(), 100)
    return {
        "sales-lead-qualification-before": r1.kpi,
        "invoice-processing-before": r2.kpi,
    }


def _make_scenario(scenario_type: str) -> RestructuringScenario:
    return RestructuringScenario(
        scenario_id=f"s-{scenario_type}",
        scenario_type=scenario_type,
        description=f"Evaluate {scenario_type}",
    )


# ---------------------------------------------------------------------------
# RestructuringScenario
# ---------------------------------------------------------------------------


def test_scenario_fields():
    s = RestructuringScenario(
        scenario_id="s1",
        scenario_type=CENTRALIZE_TEAM,
        description="Centralize the team",
        parameters={"headcount_delta": -2},
    )
    assert s.scenario_id == "s1"
    assert s.parameters["headcount_delta"] == -2


def test_scenario_default_parameters_empty():
    s = _make_scenario(CENTRALIZE_TEAM)
    assert s.parameters == {}


# ---------------------------------------------------------------------------
# evaluate_restructuring — each scenario type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_type", list(SCENARIO_TYPES))
def test_evaluate_restructuring_all_types(scenario_type):
    org = _make_org()
    kpis = _make_kpis()
    scenario = _make_scenario(scenario_type)
    impact = evaluate_restructuring(org, kpis, scenario)
    assert isinstance(impact, RestructuringImpact)
    assert isinstance(impact.summary, str)
    assert len(impact.summary) > 0


def test_centralize_team_reduces_cost():
    org = _make_org()
    kpis = _make_kpis()
    scenario = _make_scenario(CENTRALIZE_TEAM)
    impact = evaluate_restructuring(org, kpis, scenario)
    assert impact.is_cost_positive


def test_decentralize_team_reduces_cycle_time():
    org = _make_org()
    kpis = _make_kpis()
    scenario = _make_scenario(DECENTRALIZE_TEAM)
    impact = evaluate_restructuring(org, kpis, scenario)
    assert impact.cycle_time_impact_minutes < 0


def test_create_ai_ops_reduces_risk():
    org = _make_org()
    kpis = _make_kpis()
    scenario = _make_scenario(CREATE_AI_OPS_TEAM)
    impact = evaluate_restructuring(org, kpis, scenario)
    assert impact.is_risk_positive


def test_hire_additional_staff_increases_headcount():
    org = _make_org()
    kpis = _make_kpis()
    scenario = RestructuringScenario(
        scenario_id="s", scenario_type=HIRE_ADDITIONAL_STAFF,
        description="Hire 3", parameters={"headcount_delta": 3},
    )
    impact = evaluate_restructuring(org, kpis, scenario)
    assert impact.staffing_delta == 3


def test_reduce_approval_layers_increases_risk():
    org = _make_org()
    kpis = _make_kpis()
    scenario = RestructuringScenario(
        scenario_id="s", scenario_type=REDUCE_APPROVAL_LAYERS,
        description="Remove 1 layer", parameters={"approval_layers_removed": 1},
    )
    impact = evaluate_restructuring(org, kpis, scenario)
    assert impact.risk_delta > 0


def test_unknown_scenario_type_returns_zero_impact():
    org = _make_org()
    kpis = _make_kpis()
    scenario = RestructuringScenario(
        scenario_id="s", scenario_type="unknown-type", description="Unknown"
    )
    impact = evaluate_restructuring(org, kpis, scenario)
    assert impact.cost_impact == 0.0
    assert impact.risk_delta == 0.0


def test_evaluate_with_org_budget():
    org = _make_org()
    kpis = _make_kpis()
    ob = OrgBudget(org_id="co")
    ob.add_dept_budget(DepartmentBudget(dept_id="sales", annual_budget=500_000.0))
    scenario = _make_scenario(ADD_SHARED_SERVICES)
    impact = evaluate_restructuring(org, kpis, scenario, ob)
    assert isinstance(impact, RestructuringImpact)


# ---------------------------------------------------------------------------
# compare_restructuring_scenarios
# ---------------------------------------------------------------------------


def test_compare_scenarios_sorted_by_net_benefit():
    org = _make_org()
    kpis = _make_kpis()
    scenarios = [_make_scenario(t) for t in SCENARIO_TYPES]
    impacts = compare_restructuring_scenarios(org, kpis, scenarios)
    assert len(impacts) == len(SCENARIO_TYPES)
    scores = [i.net_benefit_score for i in impacts]
    assert scores == sorted(scores, reverse=True)


def test_compare_single_scenario():
    org = _make_org()
    kpis = _make_kpis()
    impacts = compare_restructuring_scenarios(org, kpis, [_make_scenario(CENTRALIZE_TEAM)])
    assert len(impacts) == 1


# ---------------------------------------------------------------------------
# RestructuringImpact helpers
# ---------------------------------------------------------------------------


def test_impact_is_cost_positive_true():
    scenario = _make_scenario(CENTRALIZE_TEAM)
    impact = RestructuringImpact(
        scenario=scenario, cost_impact=-5000.0, cycle_time_impact_minutes=0.0,
        risk_delta=0.0, staffing_delta=0, budget_impact=0.0, summary="",
    )
    assert impact.is_cost_positive


def test_impact_is_cost_positive_false():
    scenario = _make_scenario(HIRE_ADDITIONAL_STAFF)
    impact = RestructuringImpact(
        scenario=scenario, cost_impact=5000.0, cycle_time_impact_minutes=0.0,
        risk_delta=0.0, staffing_delta=2, budget_impact=0.0, summary="",
    )
    assert not impact.is_cost_positive


def test_impact_is_risk_positive_true():
    scenario = _make_scenario(CREATE_AI_OPS_TEAM)
    impact = RestructuringImpact(
        scenario=scenario, cost_impact=0.0, cycle_time_impact_minutes=0.0,
        risk_delta=-10.0, staffing_delta=0, budget_impact=0.0, summary="",
    )
    assert impact.is_risk_positive


# ---------------------------------------------------------------------------
# generate_restructuring_report
# ---------------------------------------------------------------------------


def test_generate_restructuring_report_empty():
    assert generate_restructuring_report([]) == "No restructuring scenarios to report."


def test_generate_restructuring_report_contains_scenario_label():
    org = _make_org()
    kpis = _make_kpis()
    scenario = _make_scenario(CREATE_AI_OPS_TEAM)
    impacts = [evaluate_restructuring(org, kpis, scenario)]
    report = generate_restructuring_report(impacts)
    assert SCENARIO_TYPE_LABELS[CREATE_AI_OPS_TEAM] in report


def test_generate_restructuring_report_contains_cost_line():
    org = _make_org()
    kpis = _make_kpis()
    impacts = [evaluate_restructuring(org, kpis, _make_scenario(CENTRALIZE_TEAM))]
    report = generate_restructuring_report(impacts)
    assert "Cost impact" in report


def test_scenario_type_labels_complete():
    for stype in SCENARIO_TYPES:
        assert stype in SCENARIO_TYPE_LABELS
