"""Workflow model: a graph of nodes and edges operated by a set of actors."""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.actor import Actor
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.node import Node


@dataclass
class Workflow:
    """A complete, executable definition of a business process.

    A `Workflow` is the "blueprint" that the simulation runner executes.
    It is deliberately just data (nodes, edges, actors) so the same
    workflow can be visualized, validated, diffed against a redesigned
    version, or simulated without any of those concerns leaking into the
    model itself.

    Attributes:
        workflow_id: Stable, unique identifier for this workflow definition.
        name: Human-readable name (e.g. "Sales Lead Qualification - Before").
        entry_node_id: node_id where every case begins.
        description: Longer explanation of what the workflow represents.
    """

    workflow_id: str
    name: str
    entry_node_id: str
    description: str = ""
    _nodes: dict[str, Node] = field(default_factory=dict, repr=False)
    _actors: dict[str, Actor] = field(default_factory=dict, repr=False)
    _edges: list[Edge] = field(default_factory=list, repr=False)

    def add_actor(self, actor: Actor) -> Workflow:
        """Register an actor available to perform work in this workflow."""
        self._actors[actor.actor_id] = actor
        return self

    def add_node(self, node: Node) -> Workflow:
        """Register a node, validating that its actor is already known."""
        if node.actor_id not in self._actors:
            raise ValueError(
                f"node '{node.node_id}' references unknown actor '{node.actor_id}'"
            )
        self._nodes[node.node_id] = node
        return self

    def add_edge(self, edge: Edge) -> Workflow:
        """Register a directed edge, validating both endpoints exist."""
        if edge.source not in self._nodes:
            raise ValueError(f"edge source '{edge.source}' is not a known node")
        if edge.target not in self._nodes:
            raise ValueError(f"edge target '{edge.target}' is not a known node")
        self._edges.append(edge)
        return self

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    @property
    def actors(self) -> dict[str, Actor]:
        return dict(self._actors)

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def get_node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def get_actor(self, actor_id: str) -> Actor:
        return self._actors[actor_id]

    def outgoing_edges(self, node_id: str) -> list[Edge]:
        """Return all edges leaving `node_id`, in the order they were added."""
        return [edge for edge in self._edges if edge.source == node_id]

    def validate(self) -> None:
        """Raise ValueError if the workflow is structurally inconsistent.

        Checks performed:
            - entry_node_id refers to a known node.
            - Every non-terminal node has at least one outgoing edge.
            - Outgoing edge probabilities from any node sum to ~1.0.
        """
        if self.entry_node_id not in self._nodes:
            raise ValueError(f"entry_node_id '{self.entry_node_id}' is not a known node")

        for node_id, node in self._nodes.items():
            edges = self.outgoing_edges(node_id)
            if not node.is_terminal and not edges:
                raise ValueError(
                    f"node '{node_id}' is non-terminal but has no outgoing edges"
                )
            if edges:
                total_probability = sum(edge.probability for edge in edges)
                if abs(total_probability - 1.0) > 1e-6:
                    raise ValueError(
                        f"outgoing edge probabilities from '{node_id}' sum to "
                        f"{total_probability}, expected 1.0"
                    )
