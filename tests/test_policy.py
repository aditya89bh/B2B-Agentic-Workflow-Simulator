import pytest

from b2b_workflow_simulator.policy import (
    ApprovalPolicy,
    BusinessHoursPolicy,
    EscalationPolicy,
    MandatoryHumanReviewPolicy,
    RetryPolicy,
    RoutingPolicy,
    SeparationOfDutiesPolicy,
    evaluate_policies,
    generate_policy_report,
)
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.primitives.shift import Shift
from b2b_workflow_simulator.primitives.worker import Worker
from b2b_workflow_simulator.workflow import Workflow


def build_invoice_workflow(with_approval: bool = True) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Invoice", entry_node_id="intake")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_actor(HumanActor(actor_id="controller", name="Controller"))
    workflow.add_actor(AIAgentActor(actor_id="ai_intake", name="AI Intake"))
    workflow.add_node(Node(node_id="intake", name="Intake", actor_id="clerk"))
    if with_approval:
        workflow.add_node(Node(node_id="approval", name="Approval", actor_id="controller"))
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


def test_approval_policy_passes_when_gate_precedes_target():
    workflow = build_invoice_workflow(with_approval=True)
    policy = ApprovalPolicy(
        name="controller-approval",
        target_node_id="payment",
        required_before_node_ids=("approval",),
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant
    assert evaluation.policies_checked == 1


def test_approval_policy_flags_missing_gate():
    workflow = build_invoice_workflow(with_approval=False)
    policy = ApprovalPolicy(
        name="controller-approval",
        target_node_id="payment",
        required_before_node_ids=("approval",),
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert not evaluation.is_compliant
    assert evaluation.violations[0].policy_kind == "approval"


def test_routing_policy_flags_disallowed_edge():
    workflow = build_invoice_workflow(with_approval=True)
    policy = RoutingPolicy(
        name="approval-routing", node_id="approval", allowed_next_node_ids=("intake",)
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.violation_count == 1
    assert evaluation.violations[0].node_id == "approval"


def test_routing_policy_passes_when_all_edges_allowed():
    workflow = build_invoice_workflow(with_approval=True)
    policy = RoutingPolicy(
        name="approval-routing", node_id="approval", allowed_next_node_ids=("payment",)
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_escalation_policy_passes_when_human_downstream():
    workflow = Workflow(workflow_id="wf", name="Escalation", entry_node_id="ai")
    workflow.add_actor(AIAgentActor(actor_id="agent", name="Agent"))
    workflow.add_actor(HumanActor(actor_id="human", name="Human"))
    workflow.add_node(Node(node_id="ai", name="AI", actor_id="agent"))
    workflow.add_node(
        Node(node_id="human_review", name="Review", actor_id="human", is_terminal=True)
    )
    workflow.add_edge(Edge("ai", "human_review", probability=1.0))
    policy = EscalationPolicy(name="ai-escalation", node_id="ai")

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_escalation_policy_flags_missing_human_path():
    workflow = Workflow(workflow_id="wf", name="Escalation", entry_node_id="ai")
    workflow.add_actor(AIAgentActor(actor_id="agent", name="Agent"))
    workflow.add_actor(AIAgentActor(actor_id="agent2", name="Agent 2"))
    workflow.add_node(Node(node_id="ai", name="AI", actor_id="agent"))
    workflow.add_node(Node(node_id="ai2", name="AI 2", actor_id="agent2", is_terminal=True))
    workflow.add_edge(Edge("ai", "ai2", probability=1.0))
    policy = EscalationPolicy(name="ai-escalation", node_id="ai")

    evaluation = evaluate_policies(workflow, [policy])

    assert not evaluation.is_compliant
    assert evaluation.violations[0].policy_kind == "escalation"


def test_escalation_policy_is_not_applicable_to_human_nodes():
    workflow = build_invoice_workflow(with_approval=True)
    policy = EscalationPolicy(name="not-applicable", node_id="intake")

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_retry_policy_flags_loop_with_no_escape():
    workflow = Workflow(workflow_id="wf", name="Loop", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="rep"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="rep"))
    workflow.add_edge(Edge("a", "b", probability=1.0))
    workflow.add_edge(Edge("b", "a", probability=1.0))
    policy = RetryPolicy(name="ping-pong", node_id="a", max_attempts=3)

    evaluation = evaluate_policies(workflow, [policy])

    assert not evaluation.is_compliant
    assert evaluation.violations[0].policy_kind == "retry"


def test_retry_policy_passes_when_loop_has_an_escape():
    workflow = Workflow(workflow_id="wf", name="Loop", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="rep"))
    workflow.add_node(Node(node_id="b", name="B", actor_id="rep"))
    workflow.add_node(Node(node_id="done", name="Done", actor_id="rep", is_terminal=True))
    workflow.add_edge(Edge("a", "b", probability=1.0))
    workflow.add_edge(Edge("b", "a", probability=0.5))
    workflow.add_edge(Edge("b", "done", probability=0.5))
    policy = RetryPolicy(name="ping-pong", node_id="a", max_attempts=3)

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_retry_policy_is_not_applicable_without_a_cycle():
    workflow = build_invoice_workflow(with_approval=True)
    policy = RetryPolicy(name="no-cycle", node_id="intake", max_attempts=3)

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_business_hours_policy_flags_shift_outside_allowed_window():
    workflow = Workflow(workflow_id="wf", name="Pooled", entry_node_id="handle")
    pool = ActorPool(
        actor_id="team",
        name="Team",
        workers=[
            Worker(
                worker_id="w1",
                name="Night Worker",
                shifts=[Shift(name="night", days=(0, 1, 2, 3, 4), start_hour=20.0, end_hour=23.0)],
            )
        ],
    )
    workflow.add_actor(pool)
    workflow.add_node(
        Node(node_id="handle", name="Handle", actor_id="team", is_terminal=True)
    )
    policy = BusinessHoursPolicy(
        name="business-hours", node_id="handle", allowed_start_hour=8.0, allowed_end_hour=18.0
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert not evaluation.is_compliant
    assert evaluation.violations[0].severity == "warning"


def test_business_hours_policy_passes_for_shift_within_window():
    workflow = Workflow(workflow_id="wf", name="Pooled", entry_node_id="handle")
    pool = ActorPool(
        actor_id="team",
        name="Team",
        workers=[
            Worker(
                worker_id="w1",
                name="Day Worker",
                shifts=[Shift(name="day", days=(0, 1, 2, 3, 4), start_hour=9.0, end_hour=17.0)],
            )
        ],
    )
    workflow.add_actor(pool)
    workflow.add_node(Node(node_id="handle", name="Handle", actor_id="team", is_terminal=True))
    policy = BusinessHoursPolicy(
        name="business-hours", node_id="handle", allowed_start_hour=8.0, allowed_end_hour=18.0
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_business_hours_policy_not_applicable_to_plain_actors():
    workflow = build_invoice_workflow(with_approval=True)
    policy = BusinessHoursPolicy(
        name="business-hours", node_id="intake", allowed_start_hour=8.0, allowed_end_hour=18.0
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_mandatory_human_review_policy_flags_ai_node():
    workflow = build_invoice_workflow(with_approval=True)
    workflow.add_node(
        Node(node_id="ai_step", name="AI Step", actor_id="ai_intake", is_terminal=True)
    )
    policy = MandatoryHumanReviewPolicy(name="human-review", node_id="ai_step")

    evaluation = evaluate_policies(workflow, [policy])

    assert not evaluation.is_compliant
    assert evaluation.violations[0].policy_kind == "mandatory_human_review"


def test_mandatory_human_review_policy_passes_for_human_node():
    workflow = build_invoice_workflow(with_approval=True)
    policy = MandatoryHumanReviewPolicy(name="human-review", node_id="intake")

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_separation_of_duties_policy_flags_same_actor():
    workflow = build_invoice_workflow(with_approval=True)
    policy = SeparationOfDutiesPolicy(
        name="sod", node_id_a="intake", node_id_b="payment"
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert not evaluation.is_compliant
    assert evaluation.violations[0].policy_kind == "separation_of_duties"


def test_separation_of_duties_policy_passes_for_different_actors():
    workflow = build_invoice_workflow(with_approval=True)
    policy = SeparationOfDutiesPolicy(
        name="sod", node_id_a="intake", node_id_b="approval"
    )

    evaluation = evaluate_policies(workflow, [policy])

    assert evaluation.is_compliant


def test_evaluation_counts_errors_and_warnings_separately():
    workflow = build_invoice_workflow(with_approval=False)
    policies = [
        ApprovalPolicy(
            name="controller-approval",
            target_node_id="payment",
            required_before_node_ids=("approval",),
        ),
        SeparationOfDutiesPolicy(name="sod", node_id_a="intake", node_id_b="payment"),
    ]

    evaluation = evaluate_policies(workflow, policies)

    assert evaluation.error_count == 2
    assert evaluation.warning_count == 0


def test_evaluate_policies_with_empty_list_is_always_compliant():
    workflow = build_invoice_workflow(with_approval=True)

    evaluation = evaluate_policies(workflow, [])

    assert evaluation.is_compliant
    assert evaluation.policies_checked == 0


def test_generate_policy_report_includes_workflow_name_and_summary():
    workflow = build_invoice_workflow(with_approval=False)
    policy = ApprovalPolicy(
        name="controller-approval",
        target_node_id="payment",
        required_before_node_ids=("approval",),
    )
    evaluation = evaluate_policies(workflow, [policy])

    report = generate_policy_report(evaluation)

    assert "POLICY COMPLIANCE ANALYSIS" in report
    assert "Invoice" in report
    assert "controller-approval" in report
    assert "1 violation(s) found" in report


def test_generate_policy_report_for_fully_compliant_workflow():
    workflow = build_invoice_workflow(with_approval=True)
    policy = ApprovalPolicy(
        name="controller-approval",
        target_node_id="payment",
        required_before_node_ids=("approval",),
    )
    evaluation = evaluate_policies(workflow, [policy])

    report = generate_policy_report(evaluation)

    assert "satisfies every attached policy" in report


def test_generate_policy_report_for_no_policies():
    workflow = build_invoice_workflow(with_approval=True)
    evaluation = evaluate_policies(workflow, [])

    report = generate_policy_report(evaluation)

    assert "No policies were attached" in report


@pytest.mark.parametrize(
    "policy",
    [
        ApprovalPolicy(name="a", target_node_id="x", required_before_node_ids=("y",)),
        RoutingPolicy(name="b", node_id="x", allowed_next_node_ids=("y",)),
        EscalationPolicy(name="c", node_id="x"),
        RetryPolicy(name="d", node_id="x", max_attempts=3),
        BusinessHoursPolicy(name="e", node_id="x", allowed_start_hour=8.0, allowed_end_hour=18.0),
        MandatoryHumanReviewPolicy(name="f", node_id="x"),
        SeparationOfDutiesPolicy(name="g", node_id_a="x", node_id_b="y"),
    ],
)
def test_policy_types_are_frozen_dataclasses(policy):
    with pytest.raises(AttributeError):
        policy.name = "changed"
