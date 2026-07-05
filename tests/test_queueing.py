
from b2b_workflow_simulator.discrete_event import DiscreteEventEngine
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.queueing import (
    COLLAPSING,
    GROWING,
    STABLE,
    QueueAnalysis,
    analyze_queue_behavior,
)
from b2b_workflow_simulator.simulation import SimulationResult, SimulationRunner
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


def test_uncontended_run_has_zero_queue_depth_and_no_idle_time_tracked():
    result = SimulationRunner(seed=1).run(build_linear_workflow(), 10)

    analysis = analyze_queue_behavior(result)

    assert analysis.max_queue_depth == {}
    assert analysis.queue_depth_timeline == {}


def test_overloaded_run_reports_positive_max_queue_depth():
    workflow = build_linear_workflow()

    result = SimulationRunner(seed=1).run(workflow, 40, arrival_interval_minutes=1.0)
    analysis = analyze_queue_behavior(result)

    assert analysis.max_queue_depth["rep"] > 0


def test_overloaded_run_produces_a_long_and_deep_queue():
    workflow = build_linear_workflow()

    # Cases arrive far faster than the single actor can absorb them.
    result = SimulationRunner(seed=1).run(workflow, 60, arrival_interval_minutes=1.0)
    analysis = analyze_queue_behavior(result)

    assert analysis.max_queue_depth["rep"] >= 50


def test_queue_trend_classifies_a_steadily_rising_timeline_as_growing():
    analysis = QueueAnalysis(
        queue_depth_timeline={"rep": [(0.0, 1), (10.0, 3), (20.0, 6), (30.0, 10)]}
    )

    assert analysis.queue_trend("rep") == GROWING


def test_queue_trend_classifies_a_steadily_draining_timeline_as_collapsing():
    analysis = QueueAnalysis(
        queue_depth_timeline={"rep": [(0.0, 10), (10.0, 6), (20.0, 3), (30.0, 1)]}
    )

    assert analysis.queue_trend("rep") == COLLAPSING


def test_queue_trend_classifies_a_flat_timeline_as_stable():
    analysis = QueueAnalysis(
        queue_depth_timeline={"rep": [(0.0, 4), (10.0, 5), (20.0, 4), (30.0, 5)]}
    )

    assert analysis.queue_trend("rep") == STABLE


def test_unknown_actor_has_stable_trend():
    result = SimulationRunner(seed=1).run(build_linear_workflow(), 10)
    analysis = analyze_queue_behavior(result)

    assert analysis.queue_trend("nobody") == STABLE


def test_generous_capacity_run_has_idle_time_and_positive_throughput():
    workflow = build_linear_workflow()

    result = SimulationRunner(seed=1).run(workflow, 10, arrival_interval_minutes=1000.0)
    analysis = analyze_queue_behavior(result)

    assert analysis.actor_idle_minutes["rep"] > 0.0
    assert analysis.throughput_per_hour > 0.0


def test_works_with_discrete_engine_results_too():
    workflow = build_linear_workflow()

    result = DiscreteEventEngine(seed=1).run(workflow, 30, arrival_interval_minutes=1.0)
    analysis = analyze_queue_behavior(result)

    assert analysis.max_queue_depth["rep"] > 0
    assert analysis.total_span_minutes > 0.0


def test_empty_events_produce_empty_analysis():
    analysis = analyze_queue_behavior(
        SimulationResult(workflow_name="empty", events=[], kpi=KPIResult(workflow_name="empty"))
    )

    assert analysis.total_span_minutes == 0.0
    assert analysis.throughput_per_hour == 0.0
