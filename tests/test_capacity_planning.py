import pytest

from b2b_workflow_simulator.capacity_planning import (
    BALANCED,
    OVERLOADED,
    analyze_capacity,
    generate_capacity_report,
    generate_hiring_report,
    simulate_hiring,
)
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.primitives.worker import Worker
from b2b_workflow_simulator.workflow import Workflow


def build_pool_workflow(num_workers: int = 2) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Pooled", entry_node_id="handle")
    workers = [
        Worker(worker_id=f"w{i}", name=f"Worker {i}", hourly_cost=40.0)
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


def build_actor_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf2", name="Single Actor", entry_node_id="review")
    workflow.add_actor(HumanActor(actor_id="agent", name="Agent", hourly_cost=30.0))
    workflow.add_node(
        Node(
            node_id="review",
            name="Review",
            actor_id="agent",
            base_duration_minutes=20.0,
            is_terminal=True,
        )
    )
    return workflow


class TestAnalyzeCapacity:
    def test_overloaded_actor_recommends_more_capacity(self):
        kpi = KPIResult(workflow_name="wf", actor_utilization={"agent": 0.95})
        plan = analyze_capacity(kpi, target_utilization=0.75)
        assert len(plan.overloaded) == 1
        rec = plan.overloaded[0]
        assert rec.resource_id == "agent"
        assert rec.status == OVERLOADED
        assert rec.recommended_headcount > rec.current_headcount

    def test_underutilized_actor_recommends_less_capacity(self):
        kpi = KPIResult(workflow_name="wf", pool_utilization={"team": 0.1})
        plan = analyze_capacity(kpi, pool_sizes={"team": 5}, target_utilization=0.75)
        assert len(plan.underutilized) == 1
        rec = plan.underutilized[0]
        assert rec.resource_kind == "pool"
        assert rec.recommended_headcount < rec.current_headcount

    def test_balanced_utilization_recommends_no_change(self):
        kpi = KPIResult(workflow_name="wf", actor_utilization={"agent": 0.75})
        plan = analyze_capacity(kpi, target_utilization=0.75)
        assert len(plan.balanced) == 1
        assert plan.balanced[0].headcount_delta == 0

    def test_pool_size_inferred_from_worker_utilization_when_not_given(self):
        kpi = KPIResult(
            workflow_name="wf",
            pool_utilization={"team": 0.95},
            worker_utilization={"team": {"w0": 0.9, "w1": 1.0}},
        )
        plan = analyze_capacity(kpi)
        rec = plan.recommendations[0]
        assert rec.current_headcount == 2

    def test_no_utilization_data_produces_empty_plan(self):
        kpi = KPIResult(workflow_name="wf")
        plan = analyze_capacity(kpi)
        assert plan.recommendations == []

    def test_recommendation_rationale_mentions_resource_id(self):
        kpi = KPIResult(workflow_name="wf", actor_utilization={"agent": 0.95})
        plan = analyze_capacity(kpi)
        assert "agent" in plan.recommendations[0].rationale

    def test_custom_thresholds_change_classification(self):
        kpi = KPIResult(workflow_name="wf", actor_utilization={"agent": 0.6})
        default_plan = analyze_capacity(kpi)
        assert default_plan.recommendations[0].status == BALANCED

        strict_plan = analyze_capacity(kpi, overload_threshold=0.5)
        assert strict_plan.recommendations[0].status == OVERLOADED


class TestSimulateHiring:
    def test_rejects_empty_additional_workers(self):
        with pytest.raises(ValueError, match="additional_workers must contain"):
            simulate_hiring(build_pool_workflow, "team", [], num_cases=10)

    def test_rejects_non_pool_actor(self):
        extra = [Worker(worker_id="w-extra", name="Extra", hourly_cost=40.0)]
        with pytest.raises(TypeError, match="not an ActorPool"):
            simulate_hiring(build_actor_workflow, "agent", extra, num_cases=10)

    def test_adding_workers_increases_proposed_worker_count(self):
        extra = [Worker(worker_id="w-extra", name="Extra", hourly_cost=40.0)]
        result = simulate_hiring(
            lambda: build_pool_workflow(num_workers=1),
            "team",
            extra,
            num_cases=20,
            seed=1,
            arrival_interval_minutes=10.0,
        )
        assert result.baseline_worker_count == 1
        assert result.proposed_worker_count == 2

    def test_adding_workers_reduces_queue_depth_under_contention(self):
        extra = [
            Worker(worker_id="w-extra-1", name="Extra 1", hourly_cost=40.0),
            Worker(worker_id="w-extra-2", name="Extra 2", hourly_cost=40.0),
        ]
        result = simulate_hiring(
            lambda: build_pool_workflow(num_workers=1),
            "team",
            extra,
            num_cases=30,
            seed=1,
            arrival_interval_minutes=5.0,
        )
        assert result.proposed_max_queue_depth <= result.baseline_max_queue_depth
        assert result.queue_depth_change <= 0

    def test_adding_workers_reduces_wait_time_under_contention(self):
        extra = [
            Worker(worker_id="w-extra-1", name="Extra 1", hourly_cost=40.0),
            Worker(worker_id="w-extra-2", name="Extra 2", hourly_cost=40.0),
        ]
        result = simulate_hiring(
            lambda: build_pool_workflow(num_workers=1),
            "team",
            extra,
            num_cases=30,
            seed=1,
            arrival_interval_minutes=5.0,
        )
        assert result.wait_time_change_minutes <= 0.0

    def test_supports_discrete_engine(self):
        extra = [Worker(worker_id="w-extra", name="Extra", hourly_cost=40.0)]
        result = simulate_hiring(
            lambda: build_pool_workflow(num_workers=1),
            "team",
            extra,
            num_cases=20,
            seed=1,
            arrival_interval_minutes=10.0,
            engine="discrete",
        )
        assert result.proposed_worker_count == 2


class TestGenerateCapacityReport:
    def test_includes_workflow_name_and_recommendations(self):
        kpi = KPIResult(
            workflow_name="Support Ops", actor_utilization={"agent": 0.95, "reviewer": 0.2}
        )
        plan = analyze_capacity(kpi)
        report = generate_capacity_report(plan)
        assert "Support Ops" in report
        assert "agent" in report
        assert "reviewer" in report
        assert "STAFFING RECOMMENDATIONS" in report

    def test_handles_empty_plan_gracefully(self):
        kpi = KPIResult(workflow_name="Empty Ops")
        plan = analyze_capacity(kpi)
        report = generate_capacity_report(plan)
        assert "No capacity-aware utilization data" in report


class TestGenerateHiringReport:
    def test_includes_pool_and_headcount_change(self):
        extra = [Worker(worker_id="w-extra", name="Extra", hourly_cost=40.0)]
        result = simulate_hiring(
            lambda: build_pool_workflow(num_workers=1),
            "team",
            extra,
            num_cases=20,
            seed=1,
            arrival_interval_minutes=5.0,
        )
        report = generate_hiring_report(result)
        assert "team" in report
        assert "1 -> 2" in report
        assert "IMPACT" in report
