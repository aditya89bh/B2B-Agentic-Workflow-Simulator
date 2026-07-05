from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.report import generate_report


def make_before_kpi() -> KPIResult:
    return KPIResult(
        workflow_name="Before",
        total_cases=100,
        completed_cases=70,
        failed_cases=30,
        total_cost=10000.0,
        total_duration_minutes=6000.0,
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
        total_escalations=15,
        node_total_duration_minutes={"a": 1500.0, "b": 500.0},
        actor_utilization={"ai_agent": 0.95},
    )


def test_report_includes_workflow_names():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    report = generate_report(diff)

    assert "Before" in report
    assert "After" in report


def test_report_has_all_expected_sections():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    report = generate_report(diff)

    assert "EXECUTIVE SUMMARY" in report
    assert "KPI COMPARISON" in report
    assert "BOTTLENECKS" in report
    assert "ACTOR UTILIZATION" in report
    assert "RISKS" in report
    assert "RECOMMENDATION" in report


def test_report_states_cost_reduction_direction_correctly():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    report = generate_report(diff)

    assert "reduces total simulated cost" in report


def test_report_states_cost_increase_direction_when_redesign_is_costlier():
    before = make_before_kpi()
    after = make_after_kpi()
    after.total_cost = 20000.0

    diff = compare_workflows(before, after)
    report = generate_report(diff)

    assert "increases total simulated cost" in report


def test_report_flags_high_actor_utilization_as_a_risk():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    report = generate_report(diff)

    assert "ai_agent" in report
    assert "utilization" in report.lower()


def test_report_flags_no_risks_when_metrics_are_clean():
    before = make_before_kpi()
    after = make_after_kpi()
    after.actor_utilization = {"ai_agent": 0.4}

    diff = compare_workflows(before, after)
    report = generate_report(diff)

    assert "No material risks identified" in report


def test_report_recommends_proceeding_when_redesign_clearly_wins():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    report = generate_report(diff)

    assert "Recommend proceeding" in report


def test_report_recommends_further_iteration_when_cost_does_not_improve():
    before = make_before_kpi()
    after = make_after_kpi()
    after.total_cost = 20000.0

    diff = compare_workflows(before, after)
    report = generate_report(diff)

    assert "Recommend further redesign iteration" in report


def test_report_includes_payback_when_implementation_cost_given():
    diff = compare_workflows(make_before_kpi(), make_after_kpi(), implementation_cost=1000.0)

    report = generate_report(diff)

    assert "payback" in report.lower()
