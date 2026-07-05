import pytest

from b2b_workflow_simulator.monte_carlo import (
    COMPARISON_METRICS,
    KPI_METRICS,
    MetricStats,
    compute_metric_stats,
    run_monte_carlo,
    run_monte_carlo_comparison,
)
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow


def build_before() -> Workflow:
    workflow = Workflow(workflow_id="test-before", name="Test Before", entry_node_id="review")
    workflow.add_actor(
        HumanActor(actor_id="agent", name="Agent", hourly_cost=30.0, error_rate=0.1)
    )
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
    workflow = Workflow(workflow_id="test-after", name="Test After", entry_node_id="ai_review")
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


class TestComputeMetricStats:
    def test_empty_values_returns_zeroed_stats(self):
        stats = compute_metric_stats([])
        assert stats == MetricStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def test_single_value_has_zero_std_dev(self):
        stats = compute_metric_stats([5.0])
        assert stats.mean == 5.0
        assert stats.std_dev == 0.0
        assert stats.p10 == 5.0
        assert stats.p90 == 5.0

    def test_known_distribution_produces_expected_stats(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        stats = compute_metric_stats(values)
        assert stats.sample_count == 10
        assert stats.minimum == 1.0
        assert stats.maximum == 10.0
        assert stats.mean == pytest.approx(5.5)
        assert stats.median == pytest.approx(5.5)
        assert stats.p10 == pytest.approx(1.9)
        assert stats.p90 == pytest.approx(9.1)
        assert stats.std_dev > 0.0

    def test_spread_is_p90_minus_p10(self):
        stats = compute_metric_stats([1.0, 2.0, 3.0, 4.0, 5.0])
        assert stats.spread == pytest.approx(stats.p90 - stats.p10)


class TestRunMonteCarlo:
    def test_rejects_empty_seeds(self):
        with pytest.raises(ValueError, match="seeds must contain"):
            run_monte_carlo(build_before, 10, [])

    def test_rejects_non_positive_num_cases(self):
        with pytest.raises(ValueError, match="num_cases must be"):
            run_monte_carlo(build_before, 0, [1, 2])

    def test_produces_stats_for_every_kpi_metric(self):
        result = run_monte_carlo(build_before, 20, [1, 2, 3, 4, 5])
        assert result.workflow_name == "Test Before"
        assert result.num_runs == 5
        assert set(result.metric_stats) == set(KPI_METRICS)
        for stats in result.metric_stats.values():
            assert stats.sample_count == 5

    def test_different_seeds_produce_variability(self):
        result = run_monte_carlo(build_before, 30, list(range(1, 11)))
        completion = result.metric_stats["completion_rate"]
        assert completion.minimum <= completion.mean <= completion.maximum

    def test_same_seed_repeated_gives_zero_variability(self):
        result = run_monte_carlo(build_before, 20, [42, 42, 42])
        for stats in result.metric_stats.values():
            assert stats.std_dev == pytest.approx(0.0)

    def test_supports_discrete_engine(self):
        result = run_monte_carlo(build_before, 15, [1, 2, 3], engine="discrete")
        assert result.num_runs == 3

    def test_supports_arrival_interval(self):
        result = run_monte_carlo(build_before, 15, [1, 2, 3], arrival_interval_minutes=5.0)
        assert result.num_runs == 3


class TestRunMonteCarloComparison:
    def test_rejects_empty_seeds(self):
        with pytest.raises(ValueError, match="seeds must contain"):
            run_monte_carlo_comparison(build_before, build_after, 10, [])

    def test_produces_stats_for_every_comparison_metric(self):
        result = run_monte_carlo_comparison(
            build_before, build_after, 30, [1, 2, 3, 4, 5], implementation_cost=100.0
        )
        assert result.before_name == "Test Before"
        assert result.after_name == "Test After"
        assert result.num_runs == 5
        assert set(result.metric_stats) == set(COMPARISON_METRICS)

    def test_after_is_cheaper_and_faster_than_before_on_average(self):
        result = run_monte_carlo_comparison(build_before, build_after, 40, list(range(1, 11)))
        assert (
            result.metric_stats["cost_per_case_after"].mean
            < result.metric_stats["cost_per_case_before"].mean
        )

    def test_payback_omitted_when_no_implementation_cost_given(self):
        result = run_monte_carlo_comparison(build_before, build_after, 20, [1, 2, 3])
        assert result.metric_stats["payback_in_cases"].sample_count == 0

    def test_payback_populated_when_implementation_cost_given(self):
        result = run_monte_carlo_comparison(
            build_before, build_after, 20, [1, 2, 3], implementation_cost=50.0
        )
        assert result.metric_stats["payback_in_cases"].sample_count == 3
