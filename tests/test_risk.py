from b2b_workflow_simulator.compliance import ComplianceReport, ComplianceViolation
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.policy import PolicyEvaluation, PolicyViolation
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.primitives.worker import Worker
from b2b_workflow_simulator.risk import (
    AI_FAILURE,
    CATEGORIES,
    COMPLIANCE,
    OPERATIONAL,
    PROCESS_COMPLEXITY,
    SINGLE_POINT_OF_FAILURE,
    STAFFING,
    compute_risk,
    generate_risk_report,
)
from b2b_workflow_simulator.workflow import Workflow


def build_linear_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Linear", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="rep"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="rep", is_terminal=True))
    workflow.add_edge(Edge("a", "b", probability=1.0))
    return workflow


def build_spof_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Bottleneck", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="sole_reviewer", name="Sole Reviewer"))
    for node_id in ["a", "b", "c"]:
        workflow.add_node(
            Node(
                node_id=node_id,
                name=node_id,
                actor_id="sole_reviewer",
                is_terminal=(node_id == "c"),
            )
        )
    workflow.add_edge(Edge("a", "b", probability=1.0))
    workflow.add_edge(Edge("b", "c", probability=1.0))
    return workflow


def build_ai_workflow(error_rate: float = 0.2, escalation_rate: float = 0.1) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="AI Flow", entry_node_id="a")
    workflow.add_actor(
        AIAgentActor(
            actor_id="agent",
            name="Agent",
            error_rate=error_rate,
            escalation_rate=escalation_rate,
        )
    )
    workflow.add_node(Node(node_id="a", name="A", actor_id="agent", is_terminal=True))
    return workflow


def build_pool_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Pooled", entry_node_id="a")
    pool = ActorPool(
        actor_id="team",
        name="Team",
        workers=[Worker(worker_id="w1", name="Worker One")],
    )
    workflow.add_actor(pool)
    workflow.add_node(Node(node_id="a", name="A", actor_id="team", is_terminal=True))
    return workflow


def build_cyclic_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Retry Loop", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="rep"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="rep"))
    workflow.add_node(Node(node_id="c", name="C", actor_id="rep", is_terminal=True))
    workflow.add_edge(Edge("a", "b", probability=1.0))
    workflow.add_edge(Edge("b", "a", probability=0.5))
    workflow.add_edge(Edge("b", "c", probability=0.5))
    return workflow


def test_compute_risk_returns_all_categories():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    assert set(assessment.category_scores) == set(CATEGORIES)


def test_operational_risk_reflects_failure_rate():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf", total_cases=10, completed_cases=6, failed_cases=4)

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[OPERATIONAL] > 0
    assert any(f.category == OPERATIONAL for f in assessment.factors)


def test_zero_kpi_and_simple_workflow_has_low_overall_risk():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf", total_cases=10, completed_cases=10)

    assessment = compute_risk(workflow, kpi)

    assert assessment.overall_score < 10.0


def test_single_point_of_failure_detected_for_shared_actor():
    workflow = build_spof_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[SINGLE_POINT_OF_FAILURE] > 0
    factor = assessment.factors_for(SINGLE_POINT_OF_FAILURE)[0]
    assert "sole_reviewer" in factor.description


def test_actor_pool_is_not_flagged_as_single_point_of_failure():
    workflow = build_pool_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[SINGLE_POINT_OF_FAILURE] == 0
    assert not assessment.factors_for(SINGLE_POINT_OF_FAILURE)


def test_ai_failure_risk_reflects_error_and_escalation_rate():
    workflow = build_ai_workflow(error_rate=0.3, escalation_rate=0.2)
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[AI_FAILURE] > 0
    descriptions = [f.description for f in assessment.factors_for(AI_FAILURE)]
    assert any("error rate" in d for d in descriptions)
    assert any("escalates" in d for d in descriptions)
    assert any("no reachable human fallback" in d for d in descriptions)


def test_ai_failure_risk_is_zero_for_reliable_agent_with_no_escalation():
    workflow = build_ai_workflow(error_rate=0.0, escalation_rate=0.0)
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    descriptions = [f.description for f in assessment.factors_for(AI_FAILURE)]
    assert not any("error rate" in d for d in descriptions)
    assert not any("escalates" in d for d in descriptions)
    assert any("no reachable human fallback" in d for d in descriptions)


def test_staffing_risk_flags_overloaded_actor():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf", actor_utilization={"rep": 0.97})

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[STAFFING] > 0


def test_staffing_risk_flags_overloaded_pool():
    workflow = build_pool_workflow()
    kpi = KPIResult(workflow_name="wf", pool_utilization={"team": 0.95})

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[STAFFING] > 0


def test_staffing_risk_is_zero_when_well_within_capacity():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf", actor_utilization={"rep": 0.4})

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[STAFFING] == 0


def test_process_complexity_flags_retry_loops():
    workflow = build_cyclic_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[PROCESS_COMPLEXITY] > 0
    assert any(
        "retry/rework loop" in f.description for f in assessment.factors_for(PROCESS_COMPLEXITY)
    )


def test_process_complexity_is_zero_for_small_linear_workflow():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[PROCESS_COMPLEXITY] == 0


def test_compliance_risk_uses_policy_evaluation_when_supplied():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf")
    evaluation = PolicyEvaluation(
        workflow_name="Linear",
        policies_checked=1,
        violations=[
            PolicyViolation(
                policy_name="p",
                policy_kind="approval",
                node_id="a",
                severity="error",
                description="missing approval",
            )
        ],
    )

    assessment = compute_risk(workflow, kpi, policy_evaluation=evaluation)

    assert assessment.category_scores[COMPLIANCE] > 0


def test_compliance_risk_uses_compliance_report_when_supplied():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf")
    report = ComplianceReport(
        workflow_name="Linear",
        requirements_checked=1,
        violations=[
            ComplianceViolation(
                requirement_name="gdpr",
                requirement_kind="gdpr_approval",
                node_id="a",
                description="missing consent gate",
            )
        ],
    )

    assessment = compute_risk(workflow, kpi, compliance_report=report)

    assert assessment.category_scores[COMPLIANCE] > 0


def test_compliance_risk_is_zero_without_policy_or_compliance_input():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)

    assert assessment.category_scores[COMPLIANCE] == 0


def test_overall_score_is_average_of_category_scores():
    workflow = build_linear_workflow()
    kpi = KPIResult(workflow_name="wf", total_cases=10, completed_cases=5, failed_cases=5)

    assessment = compute_risk(workflow, kpi)

    expected = sum(assessment.category_scores.values()) / len(assessment.category_scores)
    assert assessment.overall_score == expected


def test_top_factors_returns_highest_weighted_first():
    workflow = build_spof_workflow()
    kpi = KPIResult(workflow_name="wf", total_cases=10, completed_cases=5, failed_cases=5)

    assessment = compute_risk(workflow, kpi)
    top = assessment.top_factors(top_n=3)

    weights = [f.weight for f in top]
    assert weights == sorted(weights, reverse=True)


def test_generate_risk_report_includes_overall_and_category_scores():
    workflow = build_spof_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)
    report = generate_risk_report(assessment)

    assert "Bottleneck" in report
    assert "Overall risk score" in report
    assert "Single Point of Failure" in report
    assert "sole_reviewer" in report


def test_generate_risk_report_handles_no_factors():
    workflow = build_pool_workflow()
    kpi = KPIResult(workflow_name="wf")

    assessment = compute_risk(workflow, kpi)
    report = generate_risk_report(assessment)

    assert "No risk factors identified." in report
