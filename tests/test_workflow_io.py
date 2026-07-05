import json

import pytest

from b2b_workflow_simulator.examples.sales_lead_qualification import build_before_workflow
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.duration import DurationModel
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow
from b2b_workflow_simulator.workflow_io import (
    WorkflowSchemaError,
    load_workflow,
    save_workflow,
    validate_workflow_dict,
    workflow_from_dict,
    workflow_to_dict,
)


def build_small_workflow() -> Workflow:
    workflow = Workflow(
        workflow_id="test-workflow",
        name="Test Workflow",
        entry_node_id="start",
        description="A minimal workflow for round-trip tests.",
    )
    workflow.add_actor(
        HumanActor(actor_id="human", name="Human Worker", hourly_cost=30.0, error_rate=0.05)
    )
    workflow.add_actor(
        AIAgentActor(
            actor_id="ai",
            name="AI Worker",
            cost_per_execution=0.5,
            error_rate=0.02,
            escalation_rate=0.1,
        )
    )
    workflow.add_node(
        Node(
            node_id="start",
            name="Start",
            actor_id="human",
            base_duration_minutes=10.0,
            duration_model=DurationModel(kind="triangular", minimum=5.0, mode=10.0, maximum=20.0),
            metadata={"tag": "intake"},
        )
    )
    workflow.add_node(
        Node(
            node_id="end",
            name="End",
            actor_id="ai",
            base_duration_minutes=2.0,
            additional_actor_ids=("human",),
            is_terminal=True,
        )
    )
    workflow.add_edge(Edge(source="start", target="end", probability=1.0, condition="always"))
    return workflow


def test_workflow_to_dict_round_trips_through_from_dict():
    workflow = build_small_workflow()

    data = workflow_to_dict(workflow)
    rebuilt = workflow_from_dict(data)

    assert rebuilt.workflow_id == workflow.workflow_id
    assert rebuilt.name == workflow.name
    assert rebuilt.entry_node_id == workflow.entry_node_id
    assert set(rebuilt.nodes) == set(workflow.nodes)
    assert set(rebuilt.actors) == set(workflow.actors)
    assert len(rebuilt.edges) == len(workflow.edges)


def test_round_trip_preserves_simulation_behavior():
    workflow = build_small_workflow()
    rebuilt = workflow_from_dict(workflow_to_dict(workflow))

    original_result = SimulationRunner(seed=5).run(workflow, 200)
    rebuilt_result = SimulationRunner(seed=5).run(rebuilt, 200)

    assert original_result.kpi.total_cost == rebuilt_result.kpi.total_cost
    assert original_result.kpi.completed_cases == rebuilt_result.kpi.completed_cases


def test_round_trip_preserves_duration_model():
    workflow = build_small_workflow()
    rebuilt = workflow_from_dict(workflow_to_dict(workflow))

    original_model = workflow.get_node("start").duration_model
    rebuilt_model = rebuilt.get_node("start").duration_model

    assert rebuilt_model.kind == original_model.kind
    assert rebuilt_model.minimum == original_model.minimum
    assert rebuilt_model.mode == original_model.mode
    assert rebuilt_model.maximum == original_model.maximum


def test_round_trip_preserves_node_metadata():
    workflow = build_small_workflow()
    rebuilt = workflow_from_dict(workflow_to_dict(workflow))

    assert rebuilt.get_node("start").metadata == {"tag": "intake"}


def test_round_trip_preserves_additional_actor_ids():
    workflow = build_small_workflow()
    rebuilt = workflow_from_dict(workflow_to_dict(workflow))

    assert rebuilt.get_node("end").additional_actor_ids == ("human",)
    assert rebuilt.get_node("start").additional_actor_ids == ()


def test_save_and_load_workflow_round_trips_via_file(tmp_path):
    workflow = build_small_workflow()
    path = tmp_path / "workflow.json"

    save_workflow(workflow, path)
    loaded = load_workflow(path)

    assert loaded.workflow_id == workflow.workflow_id
    assert set(loaded.nodes) == set(workflow.nodes)


def test_save_workflow_writes_readable_json(tmp_path):
    workflow = build_small_workflow()
    path = tmp_path / "workflow.json"

    save_workflow(workflow, path)
    data = json.loads(path.read_text())

    assert data["workflow_id"] == "test-workflow"
    assert len(data["actors"]) == 2
    assert len(data["nodes"]) == 2


def test_bundled_examples_round_trip_through_json():
    workflow = build_before_workflow()
    rebuilt = workflow_from_dict(workflow_to_dict(workflow))

    workflow.validate()
    rebuilt.validate()
    assert set(rebuilt.nodes) == set(workflow.nodes)


def test_validate_workflow_dict_rejects_non_dict():
    with pytest.raises(WorkflowSchemaError, match="must be a JSON object"):
        validate_workflow_dict(["not", "a", "dict"])


def test_validate_workflow_dict_rejects_missing_top_level_field():
    with pytest.raises(WorkflowSchemaError, match="missing required field 'name'"):
        validate_workflow_dict(
            {
                "workflow_id": "x",
                "entry_node_id": "a",
                "actors": [{"actor_id": "a", "type": "human", "name": "A"}],
                "nodes": [{"node_id": "a", "name": "A", "actor_id": "a", "is_terminal": True}],
                "edges": [],
            }
        )


def test_validate_workflow_dict_rejects_unknown_actor_type():
    with pytest.raises(WorkflowSchemaError, match="actors\\[0\\].type"):
        validate_workflow_dict(
            {
                "workflow_id": "x",
                "name": "X",
                "entry_node_id": "a",
                "actors": [{"actor_id": "a", "type": "robot", "name": "A"}],
                "nodes": [{"node_id": "a", "name": "A", "actor_id": "a", "is_terminal": True}],
                "edges": [],
            }
        )


def test_validate_workflow_dict_rejects_non_numeric_cost_field():
    with pytest.raises(WorkflowSchemaError, match="hourly_cost must be a number"):
        validate_workflow_dict(
            {
                "workflow_id": "x",
                "name": "X",
                "entry_node_id": "a",
                "actors": [
                    {"actor_id": "a", "type": "human", "name": "A", "hourly_cost": "expensive"}
                ],
                "nodes": [{"node_id": "a", "name": "A", "actor_id": "a", "is_terminal": True}],
                "edges": [],
            }
        )


def test_validate_workflow_dict_rejects_bad_duration_model_kind():
    with pytest.raises(WorkflowSchemaError, match="duration_model.kind"):
        validate_workflow_dict(
            {
                "workflow_id": "x",
                "name": "X",
                "entry_node_id": "a",
                "actors": [{"actor_id": "a", "type": "human", "name": "A"}],
                "nodes": [
                    {
                        "node_id": "a",
                        "name": "A",
                        "actor_id": "a",
                        "is_terminal": True,
                        "duration_model": {"kind": "gaussian"},
                    }
                ],
                "edges": [],
            }
        )


def test_validate_workflow_dict_rejects_missing_edge_field():
    expected = "edges\\[0\\] is missing required field 'target'"
    with pytest.raises(WorkflowSchemaError, match=expected):
        validate_workflow_dict(
            {
                "workflow_id": "x",
                "name": "X",
                "entry_node_id": "a",
                "actors": [{"actor_id": "a", "type": "human", "name": "A"}],
                "nodes": [{"node_id": "a", "name": "A", "actor_id": "a", "is_terminal": True}],
                "edges": [{"source": "a"}],
            }
        )


def test_validate_workflow_dict_rejects_empty_actors_list():
    with pytest.raises(WorkflowSchemaError, match="actors must be a non-empty list"):
        validate_workflow_dict(
            {
                "workflow_id": "x",
                "name": "X",
                "entry_node_id": "a",
                "actors": [],
                "nodes": [{"node_id": "a", "name": "A", "actor_id": "a", "is_terminal": True}],
                "edges": [],
            }
        )


def test_workflow_from_dict_raises_workflow_error_for_unknown_actor_reference():
    data = {
        "workflow_id": "x",
        "name": "X",
        "entry_node_id": "a",
        "actors": [{"actor_id": "a", "type": "human", "name": "A"}],
        "nodes": [
            {"node_id": "a", "name": "A", "actor_id": "does-not-exist", "is_terminal": True}
        ],
        "edges": [],
    }

    with pytest.raises(ValueError, match="unknown actor"):
        workflow_from_dict(data)


def test_load_workflow_raises_schema_error_for_invalid_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"not": "a workflow"}))

    with pytest.raises(WorkflowSchemaError):
        load_workflow(path)
