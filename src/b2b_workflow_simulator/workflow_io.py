"""Persist `Workflow` definitions to and from JSON, with structural validation.

This module deliberately avoids third-party schema libraries. Validation
is a straightforward tree walk with `isinstance` checks, which is enough
to catch malformed workflow documents (missing fields, wrong types, bad
enum values) and report exactly where the problem is, without pulling in
a dependency for what is fundamentally simple structural checking.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from b2b_workflow_simulator.primitives.actor import Actor
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.duration import DurationModel
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow

_ACTOR_TYPES = ("human", "ai_agent")
_DURATION_KINDS = ("fixed", "uniform", "triangular")

_HUMAN_NUMERIC_FIELDS = ("hourly_cost", "speed_multiplier", "error_rate", "available_hours_per_day")
_AI_NUMERIC_FIELDS = (
    "cost_per_execution",
    "speed_multiplier",
    "error_rate",
    "escalation_rate",
    "available_hours_per_day",
)


class WorkflowSchemaError(ValueError):
    """Raised when a workflow JSON document does not match the expected structure."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowSchemaError(message)


def _require_keys(data: dict, keys: tuple[str, ...], context: str) -> None:
    for key in keys:
        _require(key in data, f"{context} is missing required field '{key}'")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_workflow_dict(data: Any) -> None:
    """Raise `WorkflowSchemaError` if `data` is not a valid workflow document.

    This performs the same role as a JSON Schema validator, but is
    implemented directly with stdlib type checks so the project has no
    dependency on a schema library. See the module docstring for
    rationale.
    """
    _require(isinstance(data, dict), "workflow document must be a JSON object")
    required_keys = ("workflow_id", "name", "entry_node_id", "actors", "nodes", "edges")
    _require_keys(data, required_keys, "workflow")
    _require(
        isinstance(data["workflow_id"], str) and data["workflow_id"],
        "workflow_id must be a non-empty string",
    )
    _require(isinstance(data["name"], str) and data["name"], "name must be a non-empty string")
    _require(
        isinstance(data["entry_node_id"], str) and data["entry_node_id"],
        "entry_node_id must be a non-empty string",
    )
    _require(isinstance(data.get("description", ""), str), "description must be a string")
    _require(
        isinstance(data["actors"], list) and data["actors"], "actors must be a non-empty list"
    )
    _require(isinstance(data["nodes"], list) and data["nodes"], "nodes must be a non-empty list")
    _require(isinstance(data["edges"], list), "edges must be a list")

    for index, actor in enumerate(data["actors"]):
        _validate_actor_dict(actor, f"actors[{index}]")
    for index, node in enumerate(data["nodes"]):
        _validate_node_dict(node, f"nodes[{index}]")
    for index, edge in enumerate(data["edges"]):
        _validate_edge_dict(edge, f"edges[{index}]")


def _validate_actor_dict(actor: Any, context: str) -> None:
    _require(isinstance(actor, dict), f"{context} must be an object")
    _require_keys(actor, ("actor_id", "type", "name"), context)
    _require(
        actor["type"] in _ACTOR_TYPES, f"{context}.type must be one of {_ACTOR_TYPES}"
    )
    _require(
        isinstance(actor["actor_id"], str) and actor["actor_id"],
        f"{context}.actor_id must be a non-empty string",
    )
    _require(
        isinstance(actor["name"], str) and actor["name"],
        f"{context}.name must be a non-empty string",
    )
    numeric_fields = _HUMAN_NUMERIC_FIELDS if actor["type"] == "human" else _AI_NUMERIC_FIELDS
    for field_name in numeric_fields:
        if field_name in actor:
            _require(_is_number(actor[field_name]), f"{context}.{field_name} must be a number")
    if actor["type"] == "ai_agent" and "autonomy_level" in actor:
        _require(
            isinstance(actor["autonomy_level"], str), f"{context}.autonomy_level must be a string"
        )


def _validate_node_dict(node: Any, context: str) -> None:
    _require(isinstance(node, dict), f"{context} must be an object")
    _require_keys(node, ("node_id", "name", "actor_id"), context)
    _require(
        isinstance(node["node_id"], str) and node["node_id"],
        f"{context}.node_id must be a non-empty string",
    )
    _require(
        isinstance(node["actor_id"], str) and node["actor_id"],
        f"{context}.actor_id must be a non-empty string",
    )
    if "base_duration_minutes" in node:
        _require(
            _is_number(node["base_duration_minutes"]),
            f"{context}.base_duration_minutes must be a number",
        )
    if "is_terminal" in node:
        _require(isinstance(node["is_terminal"], bool), f"{context}.is_terminal must be a boolean")
    if "additional_actor_ids" in node:
        _require(
            isinstance(node["additional_actor_ids"], list)
            and all(isinstance(item, str) and item for item in node["additional_actor_ids"]),
            f"{context}.additional_actor_ids must be a list of non-empty strings",
        )
    if "metadata" in node:
        _require(isinstance(node["metadata"], dict), f"{context}.metadata must be an object")
    if "duration_model" in node:
        _validate_duration_model_dict(node["duration_model"], f"{context}.duration_model")


def _validate_duration_model_dict(duration_model: Any, context: str) -> None:
    _require(isinstance(duration_model, dict), f"{context} must be an object")
    _require("kind" in duration_model, f"{context} is missing required field 'kind'")
    _require(
        duration_model["kind"] in _DURATION_KINDS,
        f"{context}.kind must be one of {_DURATION_KINDS}",
    )
    for field_name in ("minimum", "maximum", "mode"):
        if duration_model.get(field_name) is not None:
            _require(
                _is_number(duration_model[field_name]), f"{context}.{field_name} must be a number"
            )


def _validate_edge_dict(edge: Any, context: str) -> None:
    _require(isinstance(edge, dict), f"{context} must be an object")
    _require_keys(edge, ("source", "target"), context)
    _require(
        isinstance(edge["source"], str) and edge["source"],
        f"{context}.source must be a non-empty string",
    )
    _require(
        isinstance(edge["target"], str) and edge["target"],
        f"{context}.target must be a non-empty string",
    )
    if "probability" in edge:
        _require(_is_number(edge["probability"]), f"{context}.probability must be a number")
    if "condition" in edge:
        _require(isinstance(edge["condition"], str), f"{context}.condition must be a string")


def workflow_from_dict(data: dict) -> Workflow:
    """Build a `Workflow` from a validated JSON-compatible dict.

    Raises `WorkflowSchemaError` if `data` does not match the expected
    structure, or `ValueError` if the resulting workflow is internally
    inconsistent (e.g. a node referencing an unknown actor).
    """
    validate_workflow_dict(data)

    workflow = Workflow(
        workflow_id=data["workflow_id"],
        name=data["name"],
        entry_node_id=data["entry_node_id"],
        description=data.get("description", ""),
    )
    for actor_data in data["actors"]:
        workflow.add_actor(_actor_from_dict(actor_data))
    for node_data in data["nodes"]:
        workflow.add_node(_node_from_dict(node_data))
    for edge_data in data["edges"]:
        workflow.add_edge(
            Edge(
                source=edge_data["source"],
                target=edge_data["target"],
                probability=edge_data.get("probability", 1.0),
                condition=edge_data.get("condition", ""),
            )
        )
    return workflow


def _actor_from_dict(data: dict) -> Actor:
    common: dict[str, Any] = {"actor_id": data["actor_id"], "name": data["name"]}
    if "available_hours_per_day" in data:
        common["available_hours_per_day"] = data["available_hours_per_day"]

    if data["type"] == "human":
        return HumanActor(
            **common,
            hourly_cost=data.get("hourly_cost", 0.0),
            speed_multiplier=data.get("speed_multiplier", 1.0),
            error_rate=data.get("error_rate", 0.0),
        )
    return AIAgentActor(
        **common,
        cost_per_execution=data.get("cost_per_execution", 0.0),
        speed_multiplier=data.get("speed_multiplier", 0.2),
        error_rate=data.get("error_rate", 0.0),
        escalation_rate=data.get("escalation_rate", 0.0),
        autonomy_level=data.get("autonomy_level", "autonomous"),
    )


def _node_from_dict(data: dict) -> Node:
    duration_data = data.get("duration_model", {"kind": "fixed"})
    duration_model = DurationModel(
        kind=duration_data.get("kind", "fixed"),
        minimum=duration_data.get("minimum"),
        maximum=duration_data.get("maximum"),
        mode=duration_data.get("mode"),
    )
    return Node(
        node_id=data["node_id"],
        name=data["name"],
        actor_id=data["actor_id"],
        description=data.get("description", ""),
        base_duration_minutes=data.get("base_duration_minutes", 0.0),
        duration_model=duration_model,
        is_terminal=data.get("is_terminal", False),
        additional_actor_ids=tuple(data.get("additional_actor_ids", [])),
        metadata=data.get("metadata", {}),
    )


def workflow_to_dict(workflow: Workflow) -> dict:
    """Serialize a `Workflow` to a JSON-compatible dict."""
    actors = []
    for actor in workflow.actors.values():
        actor_dict: dict[str, Any] = {
            "actor_id": actor.actor_id,
            "name": actor.name,
            "type": actor.kind,
            "available_hours_per_day": actor.available_hours_per_day,
        }
        if isinstance(actor, HumanActor):
            actor_dict.update(
                hourly_cost=actor.hourly_cost,
                speed_multiplier=actor.speed_multiplier,
                error_rate=actor.error_rate,
            )
        elif isinstance(actor, AIAgentActor):
            actor_dict.update(
                cost_per_execution=actor.cost_per_execution,
                speed_multiplier=actor.speed_multiplier,
                error_rate=actor.error_rate,
                escalation_rate=actor.escalation_rate,
                autonomy_level=actor.autonomy_level,
            )
        actors.append(actor_dict)

    nodes = []
    for node in workflow.nodes.values():
        nodes.append(
            {
                "node_id": node.node_id,
                "name": node.name,
                "actor_id": node.actor_id,
                "description": node.description,
                "base_duration_minutes": node.base_duration_minutes,
                "duration_model": {
                    "kind": node.duration_model.kind,
                    "minimum": node.duration_model.minimum,
                    "maximum": node.duration_model.maximum,
                    "mode": node.duration_model.mode,
                },
                "is_terminal": node.is_terminal,
                "additional_actor_ids": list(node.additional_actor_ids),
                "metadata": node.metadata,
            }
        )

    edges = [
        {
            "source": edge.source,
            "target": edge.target,
            "probability": edge.probability,
            "condition": edge.condition,
        }
        for edge in workflow.edges
    ]

    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "description": workflow.description,
        "entry_node_id": workflow.entry_node_id,
        "actors": actors,
        "nodes": nodes,
        "edges": edges,
    }


def save_workflow(workflow: Workflow, path: str | Path) -> None:
    """Write `workflow` to `path` as indented JSON."""
    Path(path).write_text(json.dumps(workflow_to_dict(workflow), indent=2) + "\n")


def load_workflow(path: str | Path) -> Workflow:
    """Read and validate a `Workflow` definition from a JSON file at `path`."""
    data = json.loads(Path(path).read_text())
    return workflow_from_dict(data)


__all__ = [
    "WorkflowSchemaError",
    "validate_workflow_dict",
    "workflow_from_dict",
    "workflow_to_dict",
    "save_workflow",
    "load_workflow",
]
