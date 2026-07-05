import pytest

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.sensitivity_grid import (
    GridPoint,
    SensitivityGridResult,
    run_sensitivity_grid,
)
from b2b_workflow_simulator.workflow import Workflow


def build_before() -> Workflow:
    workflow = Workflow(workflow_id="test-before", name="Test Before", entry_node_id="review")
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


class TestRunSensitivityGrid:
    def test_rejects_unknown_x_parameter(self):
        with pytest.raises(ValueError, match="Unknown sensitivity parameter"):
            run_sensitivity_grid(
                build_before, build_after, "not_a_param", [1], "ai_error_rate", [0.1], 10
            )

    def test_rejects_unknown_y_parameter(self):
        with pytest.raises(ValueError, match="Unknown sensitivity parameter"):
            run_sensitivity_grid(
                build_before, build_after, "ai_error_rate", [0.1], "not_a_param", [1], 10
            )

    def test_rejects_same_parameter_on_both_axes(self):
        with pytest.raises(ValueError, match="must differ"):
            run_sensitivity_grid(
                build_before,
                build_after,
                "ai_error_rate",
                [0.1],
                "ai_error_rate",
                [0.2],
                10,
            )

    def test_rejects_empty_x_values(self):
        with pytest.raises(ValueError, match="x_values must contain"):
            run_sensitivity_grid(
                build_before, build_after, "ai_error_rate", [], "arrival_interval", [10], 10
            )

    def test_rejects_empty_y_values(self):
        with pytest.raises(ValueError, match="y_values must contain"):
            run_sensitivity_grid(
                build_before, build_after, "ai_error_rate", [0.1], "arrival_interval", [], 10
            )

    def test_rejects_non_positive_num_cases(self):
        with pytest.raises(ValueError, match="num_cases must be"):
            run_sensitivity_grid(
                build_before,
                build_after,
                "ai_error_rate",
                [0.1],
                "arrival_interval",
                [10],
                0,
            )

    def test_produces_one_point_per_combination(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.05, 0.1, 0.2],
            "ai_cost_per_execution",
            [0.5, 1.0],
            num_cases=20,
            seed=1,
        )
        assert len(result.points) == 6
        assert all(isinstance(point, GridPoint) for point in result.points)

    def test_point_at_returns_correct_combination(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.05, 0.1],
            "ai_cost_per_execution",
            [0.5, 1.0],
            num_cases=20,
            seed=1,
        )
        point = result.point_at(0.1, 1.0)
        assert point.x_value == 0.1
        assert point.y_value == 1.0

    def test_point_at_raises_for_missing_combination(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.05],
            "ai_cost_per_execution",
            [0.5],
            num_cases=20,
            seed=1,
        )
        with pytest.raises(KeyError):
            result.point_at(999.0, 999.0)

    def test_matrix_has_correct_shape(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.05, 0.1, 0.2],
            "ai_cost_per_execution",
            [0.5, 1.0],
            num_cases=20,
            seed=1,
        )
        matrix = result.matrix(lambda diff: diff.roi.total_cost_savings)
        assert len(matrix) == 2
        assert all(len(row) == 3 for row in matrix)

    def test_roi_matrix_matches_matrix_shape(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.05, 0.1],
            "ai_cost_per_execution",
            [0.5, 1.0],
            num_cases=20,
            seed=1,
        )
        roi_matrix = result.roi_matrix()
        assert len(roi_matrix) == 2
        assert all(len(row) == 2 for row in roi_matrix)

    def test_supports_implementation_cost_on_one_axis(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.05, 0.1],
            "implementation_cost",
            [100.0, 5000.0],
            num_cases=20,
            seed=1,
        )
        low_cost_point = result.point_at(0.05, 100.0)
        high_cost_point = result.point_at(0.05, 5000.0)
        assert low_cost_point.diff.roi.implementation_cost == 100.0
        assert high_cost_point.diff.roi.implementation_cost == 5000.0


class TestRegionClassification:
    def test_low_error_low_cost_is_safe(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.01],
            "ai_cost_per_execution",
            [0.1],
            num_cases=30,
            seed=1,
        )
        assert result.classify_region(0.01, 0.1) == "safe"

    def test_extremely_expensive_ai_is_negative_or_safe_but_not_unstable(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.01],
            "ai_cost_per_execution",
            [1000.0],
            num_cases=30,
            seed=1,
        )
        region = result.classify_region(0.01, 1000.0)
        assert region in ("negative", "safe")

    def test_region_map_matches_grid_shape(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.01, 0.5],
            "ai_cost_per_execution",
            [0.1, 10.0],
            num_cases=30,
            seed=1,
        )
        region_map = result.region_map()
        assert len(region_map) == 2
        assert all(len(row) == 2 for row in region_map)
        assert all(cell in ("safe", "negative", "unstable") for row in region_map for cell in row)

    def test_safe_negative_unstable_points_partition_all_points(self):
        result = run_sensitivity_grid(
            build_before,
            build_after,
            "ai_error_rate",
            [0.01, 0.3, 0.9],
            "ai_cost_per_execution",
            [0.1, 5.0, 50.0],
            num_cases=30,
            seed=1,
        )
        total = (
            len(result.safe_region_points())
            + len(result.negative_region_points())
            + len(result.unstable_region_points())
        )
        assert total == len(result.points)

    def test_empty_result_dataclass_defaults(self):
        result = SensitivityGridResult(x_parameter="ai_error_rate", y_parameter="arrival_interval")
        assert result.points == []
        assert result.x_values == []
        assert result.y_values == []
