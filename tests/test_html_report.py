from b2b_workflow_simulator.html_report import render_diff_html, render_portfolio_html
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.portfolio import WorkflowPortfolio
from b2b_workflow_simulator.redesign import compare_workflows


def make_before_kpi(name: str = "Before") -> KPIResult:
    return KPIResult(
        workflow_name=name,
        total_cases=100,
        completed_cases=70,
        failed_cases=30,
        total_cost=10000.0,
        total_duration_minutes=6000.0,
        node_total_duration_minutes={"a": 4000.0, "b": 2000.0},
        actor_utilization={"human_rep": 0.9},
    )


def make_after_kpi(name: str = "After") -> KPIResult:
    return KPIResult(
        workflow_name=name,
        total_cases=100,
        completed_cases=90,
        failed_cases=10,
        total_cost=4000.0,
        total_duration_minutes=2000.0,
        total_escalations=15,
        node_total_duration_minutes={"a": 1500.0, "b": 500.0},
        actor_utilization={"ai_agent": 0.95},
    )


def test_render_diff_html_is_well_formed_document():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert output.startswith("<!DOCTYPE html>")
    assert "<html" in output
    assert "</html>" in output
    assert "<title>" in output


def test_render_diff_html_includes_workflow_names():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert "Before" in output
    assert "After" in output


def test_render_diff_html_escapes_special_characters_in_names():
    before = make_before_kpi(name="Before <script>alert('x')</script>")
    after = make_after_kpi(name="After & Co.")
    diff = compare_workflows(before, after)

    output = render_diff_html(diff)

    assert "<script>alert" not in output
    assert "&lt;script&gt;" in output
    assert "After &amp; Co." in output


def test_render_diff_html_includes_all_expected_sections():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert "KPI Comparison" in output
    assert "ROI Summary" in output
    assert "Bottlenecks" in output
    assert "Actor Utilization" in output
    assert "Risks" in output
    assert "Recommendation" in output


def test_render_diff_html_includes_payback_when_implementation_cost_given():
    diff = compare_workflows(make_before_kpi(), make_after_kpi(), implementation_cost=1000.0)

    output = render_diff_html(diff)

    assert "Payback" in output


def test_render_diff_html_marks_cost_reduction_as_positive():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert 'class="positive"' in output


def build_portfolio() -> WorkflowPortfolio:
    portfolio = WorkflowPortfolio(name="Q1 Transformation")
    portfolio.add_entry(
        "workflow-a", make_before_kpi(), make_after_kpi(), implementation_cost=1000.0
    )
    return portfolio


def test_render_portfolio_html_is_well_formed_document():
    output = render_portfolio_html(build_portfolio())

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_render_portfolio_html_includes_portfolio_name():
    output = render_portfolio_html(build_portfolio())

    assert "Q1 Transformation" in output


def test_render_portfolio_html_includes_all_expected_sections():
    output = render_portfolio_html(build_portfolio())

    assert "Workflow Ranking" in output
    assert "Aggregate ROI" in output
    assert "Risks" in output
    assert "Recommended Rollout Order" in output


def test_render_portfolio_html_escapes_workflow_names():
    portfolio = WorkflowPortfolio(name="<b>Bold</b> Portfolio")
    portfolio.add_entry("workflow<script>", make_before_kpi(), make_after_kpi())

    output = render_portfolio_html(portfolio)

    assert "<script>" not in output.split("<style>")[1]
    assert "&lt;b&gt;Bold&lt;/b&gt;" in output


def test_render_portfolio_html_handles_empty_portfolio():
    portfolio = WorkflowPortfolio(name="Empty")

    output = render_portfolio_html(portfolio)

    assert "0 workflow(s)" in output
