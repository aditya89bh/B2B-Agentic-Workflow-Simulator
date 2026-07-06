"""Tests for the ROI waterfall generator."""

from __future__ import annotations

from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.waterfall import (
    build_roi_waterfall,
    waterfall_to_svg,
    waterfall_to_text,
)


def _run_pair(wf_before, wf_after, n=200, seed=42):
    r1 = SimulationRunner(seed=seed).run(wf_before, n, collect_events=False)
    r2 = SimulationRunner(seed=seed).run(wf_after, n, collect_events=False)
    return r1.kpi, r2.kpi


def _inv_kpis():
    return _run_pair(
        invoice_processing.build_before_workflow(),
        invoice_processing.build_after_workflow(),
    )


def _slq_kpis():
    return _run_pair(
        sales_lead_qualification.build_before_workflow(),
        sales_lead_qualification.build_after_workflow(),
    )


# ---------------------------------------------------------------------------
# Build waterfall
# ---------------------------------------------------------------------------


def test_waterfall_has_bars():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    assert len(w.bars) > 0


def test_waterfall_has_baseline_bar():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    labels = [b.label for b in w.bars]
    assert any("baseline" in lbl.lower() or "cost" in lbl.lower() for lbl in labels)


def test_waterfall_net_savings_computable():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    assert isinstance(w.net_savings, float)


def test_waterfall_positive_roi_for_ai_after():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after, implementation_cost=0)
    assert w.is_positive_roi


def test_waterfall_implementation_cost_creates_bar():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after, implementation_cost=5000.0)
    labels = [b.label.lower() for b in w.bars]
    assert any("implementation" in label for label in labels)


def test_waterfall_no_implementation_cost_no_impl_cost_bar():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after, implementation_cost=None)
    labels = [b.label.lower() for b in w.bars]
    assert not any("implementation cost" in lbl for lbl in labels)


def test_waterfall_assumptions_not_empty():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    assert len(w.assumptions) > 0


def test_waterfall_currency_label():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after, currency="€")
    assert w.currency == "€"


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_contains_header():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    result = waterfall_to_text(w)
    assert "ROI WATERFALL" in result


def test_text_contains_assumptions():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    result = waterfall_to_text(w)
    assert "Assumptions" in result or "assumptions" in result.lower()


def test_text_deterministic():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after, implementation_cost=5000.0)
    assert waterfall_to_text(w) == waterfall_to_text(w)


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


def test_svg_is_valid_svg():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    svg = waterfall_to_svg(w)
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")


def test_svg_contains_title():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    svg = waterfall_to_svg(w)
    assert w.workflow_name[:10] in svg


def test_svg_escapes_special_chars():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    w.workflow_name = "Test <script>alert(1)</script>"
    svg = waterfall_to_svg(w)
    assert "<script>" not in svg


def test_svg_deterministic():
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after)
    assert waterfall_to_svg(w) == waterfall_to_svg(w)


# ---------------------------------------------------------------------------
# Negative ROI case
# ---------------------------------------------------------------------------


def test_negative_roi_waterfall():
    """A waterfall where implementation cost exceeds savings should show negative ROI."""
    before, after = _inv_kpis()
    w = build_roi_waterfall(before, after, implementation_cost=1_000_000.0)
    assert not w.is_positive_roi
    text = waterfall_to_text(w)
    assert "-" in text
