import pytest

from b2b_workflow_simulator.primitives.edge import Edge


def test_edge_creates_with_defaults():
    edge = Edge(source="intake", target="research")

    assert edge.source == "intake"
    assert edge.target == "research"
    assert edge.probability == 1.0
    assert edge.condition == ""


def test_edge_accepts_probability_and_condition():
    edge = Edge(source="research", target="disqualified", probability=0.4, condition="poor_fit")

    assert edge.probability == 0.4
    assert edge.condition == "poor_fit"


def test_edge_rejects_empty_source():
    with pytest.raises(ValueError, match="source"):
        Edge(source="", target="research")


def test_edge_rejects_empty_target():
    with pytest.raises(ValueError, match="target"):
        Edge(source="intake", target="")


@pytest.mark.parametrize("probability", [-0.1, 1.1])
def test_edge_rejects_out_of_range_probability(probability):
    with pytest.raises(ValueError, match="probability"):
        Edge(source="intake", target="research", probability=probability)
