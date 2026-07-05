"""Edge primitive: a directed transition between two workflow nodes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Edge:
    """A directed connection from one node to another.

    Edges model handoffs between stages, including conditional branching
    (e.g. "if the lead is qualified, go to Proposal; otherwise go to
    Nurture"). When a node has multiple outgoing edges, `probability` is
    used to route cases stochastically during simulation, which is useful
    for modelling qualification rates, escalation rates, and similar
    real-world branching behavior.

    Attributes:
        source: node_id of the originating node.
        target: node_id of the destination node.
        probability: Likelihood this edge is taken when multiple outgoing
            edges exist from the same source. Probabilities for all edges
            leaving a given source should sum to 1.0.
        condition: Optional human-readable label describing when this edge
            is taken (e.g. "qualified", "rejected"). Purely descriptive.
    """

    source: str
    target: str
    probability: float = 1.0
    condition: str = ""

    def __post_init__(self) -> None:
        if not self.source or not self.target:
            raise ValueError("source and target must be non-empty node ids")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0.0 and 1.0")
