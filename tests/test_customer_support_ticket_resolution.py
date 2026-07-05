from b2b_workflow_simulator.examples.customer_support_ticket_resolution import (
    build_after_workflow,
    build_before_workflow,
)
from b2b_workflow_simulator.simulation import SimulationRunner

EXPECTED_EXCEPTION_NODES = {
    "exception_wrong_classification",
    "exception_missing_customer_context",
    "exception_low_confidence",
    "exception_delayed_escalation",
}


def test_before_workflow_is_valid():
    build_before_workflow().validate()


def test_after_workflow_is_valid():
    build_after_workflow().validate()


def test_before_and_after_share_the_same_node_ids():
    before_nodes = set(build_before_workflow().nodes)
    after_nodes = set(build_after_workflow().nodes)

    assert before_nodes == after_nodes


def test_before_workflow_includes_all_realistic_exception_paths():
    workflow = build_before_workflow()

    assert EXPECTED_EXCEPTION_NODES.issubset(workflow.nodes)
    for node_id in EXPECTED_EXCEPTION_NODES:
        assert workflow.get_node(node_id).is_terminal


def test_before_workflow_uses_a_single_support_agent_for_the_happy_path():
    workflow = build_before_workflow()

    for node_id in ("ticket_intake", "triage", "response_drafting", "follow_up"):
        actor_id = workflow.get_node(node_id).actor_id
        assert workflow.get_actor(actor_id).kind == "human"
        assert actor_id == "support_agent"


def test_after_workflow_uses_ai_agents_for_triage_and_response_drafting():
    workflow = build_after_workflow()

    for node_id in ("ticket_intake", "triage"):
        assert workflow.get_actor(workflow.get_node(node_id).actor_id).kind == "ai_agent"
    for node_id in ("response_drafting", "follow_up"):
        assert workflow.get_actor(workflow.get_node(node_id).actor_id).kind == "ai_agent"


def test_after_workflow_routes_complex_cases_to_a_support_reviewer():
    workflow = build_after_workflow()

    reviewer_nodes = {
        "exception_wrong_classification",
        "exception_missing_customer_context",
        "exception_low_confidence",
    }
    for node_id in reviewer_nodes:
        actor_id = workflow.get_node(node_id).actor_id
        assert workflow.get_actor(actor_id).kind == "human"
        assert actor_id == "support_reviewer"


def test_after_workflow_reserves_specialist_for_escalations_only():
    workflow = build_after_workflow()

    for node_id in ("escalation", "exception_delayed_escalation"):
        actor_id = workflow.get_node(node_id).actor_id
        assert workflow.get_actor(actor_id).kind == "human"
        assert actor_id == "specialist"


def test_after_workflow_reduces_wrong_classification_and_escalation_probability():
    before = build_before_workflow()
    after = build_after_workflow()

    def edge_probability(workflow, source, target):
        return next(
            edge.probability for edge in workflow.outgoing_edges(source) if edge.target == target
        )

    assert edge_probability(after, "triage", "exception_wrong_classification") < edge_probability(
        before, "triage", "exception_wrong_classification"
    )
    assert edge_probability(after, "triage", "escalation") < edge_probability(
        before, "triage", "escalation"
    )


def test_after_workflow_is_faster_and_cheaper_than_before():
    before = SimulationRunner(seed=13).run(build_before_workflow(), 400)
    after = SimulationRunner(seed=13).run(build_after_workflow(), 400)

    assert after.kpi.total_cost < before.kpi.total_cost
    assert after.kpi.avg_cycle_time_minutes < before.kpi.avg_cycle_time_minutes


def test_after_workflow_introduces_measurable_escalations():
    after = SimulationRunner(seed=13).run(build_after_workflow(), 500)

    assert after.kpi.total_escalations > 0
