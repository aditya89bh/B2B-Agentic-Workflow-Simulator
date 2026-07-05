import pytest

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.sensitivity import (
    SensitivityResult,
    SweepPoint,
    format_sensitivity_table,
    run_sensitivity_sweep,
)
from b2b_workflow_simulator.workflow import Workflow


def build_before() -> Workflow:
    workflow = Workflow(
        workflow_id="test-before",
        name="Test Before",
        entry_node_id="review",
    )
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


def build_after() -> Workflow:
    workflow = Workflow(
        workflow_id="test-after",
        name="Test After",
        entry_node_id="ai_review",
    )
    workflow.add_actor(
        AIAgentActor(actor_id="ai", name="AI Reviewer", cost_per_execution=1.0, error_rate=0.05)
    )
    workflow.add_node(
        Node(
            node_id="ai_review",
            name="AI Review",
            actor_id="ai",
            base_duration_minutes=2.0,
            is_terminal=True,
        )
    )
    return workflow


def test_sweep_rejects_unknown_parameter():
    with pytest.raises(ValueError, match="Unknown sensitivity parameter"):
        run_sensitivity_sweep(build_before, build_after, "not_a_parameter", [1, 2], num_cases=10)


def test_sweep_rejects_empty_values():
    with pytest.raises(ValueError, match="values must contain"):
        run_sensitivity_sweep(build_before, build_after, "ai_error_rate", [], num_cases=10)


def test_sweep_rejects_non_positive_num_cases():
    with pytest.raises(ValueError, match="num_cases must be"):
        run_sensitivity_sweep(build_before, build_after, "ai_error_rate", [0.1], num_cases=0)


def test_sweep_ai_error_rate_produces_one_point_per_value():
    result = run_sensitivity_sweep(
        build_before, build_after, "ai_error_rate", [0.0, 0.5, 1.0], num_cases=200, seed=1
    )

    assert len(result.points) == 3
    assert [point.value for point in result.points] == [0.0, 0.5, 1.0]


def test_sweep_ai_error_rate_reduces_completion_rate_as_it_increases():
    result = run_sensitivity_sweep(
        build_before, build_after, "ai_error_rate", [0.0, 0.5, 1.0], num_cases=200, seed=1
    )

    completion_rates = [point.diff.completion_rate.after for point in result.points]
    assert completion_rates[0] > completion_rates[1] > completion_rates[2]
    assert completion_rates[2] == 0.0


def test_sweep_ai_cost_per_execution_reduces_savings_as_cost_rises():
    result = run_sensitivity_sweep(
        build_before,
        build_after,
        "ai_cost_per_execution",
        [0.0, 100.0, 1000.0],
        num_cases=200,
        seed=1,
    )

    savings = [point.diff.roi.total_cost_savings for point in result.points]
    assert savings[0] > savings[1] > savings[2]


def test_sweep_human_hourly_cost_applies_to_before_and_after():
    result = run_sensitivity_sweep(
        build_before, build_after, "human_hourly_cost", [10.0, 100.0], num_cases=50, seed=1
    )

    before_costs = [point.diff.total_cost.before for point in result.points]
    assert before_costs[1] > before_costs[0]


def test_sweep_arrival_interval_introduces_wait_time_when_small():
    result = run_sensitivity_sweep(
        build_before, build_after, "arrival_interval", [0.01, 1000.0], num_cases=100, seed=1
    )

    wait_times = [point.diff.wait_time_minutes.before for point in result.points]
    assert wait_times[0] >= wait_times[1]


def test_sweep_implementation_cost_does_not_change_simulated_savings():
    result = run_sensitivity_sweep(
        build_before, build_after, "implementation_cost", [100.0, 100000.0], num_cases=50, seed=1
    )

    savings = [point.diff.roi.total_cost_savings for point in result.points]
    assert savings[0] == pytest.approx(savings[1])


def test_sweep_implementation_cost_changes_payback():
    result = run_sensitivity_sweep(
        build_before, build_after, "implementation_cost", [1.0, 100000.0], num_cases=50, seed=1
    )

    paybacks = [point.diff.roi.payback_in_cases for point in result.points]
    assert paybacks[0] is not None
    assert paybacks[1] is None or paybacks[1] > paybacks[0]


def test_break_even_range_detects_sign_change():
    points = [
        SweepPoint(value=1.0, diff=_fake_diff(total_cost_savings=100.0)),
        SweepPoint(value=2.0, diff=_fake_diff(total_cost_savings=-50.0)),
    ]
    result = SensitivityResult(parameter="test", points=points)

    assert result.break_even_range() == (1.0, 2.0)


def test_break_even_range_returns_none_when_no_sign_change():
    points = [
        SweepPoint(value=1.0, diff=_fake_diff(total_cost_savings=100.0)),
        SweepPoint(value=2.0, diff=_fake_diff(total_cost_savings=50.0)),
    ]
    result = SensitivityResult(parameter="test", points=points)

    assert result.break_even_range() is None


def test_break_even_range_handles_exact_zero():
    points = [
        SweepPoint(value=1.0, diff=_fake_diff(total_cost_savings=0.0)),
        SweepPoint(value=2.0, diff=_fake_diff(total_cost_savings=-50.0)),
    ]
    result = SensitivityResult(parameter="test", points=points)

    assert result.break_even_range() == (1.0, 1.0)


def test_format_sensitivity_table_includes_parameter_name_and_break_even():
    result = run_sensitivity_sweep(
        build_before,
        build_after,
        "ai_cost_per_execution",
        [0.0, 100.0, 1000.0],
        num_cases=200,
        seed=1,
    )

    table = format_sensitivity_table(result)

    assert "ai_cost_per_execution" in table
    assert "Break-even" in table


def _fake_diff(total_cost_savings: float):
    from b2b_workflow_simulator.kpi import KPIResult
    from b2b_workflow_simulator.redesign import compare_workflows

    before = KPIResult(
        workflow_name="Before", total_cases=10, completed_cases=10, total_cost=1000.0
    )
    after = KPIResult(
        workflow_name="After",
        total_cases=10,
        completed_cases=10,
        total_cost=1000.0 - total_cost_savings,
    )
    return compare_workflows(before, after)
