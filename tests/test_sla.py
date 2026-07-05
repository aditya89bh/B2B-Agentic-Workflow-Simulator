import pytest

from b2b_workflow_simulator.primitives.event import Event, EventType
from b2b_workflow_simulator.simulation import SimulationResult
from b2b_workflow_simulator.sla import (
    CompletionSLA,
    EscalationSLA,
    ResponseSLA,
    evaluate_sla,
    generate_sla_report,
)


def build_result(events: list[Event]) -> SimulationResult:
    return SimulationResult(workflow_name="Test Workflow", events=events)


def test_completion_sla_passes_within_deadline():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 50.0, "case-1"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0)

    report = evaluate_sla(result, [rule])

    assert report.breach_count == 0
    assert report.attainment_rate == 1.0


def test_completion_sla_flags_breach_with_correct_minutes():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-1"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0)

    report = evaluate_sla(result, [rule])

    assert report.breach_count == 1
    assert report.breaches[0].breach_minutes == 30.0
    assert report.breaches[0].actual_minutes == 90.0


def test_completion_sla_treats_failed_cases_as_terminal():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_FAILED, 120.0, "case-1"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0)

    report = evaluate_sla(result, [rule])

    assert report.breach_count == 1


def test_completion_sla_estimates_penalty_when_configured():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-1"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0, penalty_per_minute=5.0)

    report = evaluate_sla(result, [rule])

    assert report.breaches[0].penalty == 150.0
    assert report.total_penalty == 150.0


def test_completion_sla_penalty_is_none_when_not_configured():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-1"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0)

    report = evaluate_sla(result, [rule])

    assert report.breaches[0].penalty is None
    assert report.total_penalty == 0.0


def test_response_sla_flags_slow_first_response():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.TASK_STARTED, 45.0, "case-1", "triage", "rep"),
    ]
    result = build_result(events)
    rule = ResponseSLA(name="triage-response", node_id="triage", deadline_minutes=30.0)

    report = evaluate_sla(result, [rule])

    assert report.breach_count == 1
    assert report.breaches[0].node_id == "triage"


def test_response_sla_is_not_applicable_when_node_never_visited():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.TASK_STARTED, 10.0, "case-1", "other_node", "rep"),
    ]
    result = build_result(events)
    rule = ResponseSLA(name="triage-response", node_id="triage", deadline_minutes=30.0)

    report = evaluate_sla(result, [rule])

    assert report.evaluations == 0
    assert report.breach_count == 0


def test_escalation_sla_flags_slow_pickup():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.TASK_ESCALATED, 20.0, "case-1", "ai_review", "agent"),
        Event(EventType.TASK_STARTED, 90.0, "case-1", "human_review", "rep"),
    ]
    result = build_result(events)
    rule = EscalationSLA(name="escalation-pickup", node_id="ai_review", deadline_minutes=30.0)

    report = evaluate_sla(result, [rule])

    assert report.breach_count == 1
    assert report.breaches[0].breach_minutes == 40.0


def test_escalation_sla_passes_when_resolved_in_time():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.TASK_ESCALATED, 20.0, "case-1", "ai_review", "agent"),
        Event(EventType.TASK_STARTED, 30.0, "case-1", "human_review", "rep"),
    ]
    result = build_result(events)
    rule = EscalationSLA(name="escalation-pickup", node_id="ai_review", deadline_minutes=30.0)

    report = evaluate_sla(result, [rule])

    assert report.breach_count == 0


def test_escalation_sla_uses_case_terminal_event_as_resolution_when_no_next_task():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.TASK_ESCALATED, 20.0, "case-1", "ai_review", "agent"),
        Event(EventType.CASE_COMPLETED, 100.0, "case-1"),
    ]
    result = build_result(events)
    rule = EscalationSLA(name="escalation-pickup", node_id="ai_review", deadline_minutes=30.0)

    report = evaluate_sla(result, [rule])

    assert report.breach_count == 1
    assert report.breaches[0].actual_minutes == 80.0


def test_escalation_sla_is_not_applicable_when_no_escalation_occurs():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 30.0, "case-1"),
    ]
    result = build_result(events)
    rule = EscalationSLA(name="escalation-pickup", node_id="ai_review", deadline_minutes=30.0)

    report = evaluate_sla(result, [rule])

    assert report.evaluations == 0


def test_attainment_rate_across_multiple_cases():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 30.0, "case-1"),
        Event(EventType.CASE_STARTED, 0.0, "case-2"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-2"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0)

    report = evaluate_sla(result, [rule])

    assert report.cases_evaluated == 2
    assert report.evaluations == 2
    assert report.breach_count == 1
    assert report.attainment_rate == 0.5


def test_average_breach_minutes_across_multiple_breaches():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 80.0, "case-1"),
        Event(EventType.CASE_STARTED, 0.0, "case-2"),
        Event(EventType.CASE_COMPLETED, 100.0, "case-2"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0)

    report = evaluate_sla(result, [rule])

    assert report.average_breach_minutes == pytest.approx((20.0 + 40.0) / 2)


def test_breach_causes_counts_by_rule_name():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-1"),
        Event(EventType.TASK_STARTED, 45.0, "case-1", "triage", "rep"),
    ]
    result = build_result(events)
    rules = [
        CompletionSLA(name="completion-sla", deadline_minutes=60.0),
        ResponseSLA(name="response-sla", node_id="triage", deadline_minutes=30.0),
    ]

    report = evaluate_sla(result, rules)

    assert report.breach_causes() == {"completion-sla": 1, "response-sla": 1}


def test_evaluate_sla_with_no_rules_has_full_attainment():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-1"),
    ]
    result = build_result(events)

    report = evaluate_sla(result, [])

    assert report.attainment_rate == 1.0
    assert report.breach_count == 0
    assert report.rules_checked == 0


def test_generate_sla_report_includes_attainment_and_penalty():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-1"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0, penalty_per_minute=5.0)

    report_text = generate_sla_report(evaluate_sla(result, [rule]))

    assert "SLA PERFORMANCE ANALYSIS" in report_text
    assert "Attainment rate: 0.0%" in report_text
    assert "Estimated financial penalty: $150.00" in report_text
    assert "fast-resolution: 1 breach(es)" in report_text


def test_generate_sla_report_for_fully_attained_sla():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 30.0, "case-1"),
    ]
    result = build_result(events)
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0)

    report_text = generate_sla_report(evaluate_sla(result, [rule]))

    assert "Attainment rate: 100.0%" in report_text
    assert "Every applicable SLA check was met" in report_text


def test_generate_sla_report_for_no_rules():
    result = build_result([Event(EventType.CASE_STARTED, 0.0, "case-1")])

    report_text = generate_sla_report(evaluate_sla(result, []))

    assert "No SLA rules were attached" in report_text
