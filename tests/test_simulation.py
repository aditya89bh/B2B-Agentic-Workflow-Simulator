import pytest

from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.event import EventType
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow


def build_linear_workflow(error_rate: float = 0.0) -> Workflow:
    """A -> B (terminal), no branching, single human actor."""
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


def test_run_rejects_non_positive_case_count():
    workflow = build_linear_workflow()
    runner = SimulationRunner(seed=1)

    with pytest.raises(ValueError, match="num_cases"):
        runner.run(workflow, 0)


def test_run_produces_one_result_per_case_with_no_errors():
    workflow = build_linear_workflow(error_rate=0.0)
    runner = SimulationRunner(seed=1)

    result = runner.run(workflow, 10)

    assert result.kpi.total_cases == 10
    assert result.kpi.completed_cases == 10
    assert result.kpi.failed_cases == 0


def test_run_is_deterministic_given_same_seed():
    workflow = build_linear_workflow(error_rate=0.3)

    result_a = SimulationRunner(seed=123).run(workflow, 50)
    result_b = SimulationRunner(seed=123).run(workflow, 50)

    assert result_a.kpi == result_b.kpi


def test_run_computes_expected_cost_and_duration_without_failures():
    workflow = build_linear_workflow(error_rate=0.0)
    runner = SimulationRunner(seed=1)

    result = runner.run(workflow, 5)

    # 30 minutes/case at $60/hr = $30/case; 5 cases -> $150 total.
    assert result.kpi.total_cost == pytest.approx(150.0)
    assert result.kpi.total_duration_minutes == pytest.approx(150.0)
    assert result.kpi.node_visit_counts == {"a": 5, "b": 5}


def test_run_emits_case_started_and_completed_events():
    workflow = build_linear_workflow(error_rate=0.0)
    runner = SimulationRunner(seed=1)

    result = runner.run(workflow, 1)
    event_types = [event.event_type for event in result.events]

    assert event_types[0] == EventType.CASE_STARTED
    assert event_types[-1] == EventType.CASE_COMPLETED
    assert EventType.TASK_COMPLETED in event_types


def test_run_marks_case_failed_when_actor_always_errors():
    workflow = build_linear_workflow(error_rate=1.0)
    runner = SimulationRunner(seed=1)

    result = runner.run(workflow, 5)

    assert result.kpi.failed_cases == 5
    assert result.kpi.completed_cases == 0
    event_types = [event.event_type for event in result.events]
    assert EventType.TASK_FAILED in event_types
    assert EventType.CASE_FAILED in event_types
    # A failed first task means the case never reaches node "b".
    assert "b" not in result.kpi.node_visit_counts


def test_run_respects_branching_probabilities_over_many_cases():
    workflow = Workflow(workflow_id="wf", name="Branching", entry_node_id="start")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="start", name="Start", actor_id="rep"))
    workflow.add_node(Node(node_id="path_a", name="A", actor_id="rep", is_terminal=True))
    workflow.add_node(Node(node_id="path_b", name="B", actor_id="rep", is_terminal=True))
    workflow.add_edge(Edge("start", "path_a", probability=0.9))
    workflow.add_edge(Edge("start", "path_b", probability=0.1))

    result = SimulationRunner(seed=99).run(workflow, 2000)

    path_a_visits = result.kpi.node_visit_counts.get("path_a", 0)
    path_b_visits = result.kpi.node_visit_counts.get("path_b", 0)
    total = path_a_visits + path_b_visits

    assert total == 2000
    assert 0.85 < path_a_visits / total < 0.95
