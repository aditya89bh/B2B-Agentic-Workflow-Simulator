from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.portfolio import WorkflowPortfolio
from b2b_workflow_simulator.report import generate_portfolio_report


def make_kpi(name: str, total_cost: float, completed: int = 90, failed: int = 10) -> KPIResult:
    return KPIResult(
        workflow_name=name,
        total_cases=100,
        completed_cases=completed,
        failed_cases=failed,
        total_cost=total_cost,
        total_duration_minutes=1000.0,
    )


def build_portfolio() -> WorkflowPortfolio:
    portfolio = WorkflowPortfolio(name="Q1 Transformation")
    portfolio.add_entry(
        "big-savings-workflow",
        make_kpi("Before", 10000.0),
        make_kpi("After", 4000.0),
        implementation_cost=1000.0,
    )
    portfolio.add_entry(
        "small-savings-workflow",
        make_kpi("Before", 2000.0),
        make_kpi("After", 1800.0),
        implementation_cost=500.0,
    )
    return portfolio


def test_portfolio_report_has_all_expected_sections():
    report = generate_portfolio_report(build_portfolio())

    assert "WORKFLOW PORTFOLIO ANALYSIS" in report
    assert "EXECUTIVE SUMMARY" in report
    assert "WORKFLOW RANKING" in report
    assert "AGGREGATE ROI & PAYBACK" in report
    assert "RISKS" in report
    assert "RECOMMENDED ROLLOUT ORDER" in report


def test_portfolio_report_includes_portfolio_name():
    report = generate_portfolio_report(build_portfolio())

    assert "Q1 Transformation" in report


def test_portfolio_report_ranks_higher_savings_workflow_first():
    report = generate_portfolio_report(build_portfolio())

    ranking_section = report.split("WORKFLOW RANKING")[1].split("AGGREGATE")[0]
    rollout_section = report.split("RECOMMENDED ROLLOUT ORDER")[1]

    assert ranking_section.index("big-savings-workflow") < ranking_section.index(
        "small-savings-workflow"
    )
    assert rollout_section.index("1. big-savings-workflow") < rollout_section.index(
        "2. small-savings-workflow"
    )


def test_portfolio_report_can_rank_by_roi_percentage():
    portfolio = WorkflowPortfolio(name="Q1")
    # Low absolute savings, but much higher ROI percentage.
    portfolio.add_entry("high-roi", make_kpi("Before", 1000.0), make_kpi("After", 100.0))
    portfolio.add_entry("low-roi", make_kpi("Before", 10000.0), make_kpi("After", 9500.0))

    report = generate_portfolio_report(portfolio, rank_by="roi_percentage")

    ranking_section = report.split("WORKFLOW RANKING")[1].split("AGGREGATE")[0]
    assert ranking_section.index("high-roi") < ranking_section.index("low-roi")


def test_portfolio_report_includes_aggregate_payback_when_costs_given():
    report = generate_portfolio_report(build_portfolio())

    assert "Total implementation cost" in report
    assert "Payback (case-volume periods)" in report


def test_portfolio_report_omits_payback_without_implementation_cost():
    portfolio = WorkflowPortfolio(name="No Cost Data")
    portfolio.add_entry("workflow-a", make_kpi("Before", 1000.0), make_kpi("After", 400.0))

    report = generate_portfolio_report(portfolio)

    assert "Total implementation cost" not in report


def test_portfolio_report_flags_no_risks_when_metrics_are_clean():
    report = generate_portfolio_report(build_portfolio())

    assert "No material risks identified" in report


def test_portfolio_report_aggregates_risks_per_workflow():
    portfolio = WorkflowPortfolio(name="Risky")
    risky_before = make_kpi("Before", 10000.0, completed=90, failed=10)
    risky_after = make_kpi("After", 5000.0, completed=50, failed=50)
    portfolio.add_entry("risky-workflow", risky_before, risky_after)

    report = generate_portfolio_report(portfolio)

    assert "[risky-workflow]" in report


def test_portfolio_report_handles_empty_portfolio():
    portfolio = WorkflowPortfolio(name="Empty")

    report = generate_portfolio_report(portfolio)

    assert "0 workflow redesign(s)" in report
