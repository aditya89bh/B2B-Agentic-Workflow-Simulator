import pytest

from b2b_workflow_simulator.discrete_event import DiscreteEventEngine
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.primitives.event import EventType
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.primitives.shift import Shift
from b2b_workflow_simulator.primitives.worker import Worker
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow


def build_pool_workflow(num_workers: int = 2, error_rate: float = 0.0) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Pooled", entry_node_id="handle")
    workers = [
        Worker(worker_id=f"w{i}", name=f"Worker {i}", hourly_cost=40.0, error_rate=error_rate)
        for i in range(num_workers)
    ]
    workflow.add_actor(ActorPool(actor_id="team", name="Support Team", workers=workers))
    workflow.add_node(
        Node(
            node_id="handle",
            name="Handle",
            actor_id="team",
            base_duration_minutes=30.0,
            is_terminal=True,
        )
    )
    return workflow


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_workflow_completes_all_cases(engine):
    workflow = build_pool_workflow()

    result = SimulationRunner(seed=1).run(workflow, 20, engine=engine)

    assert result.kpi.total_cases == 20
    assert result.kpi.completed_cases == 20


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_workflow_reports_pool_and_worker_utilization(engine):
    workflow = build_pool_workflow()

    result = SimulationRunner(seed=1).run(
        workflow, 20, arrival_interval_minutes=10.0, engine=engine
    )

    assert "team" in result.kpi.pool_utilization
    assert set(result.kpi.worker_utilization["team"]) == {"w0", "w1"}
    assert result.kpi.pool_utilization["team"] > 0.0


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_workflow_tracks_wait_time_without_arrival_interval(engine):
    """Pools always enforce capacity, even without arrival_interval_minutes."""
    workflow = build_pool_workflow(num_workers=1)

    result = SimulationRunner(seed=1).run(workflow, 5, engine=engine)

    assert result.kpi.total_wait_minutes > 0.0


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_workflow_records_failures_from_worker_error_rate(engine):
    workflow = build_pool_workflow(error_rate=1.0)

    result = SimulationRunner(seed=1).run(workflow, 5, engine=engine)

    assert result.kpi.failed_cases == 5
    assert result.kpi.completed_cases == 0


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_task_events_include_worker_id(engine):
    workflow = build_pool_workflow()

    result = SimulationRunner(seed=1).run(workflow, 3, engine=engine)

    started_events = [e for e in result.events if e.event_type == EventType.TASK_STARTED]
    assert all(e.details.get("worker_id") in {"w0", "w1"} for e in started_events)


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_workflow_is_deterministic_given_same_seed(engine):
    workflow = build_pool_workflow()

    result_a = SimulationRunner(seed=5).run(
        workflow, 30, arrival_interval_minutes=15.0, engine=engine
    )
    result_b = SimulationRunner(seed=5).run(
        workflow, 30, arrival_interval_minutes=15.0, engine=engine
    )

    assert result_a.kpi == result_b.kpi


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_routes_around_unavailable_workers(engine):
    workflow = Workflow(workflow_id="wf", name="Pooled", entry_node_id="handle")
    workflow.add_actor(
        ActorPool(
            actor_id="team",
            name="Support Team",
            workers=[
                Worker(worker_id="out", name="Out", available=False),
                Worker(worker_id="in", name="In", available=True),
            ],
        )
    )
    workflow.add_node(
        Node(
            node_id="handle",
            name="Handle",
            actor_id="team",
            base_duration_minutes=10.0,
            is_terminal=True,
        )
    )

    result = SimulationRunner(seed=1).run(workflow, 5, engine=engine)

    started_events = [e for e in result.events if e.event_type == EventType.TASK_STARTED]
    assert all(e.details.get("worker_id") == "in" for e in started_events)


@pytest.mark.parametrize("engine", ["simple", "discrete"])
def test_pool_respects_shift_hours(engine):
    workflow = Workflow(workflow_id="wf", name="Pooled", entry_node_id="handle")
    workflow.add_actor(
        ActorPool(
            actor_id="team",
            name="Support Team",
            workers=[
                Worker(
                    worker_id="w0",
                    name="Worker",
                    shifts=[
                        Shift(
                            name="Day",
                            days=frozenset({0, 1, 2, 3, 4}),
                            start_hour=9,
                            end_hour=17,
                        )
                    ],
                )
            ],
        )
    )
    workflow.add_node(
        Node(
            node_id="handle",
            name="Handle",
            actor_id="team",
            base_duration_minutes=10.0,
            is_terminal=True,
        )
    )

    result = SimulationRunner(seed=1).run(workflow, 1, engine=engine)

    started_events = [e for e in result.events if e.event_type == EventType.TASK_STARTED]
    assert started_events[0].timestamp_minutes == 9 * 60.0


def test_direct_discrete_engine_supports_pools():
    workflow = build_pool_workflow()

    result = DiscreteEventEngine(seed=1).run(workflow, 10, arrival_interval_minutes=5.0)

    assert result.kpi.completed_cases == 10
    assert result.kpi.pool_utilization["team"] > 0.0
