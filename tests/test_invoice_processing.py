from b2b_workflow_simulator.examples.invoice_processing import (
    build_after_workflow,
    build_before_workflow,
)
from b2b_workflow_simulator.simulation import SimulationRunner

EXPECTED_EXCEPTION_NODES = {
    "exception_missing_po",
    "exception_mismatched_amount",
    "exception_vendor_data_issue",
    "exception_approval_delay",
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


def test_after_workflow_uses_ai_agents_for_straight_through_processing():
    workflow = build_after_workflow()

    for node_id in ("invoice_intake", "validation", "approval", "erp_entry"):
        assert workflow.get_actor(workflow.get_node(node_id).actor_id).kind == "ai_agent"


def test_after_workflow_routes_every_exception_to_a_human_specialist():
    workflow = build_after_workflow()

    for node_id in EXPECTED_EXCEPTION_NODES:
        actor_id = workflow.get_node(node_id).actor_id
        assert workflow.get_actor(actor_id).kind == "human"
        assert actor_id == "ap_specialist"


def test_after_workflow_reduces_approval_delay_probability():
    before = build_before_workflow()
    after = build_after_workflow()

    before_delay_edge = next(
        edge
        for edge in before.outgoing_edges("approval")
        if edge.target == "exception_approval_delay"
    )
    after_delay_edge = next(
        edge
        for edge in after.outgoing_edges("approval")
        if edge.target == "exception_approval_delay"
    )

    assert after_delay_edge.probability < before_delay_edge.probability


def test_after_workflow_is_faster_and_cheaper_than_before():
    before = SimulationRunner(seed=11).run(build_before_workflow(), 400)
    after = SimulationRunner(seed=11).run(build_after_workflow(), 400)

    assert after.kpi.total_cost < before.kpi.total_cost
    assert after.kpi.avg_cycle_time_minutes < before.kpi.avg_cycle_time_minutes


def test_after_workflow_introduces_measurable_escalations():
    after = SimulationRunner(seed=11).run(build_after_workflow(), 500)

    assert after.kpi.total_escalations > 0
