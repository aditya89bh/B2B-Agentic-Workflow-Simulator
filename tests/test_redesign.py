import pytest

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.redesign import MetricDelta, compare_workflows


def make_before_kpi() -> KPIResult:
    return KPIResult(
        workflow_name="Before",
        total_cases=100,
        completed_cases=70,
        failed_cases=30,
        total_cost=10000.0,
        total_duration_minutes=6000.0,
        total_wait_minutes=500.0,
        total_escalations=0,
        node_total_duration_minutes={"a": 4000.0, "b": 2000.0},
        actor_utilization={"human_rep": 0.9},
    )


def make_after_kpi() -> KPIResult:
    return KPIResult(
        workflow_name="After",
        total_cases=100,
        completed_cases=90,
        failed_cases=10,
        total_cost=4000.0,
        total_duration_minutes=2000.0,
        total_wait_minutes=50.0,
        total_escalations=15,
        node_total_duration_minutes={"a": 1500.0, "b": 500.0},
        actor_utilization={"ai_agent": 0.4},
    )


def test_metric_delta_computes_absolute_and_percent_change():
    delta = MetricDelta(label="Total cost", before=10000.0, after=4000.0)

    assert delta.delta == -6000.0
    assert delta.percent_change == pytest.approx(-60.0)


def test_metric_delta_percent_change_is_none_when_before_is_zero():
    delta = MetricDelta(label="Escalation rate", before=0.0, after=0.2)

    assert delta.percent_change is None


def test_compare_workflows_computes_all_headline_metrics():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    assert diff.before_name == "Before"
    assert diff.after_name == "After"
    assert diff.completion_rate.before == 0.7
    assert diff.completion_rate.after == 0.9
    assert diff.failure_rate.before == 0.3
    assert diff.failure_rate.after == 0.1
    assert diff.total_cost.before == 10000.0
    assert diff.total_cost.after == 4000.0
    assert diff.cost_per_case.before == 100.0
    assert diff.cost_per_case.after == 40.0
    assert diff.escalation_rate.after == 0.15


def test_compare_workflows_exposes_metrics_in_stable_order():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    labels = [metric.label for metric in diff.metrics]

    assert labels == [
        "Completion rate",
        "Failure rate",
        "Total cost",
        "Cost per case",
        "Cycle time (minutes)",
        "Wait time (minutes)",
        "Escalation rate",
    ]


def test_compare_workflows_carries_bottlenecks_and_utilization():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    assert diff.before_bottlenecks[0] == ("a", 4000.0)
    assert diff.after_bottlenecks[0] == ("a", 1500.0)
    assert diff.before_utilization == {"human_rep": 0.9}
    assert diff.after_utilization == {"ai_agent": 0.4}


def test_roi_computes_savings_without_implementation_cost():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    assert diff.roi.total_cost_savings == 6000.0
    assert diff.roi.cost_savings_per_case == 60.0
    assert diff.roi.roi_percentage == pytest.approx(60.0)
    assert diff.roi.implementation_cost is None
    assert diff.roi.payback_in_cases is None
    assert diff.roi.payback_feasible is False


def test_roi_computes_payback_when_implementation_cost_given():
    diff = compare_workflows(make_before_kpi(), make_after_kpi(), implementation_cost=3000.0)

    assert diff.roi.payback_feasible is True
    assert diff.roi.payback_in_cases == pytest.approx(3000.0 / 60.0)


def test_roi_marks_payback_infeasible_when_redesign_costs_more():
    before = make_before_kpi()
    after = make_after_kpi()
    after.total_cost = 20000.0  # Redesign is more expensive per case, not less.

    diff = compare_workflows(before, after, implementation_cost=1000.0)

    assert diff.roi.payback_feasible is False
    assert diff.roi.payback_in_cases is None


def test_roi_percentage_is_none_when_before_cost_is_zero():
    before = make_before_kpi()
    before.total_cost = 0.0

    diff = compare_workflows(before, make_after_kpi())

    assert diff.roi.roi_percentage is None
