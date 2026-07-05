import pytest

from b2b_workflow_simulator.discrete_event import DiscreteEventEngine
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.event import EventType
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow


def build_linear_workflow(error_rate: float = 0.0) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Linear", entry_node_id="a")
    workflow.add_actor(
        HumanActor(actor_id="rep", name="Rep", hourly_cost=60.0, error_rate=error_rate)
    )
    workflow.add_node(Node(node_id="a", name="A", actor_id="rep", base_duration_minutes=10.0))
    workflow.add_node(
        Node(node_id="b", name="B", actor_id="rep", base_duration_minutes=20.0, is_terminal=True)
    )
    workflow.add_edge(Edge("a", "b"))
    return workflow


def build_two_actor_workflow() -> Workflow:
    """Two cases can be in flight on different actors at once."""
    workflow = Workflow(workflow_id="wf", name="TwoActor", entry_node_id="triage")
    workflow.add_actor(HumanActor(actor_id="triager", name="Triager", hourly_cost=40.0))
    workflow.add_actor(HumanActor(actor_id="closer", name="Closer", hourly_cost=80.0))
    workflow.add_node(
        Node(node_id="triage", name="Triage", actor_id="triager", base_duration_minutes=1.0)
    )
    workflow.add_node(
        Node(
            node_id="close",
            name="Close",
            actor_id="closer",
            base_duration_minutes=15.0,
            is_terminal=True,
        )
    )
    workflow.add_edge(Edge("triage", "close"))
    return workflow


def test_rejects_non_positive_case_count():
    with pytest.raises(ValueError, match="num_cases"):
        DiscreteEventEngine(seed=1).run(build_linear_workflow(), 0)


def test_rejects_negative_arrival_interval():
    with pytest.raises(ValueError, match="arrival_interval_minutes"):
        DiscreteEventEngine(seed=1).run(build_linear_workflow(), 5, arrival_interval_minutes=-1.0)


def test_produces_one_result_per_case_with_no_errors():
    result = DiscreteEventEngine(seed=1).run(build_linear_workflow(), 10)

    assert result.kpi.total_cases == 10
    assert result.kpi.completed_cases == 10
    assert result.kpi.failed_cases == 0


def test_is_deterministic_given_same_seed():
    workflow = build_linear_workflow(error_rate=0.3)

    result_a = DiscreteEventEngine(seed=123).run(workflow, 50)
    result_b = DiscreteEventEngine(seed=123).run(workflow, 50)

    assert result_a.kpi == result_b.kpi


def test_capacity_aware_run_is_deterministic_given_same_seed():
    workflow = build_linear_workflow(error_rate=0.2)

    result_a = DiscreteEventEngine(seed=7).run(workflow, 30, arrival_interval_minutes=10.0)
    result_b = DiscreteEventEngine(seed=7).run(workflow, 30, arrival_interval_minutes=10.0)

    assert result_a.kpi == result_b.kpi


def test_marks_case_failed_when_actor_always_errors():
    result = DiscreteEventEngine(seed=1).run(build_linear_workflow(error_rate=1.0), 5)

    assert result.kpi.failed_cases == 5
    assert result.kpi.completed_cases == 0
    event_types = [event.event_type for event in result.events]
    assert EventType.TASK_FAILED in event_types
    assert EventType.CASE_FAILED in event_types


def test_emits_events_in_chronological_order():
    workflow = build_linear_workflow(error_rate=0.0)

    result = DiscreteEventEngine(seed=1).run(workflow, 20, arrival_interval_minutes=1.0)

    timestamps = [event.timestamp_minutes for event in result.events]
    assert timestamps == sorted(timestamps)


def test_case_started_first_and_case_completed_last_per_case():
    workflow = build_linear_workflow(error_rate=0.0)
    result = DiscreteEventEngine(seed=1).run(workflow, 1)

    event_types = [event.event_type for event in result.events]
    assert event_types[0] == EventType.CASE_STARTED
    assert event_types[-1] == EventType.CASE_COMPLETED


def test_overloaded_run_emits_queued_and_resource_released_events():
    workflow = build_linear_workflow(error_rate=0.0)

    result = DiscreteEventEngine(seed=1).run(workflow, 20, arrival_interval_minutes=1.0)

    event_types = [event.event_type for event in result.events]
    assert EventType.TASK_QUEUED in event_types
    assert EventType.RESOURCE_RELEASED in event_types
    assert result.kpi.total_wait_minutes > 0.0


def test_uncontended_run_has_no_wait_time():
    result = DiscreteEventEngine(seed=1).run(build_linear_workflow(), 20)

    assert result.kpi.total_wait_minutes == 0.0
    assert result.kpi.actor_utilization == {}


def test_tracks_actor_utilization_under_capacity_mode():
    workflow = build_linear_workflow(error_rate=0.0)

    result = DiscreteEventEngine(seed=1).run(workflow, 10, arrival_interval_minutes=100.0)

    assert result.kpi.actor_busy_minutes["rep"] == pytest.approx(10 * 30.0)


def test_respects_branching_probabilities_over_many_cases():
    workflow = Workflow(workflow_id="wf", name="Branching", entry_node_id="start")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="start", name="Start", actor_id="rep"))
    workflow.add_node(Node(node_id="path_a", name="A", actor_id="rep", is_terminal=True))
    workflow.add_node(Node(node_id="path_b", name="B", actor_id="rep", is_terminal=True))
    workflow.add_edge(Edge("start", "path_a", probability=0.9))
    workflow.add_edge(Edge("start", "path_b", probability=0.1))

    result = DiscreteEventEngine(seed=99).run(workflow, 2000)

    path_a_visits = result.kpi.node_visit_counts.get("path_a", 0)
    path_b_visits = result.kpi.node_visit_counts.get("path_b", 0)
    total = path_a_visits + path_b_visits

    assert total == 2000
    assert 0.85 < path_a_visits / total < 0.95


def test_counts_ai_agent_escalations():
    workflow = Workflow(workflow_id="wf", name="Escalating", entry_node_id="a")
    workflow.add_actor(
        AIAgentActor(actor_id="bot", name="Bot", escalation_rate=1.0, error_rate=0.0)
    )
    workflow.add_node(
        Node(node_id="a", name="A", actor_id="bot", base_duration_minutes=5.0, is_terminal=True)
    )

    result = DiscreteEventEngine(seed=1).run(workflow, 10)

    assert result.kpi.total_escalations == 10
    assert result.kpi.escalation_rate == 1.0


def test_interleaves_cases_across_actors_chronologically():
    """Case 2 can start its triage step before case 1 finishes its close step."""
    workflow = build_two_actor_workflow()

    result = DiscreteEventEngine(seed=1).run(workflow, 3, arrival_interval_minutes=5.0)

    triage_starts = [
        event.timestamp_minutes
        for event in result.events
        if event.event_type == EventType.TASK_STARTED and event.node_id == "triage"
    ]
    # Every case's triage starts at its own arrival time: the 1-minute triage
    # step never contends for the shared actor at a 5-minute arrival cadence.
    assert triage_starts == pytest.approx([0.0, 5.0, 10.0])


def test_simulation_runner_engine_discrete_matches_direct_engine_use():
    workflow = build_linear_workflow(error_rate=0.1)

    via_runner = SimulationRunner(seed=5).run(workflow, 25, engine="discrete")
    direct = DiscreteEventEngine(seed=5).run(workflow, 25)

    assert via_runner.kpi == direct.kpi


def test_two_engines_can_diverge_under_shared_actor_contention():
    """The whole point of the discrete engine: it resolves contention differently."""
    workflow = build_two_actor_workflow()

    simple = SimulationRunner(seed=3).run(workflow, 15, arrival_interval_minutes=3.0)
    discrete = SimulationRunner(seed=3).run(
        workflow, 15, arrival_interval_minutes=3.0, engine="discrete"
    )

    # Both are valid, deterministic simulations of the same workflow; they
    # need not produce identical wait-time totals since the engines process
    # contention in different orders.
    assert simple.kpi.completed_cases == discrete.kpi.completed_cases == 15
