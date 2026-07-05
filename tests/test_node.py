import pytest

from b2b_workflow_simulator.primitives.node import Node


def test_node_creates_with_defaults():
    node = Node(node_id="intake", name="Lead Intake", actor_id="sdr")

    assert node.node_id == "intake"
    assert node.name == "Lead Intake"
    assert node.actor_id == "sdr"
    assert node.description == ""
    assert node.base_duration_minutes == 0.0
    assert node.is_terminal is False
    assert node.metadata == {}


def test_node_accepts_full_configuration():
    node = Node(
        node_id="proposal",
        name="Proposal Draft",
        actor_id="ae",
        description="Draft the proposal",
        base_duration_minutes=45.0,
        is_terminal=True,
        metadata={"channel": "email"},
    )

    assert node.base_duration_minutes == 45.0
    assert node.is_terminal is True
    assert node.metadata == {"channel": "email"}


def test_node_rejects_empty_node_id():
    with pytest.raises(ValueError, match="node_id"):
        Node(node_id="", name="Lead Intake", actor_id="sdr")


def test_node_rejects_empty_actor_id():
    with pytest.raises(ValueError, match="actor_id"):
        Node(node_id="intake", name="Lead Intake", actor_id="")


def test_node_rejects_negative_duration():
    with pytest.raises(ValueError, match="base_duration_minutes"):
        Node(node_id="intake", name="Lead Intake", actor_id="sdr", base_duration_minutes=-1.0)


def test_node_metadata_is_independent_per_instance():
    first = Node(node_id="a", name="A", actor_id="sdr")
    second = Node(node_id="b", name="B", actor_id="sdr")

    first.metadata["key"] = "value"

    assert second.metadata == {}
