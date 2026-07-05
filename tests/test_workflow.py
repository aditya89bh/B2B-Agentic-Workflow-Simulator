import pytest

from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow


def build_simple_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf1", name="Simple", entry_node_id="start")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="start", name="Start", actor_id="rep"))
    workflow.add_node(Node(node_id="end", name="End", actor_id="rep", is_terminal=True))
    workflow.add_edge(Edge("start", "end"))
    return workflow


def test_add_node_requires_known_actor():
    workflow = Workflow(workflow_id="wf1", name="Simple", entry_node_id="start")

    with pytest.raises(ValueError, match="unknown actor"):
        workflow.add_node(Node(node_id="start", name="Start", actor_id="rep"))


def test_add_edge_requires_known_nodes():
    workflow = Workflow(workflow_id="wf1", name="Simple", entry_node_id="start")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="start", name="Start", actor_id="rep"))

    with pytest.raises(ValueError, match="target"):
        workflow.add_edge(Edge("start", "missing"))


def test_workflow_exposes_immutable_views():
    workflow = build_simple_workflow()

    nodes = workflow.nodes
    nodes["start"] = None

    assert workflow.get_node("start") is not None
    assert workflow.get_node("start").node_id == "start"


def test_outgoing_edges_filters_by_source():
    workflow = build_simple_workflow()

    edges = workflow.outgoing_edges("start")

    assert len(edges) == 1
    assert edges[0].target == "end"
    assert workflow.outgoing_edges("end") == []


def test_validate_passes_for_well_formed_workflow():
    workflow = build_simple_workflow()

    workflow.validate()


def test_validate_rejects_unknown_entry_node():
    workflow = Workflow(workflow_id="wf1", name="Simple", entry_node_id="missing")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="start", name="Start", actor_id="rep", is_terminal=True))

    with pytest.raises(ValueError, match="entry_node_id"):
        workflow.validate()


def test_validate_rejects_non_terminal_node_without_outgoing_edges():
    workflow = Workflow(workflow_id="wf1", name="Simple", entry_node_id="start")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="start", name="Start", actor_id="rep", is_terminal=False))

    with pytest.raises(ValueError, match="no outgoing edges"):
        workflow.validate()


def test_validate_rejects_probabilities_not_summing_to_one():
    workflow = Workflow(workflow_id="wf1", name="Simple", entry_node_id="start")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_node(Node(node_id="start", name="Start", actor_id="rep"))
    workflow.add_node(Node(node_id="a", name="A", actor_id="rep", is_terminal=True))
    workflow.add_node(Node(node_id="b", name="B", actor_id="rep", is_terminal=True))
    workflow.add_edge(Edge("start", "a", probability=0.5))
    workflow.add_edge(Edge("start", "b", probability=0.4))

    with pytest.raises(ValueError, match="sum to"):
        workflow.validate()
