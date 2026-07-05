from b2b_workflow_simulator.ai_adoption import (
    FULL_DEPLOYMENT,
    NOT_RECOMMENDED,
    PHASED_ROLLOUT,
    PILOT,
    assess_ai_adoption,
    generate_ai_adoption_report,
)
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.policy import PolicyEvaluation, PolicyViolation
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow


def build_all_human_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Manual", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="clerk", is_terminal=True))
    return workflow


def build_ai_workflow(
    error_rate: float = 0.0, escalation_rate: float = 0.0, with_human_fallback: bool = True
) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="AI Flow", entry_node_id="a")
    workflow.add_actor(
        AIAgentActor(
            actor_id="agent", name="Agent", error_rate=error_rate, escalation_rate=escalation_rate
        )
    )
    if with_human_fallback:
        workflow.add_actor(HumanActor(actor_id="reviewer", name="Reviewer"))
        workflow.add_node(Node(node_id="a", name="A", actor_id="agent"))
        workflow.add_node(Node(node_id="b", name="B", actor_id="reviewer", is_terminal=True))
        workflow.add_edge(Edge("a", "b", probability=1.0))
    else:
        workflow.add_node(Node(node_id="a", name="A", actor_id="agent", is_terminal=True))
    return workflow


def build_kpi(
    total_cases: int = 10,
    completed_cases: int = 10,
    failed_cases: int = 0,
    node_visit_counts: dict | None = None,
    multi_resource_task_count: int = 0,
) -> KPIResult:
    return KPIResult(
        workflow_name="wf",
        total_cases=total_cases,
        completed_cases=completed_cases,
        failed_cases=failed_cases,
        node_visit_counts=node_visit_counts or {},
        multi_resource_task_count=multi_resource_task_count,
    )


def test_all_human_workflow_has_zero_ai_maturity_and_full_governance():
    workflow = build_all_human_workflow()
    kpi = build_kpi()

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.ai_maturity == 0.0
    assert assessment.governance_score == 100.0
    assert assessment.explainability_score == 100.0


def test_all_human_workflow_has_full_human_dependency():
    workflow = build_all_human_workflow()
    kpi = build_kpi(node_visit_counts={"a": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.human_dependency == 100.0


def test_reliable_ai_with_fallback_scores_well_across_dimensions():
    workflow = build_ai_workflow(error_rate=0.01, escalation_rate=0.02, with_human_fallback=True)
    kpi = build_kpi(node_visit_counts={"a": 10, "b": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.ai_maturity > 90.0
    assert assessment.governance_score == 100.0
    assert assessment.explainability_score > 90.0


def test_ai_without_human_fallback_has_reduced_governance():
    workflow = build_ai_workflow(error_rate=0.01, escalation_rate=0.02, with_human_fallback=False)
    kpi = build_kpi(node_visit_counts={"a": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.governance_score == 0.0
    assert "human fallback" in assessment.reasoning[3]


def test_unreliable_ai_has_low_maturity_and_explainability():
    workflow = build_ai_workflow(error_rate=0.4, escalation_rate=0.4, with_human_fallback=True)
    kpi = build_kpi(node_visit_counts={"a": 10, "b": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.ai_maturity < 50.0
    assert assessment.explainability_score < 70.0


def test_policy_evaluation_overrides_structural_governance_score():
    workflow = build_ai_workflow(error_rate=0.01, escalation_rate=0.01, with_human_fallback=False)
    kpi = build_kpi(node_visit_counts={"a": 10})
    evaluation = PolicyEvaluation(
        workflow_name="wf",
        policies_checked=1,
        violations=[
            PolicyViolation(
                policy_name="p",
                policy_kind="mandatory_human_review",
                node_id="a",
                severity="error",
                description="AI node lacks mandatory human review",
            )
        ],
    )

    assessment = assess_ai_adoption(workflow, kpi, policy_evaluation=evaluation)

    assert assessment.governance_score == 85.0
    assert "policy violation" in assessment.reasoning[3]


def test_low_governance_caps_recommendation_at_pilot():
    workflow = build_ai_workflow(error_rate=0.01, escalation_rate=0.01, with_human_fallback=False)
    kpi = build_kpi(node_visit_counts={"a": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.governance_score == 0.0
    assert assessment.recommendation == PILOT


def test_fully_manual_process_yields_moderate_or_pilot_recommendation():
    workflow = build_all_human_workflow()
    kpi = build_kpi(node_visit_counts={"a": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.recommendation in {PILOT, PHASED_ROLLOUT, NOT_RECOMMENDED}


def test_mature_well_governed_ai_workflow_recommends_full_deployment():
    workflow = build_ai_workflow(error_rate=0.0, escalation_rate=0.0, with_human_fallback=True)
    kpi = build_kpi(total_cases=10, completed_cases=10, node_visit_counts={"a": 10, "b": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    assert assessment.recommendation == FULL_DEPLOYMENT


def test_high_failure_rate_reduces_automation_readiness():
    workflow = build_all_human_workflow()
    stable_kpi = build_kpi(total_cases=10, completed_cases=10, failed_cases=0)
    unstable_kpi = build_kpi(total_cases=10, completed_cases=4, failed_cases=6)

    stable_assessment = assess_ai_adoption(workflow, stable_kpi)
    unstable_assessment = assess_ai_adoption(workflow, unstable_kpi)

    assert unstable_assessment.automation_readiness < stable_assessment.automation_readiness


def test_multi_resource_tasks_increase_rollout_complexity():
    workflow = build_all_human_workflow()
    simple_kpi = build_kpi(multi_resource_task_count=0)
    coordinated_kpi = build_kpi(multi_resource_task_count=10)

    simple_assessment = assess_ai_adoption(workflow, simple_kpi)
    coordinated_assessment = assess_ai_adoption(workflow, coordinated_kpi)

    assert coordinated_assessment.rollout_complexity > simple_assessment.rollout_complexity


def test_readiness_index_is_average_of_normalized_components():
    workflow = build_all_human_workflow()
    kpi = build_kpi(node_visit_counts={"a": 10})

    assessment = assess_ai_adoption(workflow, kpi)

    expected = (
        assessment.automation_readiness
        + assessment.automation_readiness
        + assessment.governance_score
        + assessment.explainability_score
        + (100.0 - assessment.human_dependency)
        + (100.0 - assessment.rollout_complexity)
    ) / 6.0
    assert assessment.readiness_index == expected


def test_generate_ai_adoption_report_includes_all_scores_and_recommendation():
    workflow = build_ai_workflow(error_rate=0.01, escalation_rate=0.01, with_human_fallback=True)
    kpi = build_kpi(node_visit_counts={"a": 10, "b": 10})

    assessment = assess_ai_adoption(workflow, kpi)
    report = generate_ai_adoption_report(assessment)

    assert "AI Flow" in report
    assert "Readiness index" in report
    assert "Recommendation: Full deployment" in report
    assert "Automation readiness" in report
    assert "Reasoning:" in report
