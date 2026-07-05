from b2b_workflow_simulator.examples.sales_lead_qualification import (
    build_after_workflow,
    build_before_workflow,
)
from b2b_workflow_simulator.simulation import SimulationRunner


def test_before_workflow_is_valid():
    workflow = build_before_workflow()

    workflow.validate()


def test_after_workflow_is_valid():
    workflow = build_after_workflow()

    workflow.validate()


def test_before_and_after_share_the_same_node_ids():
    before_nodes = set(build_before_workflow().nodes)
    after_nodes = set(build_after_workflow().nodes)

    assert before_nodes == after_nodes


def test_after_workflow_uses_ai_agents_for_intake_and_research():
    workflow = build_after_workflow()

    assert workflow.get_node("lead_intake").actor_id == "intake_agent"
    assert workflow.get_node("initial_research").actor_id == "research_agent"
    assert workflow.get_actor("intake_agent").kind == "ai_agent"
    assert workflow.get_actor("research_agent").kind == "ai_agent"


def test_after_workflow_keeps_discovery_call_human():
    workflow = build_after_workflow()

    assert workflow.get_node("discovery_call").actor_id == "ae"
    assert workflow.get_actor("ae").kind == "human"


def test_after_workflow_is_faster_and_cheaper_than_before():
    before = SimulationRunner(seed=7).run(build_before_workflow(), 500)
    after = SimulationRunner(seed=7).run(build_after_workflow(), 500)

    assert after.kpi.total_cost < before.kpi.total_cost
    assert after.kpi.avg_cycle_time_minutes < before.kpi.avg_cycle_time_minutes
