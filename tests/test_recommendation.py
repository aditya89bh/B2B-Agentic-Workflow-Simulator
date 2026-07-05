from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.recommendation import (
    AUTOMATE_TASK,
    INCREASE_STAFFING,
    INTRODUCE_APPROVAL_GATE,
    INTRODUCE_MEMORY_AGENT,
    KEEP_HUMAN_REVIEW,
    MERGE_ACTIVITIES,
    REDESIGN_ESCALATION,
    REDUCE_STAFFING,
    REMOVE_APPROVAL,
    SPLIT_ACTIVITIES,
    generate_recommendation_report,
    generate_recommendations,
)
from b2b_workflow_simulator.risk import compute_risk
from b2b_workflow_simulator.workflow import Workflow


def build_automation_candidate_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Simple", entry_node_id="intake")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_node(Node(node_id="intake", name="Intake", actor_id="clerk", is_terminal=True))
    return workflow


def build_kpi(
    total_cases: int = 10,
    node_visit_counts: dict | None = None,
    node_total_duration_minutes: dict | None = None,
    node_failure_counts: dict | None = None,
    actor_utilization: dict | None = None,
    pool_utilization: dict | None = None,
    total_escalations: int = 0,
) -> KPIResult:
    return KPIResult(
        workflow_name="wf",
        total_cases=total_cases,
        completed_cases=total_cases,
        node_visit_counts=node_visit_counts or {},
        node_total_duration_minutes=node_total_duration_minutes or {},
        node_failure_counts=node_failure_counts or {},
        actor_utilization=actor_utilization or {},
        pool_utilization=pool_utilization or {},
        total_escalations=total_escalations,
    )


def test_recommends_automation_for_high_frequency_human_task():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(total_cases=10, node_visit_counts={"intake": 10})

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(AUTOMATE_TASK)
    assert result.of_kind(AUTOMATE_TASK)[0].node_id == "intake"


def test_does_not_recommend_automation_for_low_frequency_task():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(total_cases=10, node_visit_counts={"intake": 2})

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(AUTOMATE_TASK)


def test_does_not_recommend_automation_for_approval_named_node():
    workflow = Workflow(workflow_id="wf", name="Approval Flow", entry_node_id="approval")
    workflow.add_actor(HumanActor(actor_id="controller", name="Controller"))
    workflow.add_node(
        Node(node_id="approval", name="Approval", actor_id="controller", is_terminal=True)
    )
    kpi = build_kpi(total_cases=10, node_visit_counts={"approval": 10})

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(AUTOMATE_TASK)


def build_unreliable_ai_workflow(error_rate=0.2, escalation_rate=0.2) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="AI Flow", entry_node_id="a")
    workflow.add_actor(
        AIAgentActor(
            actor_id="agent", name="Agent", error_rate=error_rate, escalation_rate=escalation_rate
        )
    )
    workflow.add_node(Node(node_id="a", name="A", actor_id="agent", is_terminal=True))
    return workflow


def test_recommends_keep_human_review_for_unreliable_agent():
    workflow = build_unreliable_ai_workflow(error_rate=0.2, escalation_rate=0.2)
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(KEEP_HUMAN_REVIEW)


def test_does_not_recommend_keep_human_review_for_reliable_agent():
    workflow = build_unreliable_ai_workflow(error_rate=0.01, escalation_rate=0.01)
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(KEEP_HUMAN_REVIEW)


def test_keep_human_review_includes_risk_assessment_note_when_supplied():
    workflow = build_unreliable_ai_workflow(error_rate=0.2, escalation_rate=0.2)
    kpi = build_kpi()
    risk = compute_risk(workflow, kpi)

    result = generate_recommendations(workflow, kpi, risk_assessment=risk)

    reasoning = result.of_kind(KEEP_HUMAN_REVIEW)[0].reasoning
    assert "Flagged by risk assessment" in reasoning


def test_recommends_increase_staffing_for_overloaded_actor():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(actor_utilization={"clerk": 0.95})

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(INCREASE_STAFFING)


def test_recommends_reduce_staffing_for_underutilized_actor():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(actor_utilization={"clerk": 0.05})

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(REDUCE_STAFFING)


def test_no_staffing_recommendation_within_healthy_utilization_band():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(actor_utilization={"clerk": 0.5})

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(INCREASE_STAFFING)
    assert not result.of_kind(REDUCE_STAFFING)


def test_recommends_increase_staffing_for_overloaded_pool():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(pool_utilization={"team": 0.93})

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(INCREASE_STAFFING)


def build_merge_candidate_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Two Steps", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="clerk"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="clerk", is_terminal=True))
    workflow.add_edge(Edge("a", "b", probability=1.0))
    return workflow


def test_recommends_merge_for_sequential_same_actor_steps():
    workflow = build_merge_candidate_workflow()
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(MERGE_ACTIVITIES)


def test_does_not_recommend_merge_across_different_actors():
    workflow = Workflow(workflow_id="wf", name="Two Actors", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_actor(HumanActor(actor_id="controller", name="Controller"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="clerk"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="controller", is_terminal=True))
    workflow.add_edge(Edge("a", "b", probability=1.0))
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(MERGE_ACTIVITIES)


def build_three_step_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Three Steps", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_actor(HumanActor(actor_id="controller", name="Controller"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="clerk"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="controller"))
    workflow.add_node(Node(node_id="c", name="C", actor_id="clerk", is_terminal=True))
    workflow.add_edge(Edge("a", "b", probability=1.0))
    workflow.add_edge(Edge("b", "c", probability=1.0))
    return workflow


def test_recommends_split_for_unusually_long_task():
    workflow = build_three_step_workflow()
    kpi = build_kpi(
        node_visit_counts={"a": 10, "b": 10, "c": 10},
        node_total_duration_minutes={"a": 50.0, "b": 500.0, "c": 50.0},
    )

    result = generate_recommendations(workflow, kpi)

    split = result.of_kind(SPLIT_ACTIVITIES)
    assert split
    assert split[0].node_id == "b"


def test_no_split_recommendation_when_durations_are_similar():
    workflow = build_merge_candidate_workflow()
    kpi = build_kpi(
        node_visit_counts={"a": 10, "b": 10},
        node_total_duration_minutes={"a": 100.0, "b": 110.0},
    )

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(SPLIT_ACTIVITIES)


def test_recommends_memory_agent_for_high_escalation_low_error_agent():
    workflow = build_unreliable_ai_workflow(error_rate=0.01, escalation_rate=0.25)
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(INTRODUCE_MEMORY_AGENT)


def test_does_not_recommend_memory_agent_when_error_rate_also_high():
    workflow = build_unreliable_ai_workflow(error_rate=0.2, escalation_rate=0.25)
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(INTRODUCE_MEMORY_AGENT)


def build_sensitive_workflow(with_approval: bool) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Payment Flow", entry_node_id="intake")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_node(Node(node_id="intake", name="Intake", actor_id="clerk"))
    if with_approval:
        workflow.add_node(Node(node_id="approval", name="Approval", actor_id="clerk"))
        workflow.add_node(
            Node(node_id="payment", name="Payment", actor_id="clerk", is_terminal=True)
        )
        workflow.add_edge(Edge("intake", "approval", probability=1.0))
        workflow.add_edge(Edge("approval", "payment", probability=1.0))
    else:
        workflow.add_node(
            Node(node_id="payment", name="Payment", actor_id="clerk", is_terminal=True)
        )
        workflow.add_edge(Edge("intake", "payment", probability=1.0))
    return workflow


def test_recommends_approval_gate_for_sensitive_node_with_no_upstream_approval():
    workflow = build_sensitive_workflow(with_approval=False)
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    gates = result.of_kind(INTRODUCE_APPROVAL_GATE)
    assert any(r.node_id == "payment" for r in gates)


def test_does_not_recommend_approval_gate_when_upstream_approval_exists():
    workflow = build_sensitive_workflow(with_approval=True)
    kpi = build_kpi()

    result = generate_recommendations(workflow, kpi)

    gates = result.of_kind(INTRODUCE_APPROVAL_GATE)
    assert not any(r.node_id == "payment" for r in gates)


def test_recommends_removing_approval_that_never_fails():
    workflow = build_sensitive_workflow(with_approval=True)
    kpi = build_kpi(
        node_visit_counts={"approval": 20},
        node_failure_counts={},
    )

    result = generate_recommendations(workflow, kpi)

    removals = result.of_kind(REMOVE_APPROVAL)
    assert any(r.node_id == "approval" for r in removals)


def test_does_not_recommend_removing_approval_that_sometimes_fails():
    workflow = build_sensitive_workflow(with_approval=True)
    kpi = build_kpi(
        node_visit_counts={"approval": 20},
        node_failure_counts={"approval": 3},
    )

    result = generate_recommendations(workflow, kpi)

    removals = result.of_kind(REMOVE_APPROVAL)
    assert not any(r.node_id == "approval" for r in removals)


def test_does_not_recommend_removing_approval_with_too_few_visits():
    workflow = build_sensitive_workflow(with_approval=True)
    kpi = build_kpi(node_visit_counts={"approval": 2})

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(REMOVE_APPROVAL)


def build_ai_retry_loop_workflow(escalation_rate: float = 0.3) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="AI Retry Loop", entry_node_id="a")
    workflow.add_actor(
        AIAgentActor(actor_id="agent", name="Agent", escalation_rate=escalation_rate)
    )
    workflow.add_node(Node(node_id="a", name="A", actor_id="agent"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="agent", is_terminal=True))
    workflow.add_edge(Edge("a", "b", probability=0.7))
    workflow.add_edge(Edge("b", "a", probability=0.3))
    return workflow


def test_recommends_escalation_redesign_for_ai_node_in_retry_loop():
    workflow = build_ai_retry_loop_workflow(escalation_rate=0.3)
    kpi = build_kpi(total_cases=10, total_escalations=3)

    result = generate_recommendations(workflow, kpi)

    assert result.of_kind(REDESIGN_ESCALATION)


def test_no_escalation_redesign_when_overall_escalation_rate_is_low():
    workflow = build_ai_retry_loop_workflow(escalation_rate=0.3)
    kpi = build_kpi(total_cases=100, total_escalations=1)

    result = generate_recommendations(workflow, kpi)

    assert not result.of_kind(REDESIGN_ESCALATION)


def test_recommendations_are_sorted_by_confidence_descending():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(
        total_cases=10,
        node_visit_counts={"intake": 10},
        actor_utilization={"clerk": 0.95},
    )

    result = generate_recommendations(workflow, kpi)
    confidences = [r.confidence for r in result.recommendations]
    rank = {"high": 2, "medium": 1, "low": 0}
    ranks = [rank[c] for c in confidences]

    assert ranks == sorted(ranks, reverse=True)


def test_recommendation_set_len_matches_recommendation_count():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(total_cases=10, node_visit_counts={"intake": 10})

    result = generate_recommendations(workflow, kpi)

    assert len(result) == len(result.recommendations)


def test_generate_recommendation_report_lists_all_recommendations():
    workflow = build_automation_candidate_workflow()
    kpi = build_kpi(total_cases=10, node_visit_counts={"intake": 10})

    result = generate_recommendations(workflow, kpi)
    report = generate_recommendation_report(result)

    assert "Simple" in report
    assert "Automate 'Intake'" in report
    assert "Reasoning:" in report
    assert "Affected KPIs:" in report
    assert "Expected benefit:" in report


def test_generate_recommendation_report_handles_no_recommendations():
    workflow = Workflow(workflow_id="wf", name="Quiet", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="clerk", is_terminal=True))
    kpi = build_kpi(total_cases=0)

    result = generate_recommendations(workflow, kpi)
    report = generate_recommendation_report(result)

    assert "No actionable recommendations" in report
