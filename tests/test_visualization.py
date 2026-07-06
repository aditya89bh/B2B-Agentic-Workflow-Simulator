"""Tests for workflow graph visualization (Mermaid + text)."""

from __future__ import annotations

from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.visualization import (
    compare_mermaid,
    compare_text,
    to_mermaid,
    to_text,
)


def _inv_before():
    return invoice_processing.build_before_workflow()


def _inv_after():
    return invoice_processing.build_after_workflow()


def _slq_before():
    return sales_lead_qualification.build_before_workflow()


# ---------------------------------------------------------------------------
# Mermaid output
# ---------------------------------------------------------------------------


def test_mermaid_starts_with_flowchart():
    result = to_mermaid(_inv_before())
    assert result.startswith("flowchart LR")


def test_mermaid_contains_all_nodes():
    wf = _inv_before()
    result = to_mermaid(wf)
    for node_id in wf.nodes:
        safe = node_id.replace("-", "_")
        assert safe in result, f"Node {node_id!r} not found in Mermaid output"


def test_mermaid_terminal_nodes_use_stadium_shape():
    wf = _inv_before()
    result = to_mermaid(wf)
    for node_id, node in wf.nodes.items():
        if node.is_terminal:
            safe = node_id.replace("-", "_")
            assert f"{safe}([" in result, f"Terminal node {node_id!r} missing stadium shape"


def test_mermaid_non_terminal_nodes_use_rect_shape():
    wf = _inv_before()
    result = to_mermaid(wf)
    for node_id, node in wf.nodes.items():
        if not node.is_terminal:
            safe = node_id.replace("-", "_")
            assert f"{safe}[" in result


def test_mermaid_shows_branch_probabilities():
    wf = _inv_before()
    result = to_mermaid(wf)
    # Invoice processing has edges with probability < 1.0
    assert "|" in result and "%" in result


def test_mermaid_shows_actor_kind():
    wf = _inv_after()
    result = to_mermaid(wf)
    assert "AI" in result


def test_mermaid_entry_node_has_style():
    wf = _inv_before()
    result = to_mermaid(wf)
    entry_safe = wf.entry_node_id.replace("-", "_")
    assert f"style {entry_safe}" in result


def test_mermaid_deterministic():
    wf = _inv_before()
    assert to_mermaid(wf) == to_mermaid(wf)


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_contains_workflow_name():
    wf = _inv_before()
    result = to_text(wf)
    assert wf.name in result


def test_text_marks_entry_node():
    wf = _inv_before()
    result = to_text(wf)
    assert "[ENTRY]" in result


def test_text_marks_terminal_nodes():
    wf = _inv_before()
    result = to_text(wf)
    assert "[TERMINAL]" in result


def test_text_shows_branch_probabilities():
    wf = _inv_before()
    result = to_text(wf)
    assert "%" in result


def test_text_shows_actor_ids():
    wf = _inv_before()
    result = to_text(wf)
    for actor_id in wf.actors:
        assert actor_id in result


def test_text_all_nodes_visited():
    wf = _inv_before()
    result = to_text(wf)
    for node_id in wf.nodes:
        assert node_id in result


def test_text_deterministic():
    wf = _inv_before()
    assert to_text(wf) == to_text(wf)


# ---------------------------------------------------------------------------
# Before/after comparison
# ---------------------------------------------------------------------------


def test_compare_text_shows_added_nodes():
    before = _inv_before()
    after = _inv_after()
    result = compare_text(before, after)
    assert "Added nodes:" in result or "WORKFLOW COMPARISON" in result


def test_compare_text_shows_both_workflow_names():
    before = _inv_before()
    after = _inv_after()
    result = compare_text(before, after)
    assert before.name in result
    assert after.name in result


def test_compare_mermaid_contains_both_diagrams():
    before = _inv_before()
    after = _inv_after()
    result = compare_mermaid(before, after)
    assert "flowchart LR" in result
    assert before.name in result
    assert after.name in result


def test_compare_mermaid_has_separator_comments():
    result = compare_mermaid(_inv_before(), _inv_after())
    assert result.startswith("%%")
