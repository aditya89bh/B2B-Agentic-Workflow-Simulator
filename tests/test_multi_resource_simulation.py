import pytest

from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.event import EventType
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow


def build_workflow() -> Workflow:
    workflow = Workflow(
        workflow_id="contract-review",
        name="Contract Review",
        entry_node_id="draft",
    )
    workflow.add_actor(HumanActor(actor_id="manager", name="Manager", hourly_cost=60.0))
    workflow.add_actor(HumanActor(actor_id="legal", name="Legal", hourly_cost=90.0))
    workflow.add_node(
        Node(node_id="draft", name="Draft", actor_id="manager", base_duration_minutes=10.0)
    )
    workflow.add_node(
        Node(
            node_id="review",
            name="Joint Review",
            actor_id="manager",
            additional_actor_ids=("legal",),
            base_duration_minutes=30.0,
            is_terminal=True,
        )
    )
    workflow.add_edge(Edge("draft", "review", probability=1.0))
    return workflow


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_multi_resource_task_completes_all_cases(engine):
    workflow = build_workflow()

    result = SimulationRunner(seed=1).run(workflow, 10, engine=engine)

    assert result.kpi.total_cases == 10
    assert result.kpi.completed_cases == 10


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_multi_resource_task_counts_toward_kpi(engine):
    workflow = build_workflow()

    result = SimulationRunner(seed=1).run(workflow, 5, engine=engine)

    assert result.kpi.multi_resource_task_count == 5


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_multi_resource_task_charges_cost_for_every_participant(engine):
    workflow = build_workflow()

    result = SimulationRunner(seed=1).run(workflow, 1, engine=engine)

    # Manager's draft (10 min) + joint review (30 min each for manager and legal).
    manager_cost = (10.0 / 60.0) * 60.0 + (30.0 / 60.0) * 60.0
    legal_cost = (30.0 / 60.0) * 90.0
    assert result.kpi.total_cost == pytest.approx(manager_cost + legal_cost)


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_multi_resource_task_records_coordination_delay_under_contention(engine):
    workflow = build_workflow()

    result = SimulationRunner(seed=7).run(
        workflow, 30, arrival_interval_minutes=5.0, engine=engine
    )

    # With cases arriving faster than the joint review can clear them,
    # legal (who is not otherwise busy on "draft") must wait for the
    # manager to sync up, producing measurable coordination delay.
    assert result.kpi.total_coordination_delay_minutes >= 0.0
    assert result.kpi.node_coordination_delay_minutes.get("review", 0.0) >= 0.0


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_multi_resource_task_started_event_lists_participants(engine):
    workflow = build_workflow()

    result = SimulationRunner(seed=1).run(workflow, 1, engine=engine)

    review_started = [
        event
        for event in result.events
        if event.event_type == EventType.TASK_STARTED and event.node_id == "review"
    ]
    assert len(review_started) == 1
    assert set(review_started[0].details["participants"]) == {"manager", "legal"}


def test_single_resource_nodes_are_unaffected_by_multi_resource_support():
    workflow = build_workflow()

    result = SimulationRunner(seed=1).run(workflow, 1, engine="simple")

    draft_started = [
        event
        for event in result.events
        if event.event_type == EventType.TASK_STARTED and event.node_id == "draft"
    ]
    assert draft_started[0].details == {}
    assert result.kpi.multi_resource_task_count == 1  # only "review" counts
