"""Tests for the executive snapshot report."""

from __future__ import annotations

from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.snapshot import (
    build_snapshot,
    snapshot_to_html,
    snapshot_to_text,
)


def _run_pair(before_fn, after_fn, n=200, seed=42):
    r1 = SimulationRunner(seed=seed).run(before_fn(), n, collect_events=False)
    r2 = SimulationRunner(seed=seed).run(after_fn(), n, collect_events=False)
    return r1.kpi, r2.kpi


def _inv_kpis():
    return _run_pair(
        invoice_processing.build_before_workflow,
        invoice_processing.build_after_workflow,
    )


def _slq_kpis():
    return _run_pair(
        sales_lead_qualification.build_before_workflow,
        sales_lead_qualification.build_after_workflow,
    )


# ---------------------------------------------------------------------------
# Build snapshot
# ---------------------------------------------------------------------------


def test_snapshot_has_headline():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert isinstance(snap.headline, str)
    assert len(snap.headline) > 10


def test_snapshot_has_bottlenecks():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert isinstance(snap.top_bottlenecks, list)


def test_snapshot_has_risks():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert isinstance(snap.top_risks, list)
    assert len(snap.top_risks) > 0


def test_snapshot_has_recommendations():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert isinstance(snap.top_recommendations, list)
    assert len(snap.top_recommendations) > 0


def test_snapshot_has_assumptions():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert len(snap.assumptions) > 0


def test_snapshot_has_next_steps():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert len(snap.next_steps) > 0


def test_snapshot_diff_matches_kpis():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert snap.before_kpi is before
    assert snap.after_kpi is after


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_contains_decision_section():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "DECISION" in result


def test_text_contains_kpi_summary():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "KPI SUMMARY" in result


def test_text_contains_roi_summary():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after, implementation_cost=5000.0)
    result = snapshot_to_text(snap)
    assert "ROI SUMMARY" in result
    assert "5,000" in result


def test_text_contains_bottlenecks():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "BOTTLENECK" in result.upper()


def test_text_contains_risks():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "RISK" in result.upper()


def test_text_contains_recommendations():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "RECOMMENDATION" in result.upper()


def test_text_contains_assumptions():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "ASSUMPTIONS" in result.upper()


def test_text_contains_next_steps():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "VALIDATE" in result.upper()


def test_text_contains_before_after_metrics():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    result = snapshot_to_text(snap)
    assert "Before" in result and "After" in result


def test_text_deterministic():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after, implementation_cost=3000.0)
    assert snapshot_to_text(snap) == snapshot_to_text(snap)


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------


def test_html_is_valid_html():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    html = snapshot_to_html(snap)
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_html_contains_headline():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    html = snapshot_to_html(snap)
    assert "Decision" in html


def test_html_escapes_special_chars():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    snap.headline = "<script>alert('xss')</script>"
    html = snapshot_to_html(snap)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_html_contains_table():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    html = snapshot_to_html(snap)
    assert "<table>" in html


def test_html_deterministic():
    before, after = _inv_kpis()
    snap = build_snapshot(before, after)
    assert snapshot_to_html(snap) == snapshot_to_html(snap)


# ---------------------------------------------------------------------------
# Negative ROI case
# ---------------------------------------------------------------------------


def test_negative_roi_headline():
    """Very large implementation cost should produce a conditional/negative headline."""
    before, after = _inv_kpis()
    snap = build_snapshot(before, after, implementation_cost=10_000_000.0)
    assert isinstance(snap.headline, str)
    text = snapshot_to_text(snap)
    assert "10,000,000" in text or "not reached" in text
