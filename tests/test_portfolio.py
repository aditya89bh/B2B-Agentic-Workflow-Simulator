import pytest

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.portfolio import WorkflowPortfolio


def make_kpi(name: str, total_cost: float, wait_minutes: float = 0.0) -> KPIResult:
    return KPIResult(
        workflow_name=name,
        total_cases=100,
        completed_cases=90,
        failed_cases=10,
        total_cost=total_cost,
        total_duration_minutes=1000.0,
        total_wait_minutes=wait_minutes,
    )


def test_add_entry_returns_self_for_chaining():
    portfolio = WorkflowPortfolio(name="Q1")

    result = portfolio.add_entry("workflow-a", make_kpi("Before", 1000.0), make_kpi("After", 400.0))

    assert result is portfolio
    assert len(portfolio.entries) == 1


def test_ranked_orders_by_total_cost_savings_by_default():
    portfolio = WorkflowPortfolio(name="Q1")
    portfolio.add_entry("small-savings", make_kpi("Before", 1000.0), make_kpi("After", 900.0))
    portfolio.add_entry("big-savings", make_kpi("Before", 1000.0), make_kpi("After", 200.0))

    ranked = portfolio.ranked()

    assert [entry.name for entry in ranked] == ["big-savings", "small-savings"]


def test_ranked_supports_roi_percentage():
    portfolio = WorkflowPortfolio(name="Q1")
    # Same absolute savings, but a much higher starting cost for "low-roi".
    portfolio.add_entry("low-roi", make_kpi("Before", 10000.0), make_kpi("After", 9000.0))
    portfolio.add_entry("high-roi", make_kpi("Before", 2000.0), make_kpi("After", 1000.0))

    ranked = portfolio.ranked(by="roi_percentage")

    assert ranked[0].name == "high-roi"


def test_ranked_rejects_unknown_metric():
    portfolio = WorkflowPortfolio(name="Q1")
    portfolio.add_entry("workflow-a", make_kpi("Before", 1000.0), make_kpi("After", 400.0))

    with pytest.raises(ValueError, match="Unknown ranking metric"):
        portfolio.ranked(by="not_a_real_metric")


def test_summary_aggregates_cost_across_entries():
    portfolio = WorkflowPortfolio(name="Q1")
    portfolio.add_entry("workflow-a", make_kpi("Before", 1000.0), make_kpi("After", 400.0))
    portfolio.add_entry("workflow-b", make_kpi("Before", 2000.0), make_kpi("After", 1500.0))

    summary = portfolio.summary()

    assert summary.workflow_count == 2
    assert summary.total_before_cost == 3000.0
    assert summary.total_after_cost == 1900.0
    assert summary.total_cost_savings == 1100.0
    assert summary.portfolio_roi_percentage == pytest.approx(1100.0 / 3000.0 * 100.0)


def test_summary_aggregates_wait_time_savings():
    portfolio = WorkflowPortfolio(name="Q1")
    portfolio.add_entry(
        "workflow-a",
        make_kpi("Before", 1000.0, wait_minutes=500.0),
        make_kpi("After", 400.0, wait_minutes=100.0),
    )

    summary = portfolio.summary()

    assert summary.total_wait_minutes_saved == pytest.approx(400.0)


def test_summary_computes_payback_when_implementation_costs_given():
    portfolio = WorkflowPortfolio(name="Q1")
    portfolio.add_entry(
        "workflow-a",
        make_kpi("Before", 1000.0),
        make_kpi("After", 400.0),
        implementation_cost=300.0,
    )
    portfolio.add_entry(
        "workflow-b",
        make_kpi("Before", 2000.0),
        make_kpi("After", 1500.0),
        implementation_cost=200.0,
    )

    summary = portfolio.summary()

    assert summary.total_implementation_cost == 500.0
    assert summary.payback_feasible is True
    assert summary.payback_in_periods == pytest.approx(500.0 / 1100.0)


def test_summary_marks_payback_infeasible_without_implementation_cost():
    portfolio = WorkflowPortfolio(name="Q1")
    portfolio.add_entry("workflow-a", make_kpi("Before", 1000.0), make_kpi("After", 400.0))

    summary = portfolio.summary()

    assert summary.total_implementation_cost == 0.0
    assert summary.payback_feasible is False
    assert summary.payback_in_periods is None


def test_summary_handles_empty_portfolio():
    portfolio = WorkflowPortfolio(name="Empty")

    summary = portfolio.summary()

    assert summary.workflow_count == 0
    assert summary.total_before_cost == 0.0
    assert summary.portfolio_roi_percentage is None
