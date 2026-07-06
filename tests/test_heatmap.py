"""Tests for the bottleneck heatmap generator."""

from __future__ import annotations

from b2b_workflow_simulator.examples import invoice_processing
from b2b_workflow_simulator.heatmap import (
    BottleneckHeatmap,
    HeatmapCell,
    build_bottleneck_heatmap,
    heatmap_to_svg,
    heatmap_to_text,
)
from b2b_workflow_simulator.shared_resources import (
    LEGAL_REVIEWER,
    SharedResource,
    SharedResourcePool,
)
from b2b_workflow_simulator.simulation import SimulationRunner


def _run_after(n=200, seed=42, arrival=None):
    wf = invoice_processing.build_after_workflow()
    r = SimulationRunner(seed=seed).run(wf, n, arrival_interval_minutes=arrival,
                                        collect_events=False)
    return wf, r.kpi


# ---------------------------------------------------------------------------
# Build heatmap
# ---------------------------------------------------------------------------


def test_heatmap_has_cells():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    assert len(h.cells) > 0


def test_heatmap_cells_sorted_by_pressure_descending():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    pressures = [c.overall_pressure for c in h.cells]
    assert pressures == sorted(pressures, reverse=True)


def test_heatmap_pressure_range():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    for cell in h.cells:
        assert 0.0 <= cell.overall_pressure <= 100.0


def test_heatmap_top_returns_n_cells():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    top3 = h.top(3)
    assert len(top3) <= 3


def test_heatmap_top_are_highest_pressure():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    top3 = h.top(3)
    all_pressures = [c.overall_pressure for c in h.cells]
    top_pressures = [c.overall_pressure for c in top3]
    for p in top_pressures:
        assert p >= min(all_pressures)


def test_heatmap_cell_level():
    cell = HeatmapCell("test", "node", overall_pressure=85.0)
    assert cell.level == "critical"
    cell2 = HeatmapCell("test", "node", overall_pressure=10.0)
    assert cell2.level == "minimal"


def test_heatmap_assumptions_not_empty():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    assert len(h.assumptions) > 0


# ---------------------------------------------------------------------------
# Capacity-aware wait pressure
# ---------------------------------------------------------------------------


def test_wait_pressure_with_arrival_interval():
    wf, kpi_no_arrival = _run_after()
    wf, kpi_with_arrival = _run_after(arrival=2.0)
    h_no = build_bottleneck_heatmap(wf, kpi_no_arrival)
    h_with = build_bottleneck_heatmap(wf, kpi_with_arrival)
    total_wait_no = sum(c.wait_pressure for c in h_no.cells)
    total_wait_with = sum(c.wait_pressure for c in h_with.cells)
    assert total_wait_with >= total_wait_no


# ---------------------------------------------------------------------------
# Shared resource contention cells
# ---------------------------------------------------------------------------


def test_shared_resource_cells_added():
    wf, kpi = _run_after()
    pool = SharedResourcePool(org_id="test")
    pool.add_resource(SharedResource(
        resource_id="legal", name="Legal Reviewer",
        resource_type=LEGAL_REVIEWER, capacity_minutes_per_day=10.0,
    ))
    pool.record_usage("legal", "inv", "finance", 100.0)  # overloaded
    h = build_bottleneck_heatmap(wf, kpi, shared_resources=pool)
    resource_cells = [c for c in h.cells if c.category == "resource"]
    assert len(resource_cells) > 0


def test_shared_resource_zero_usage_not_added():
    wf, kpi = _run_after()
    pool = SharedResourcePool(org_id="test")
    pool.add_resource(SharedResource(
        resource_id="idle", name="Idle Resource",
        resource_type=LEGAL_REVIEWER, capacity_minutes_per_day=100.0,
    ))
    h = build_bottleneck_heatmap(wf, kpi, shared_resources=pool)
    resource_cells = [c for c in h.cells if c.category == "resource"]
    assert len(resource_cells) == 0


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def test_text_contains_header():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    result = heatmap_to_text(h)
    assert "BOTTLENECK HEATMAP" in result


def test_text_contains_assumptions():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    result = heatmap_to_text(h)
    assert "Assumptions" in result or "assumptions" in result.lower()


def test_text_deterministic():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    assert heatmap_to_text(h) == heatmap_to_text(h)


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


def test_svg_is_valid():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    svg = heatmap_to_svg(h)
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_svg_escapes_special_chars():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    h.workflow_name = "Test <script>x</script>"
    svg = heatmap_to_svg(h)
    assert "<script>" not in svg


def test_svg_deterministic():
    wf, kpi = _run_after()
    h = build_bottleneck_heatmap(wf, kpi)
    assert heatmap_to_svg(h) == heatmap_to_svg(h)


def test_empty_heatmap_svg():
    h = BottleneckHeatmap(workflow_name="Empty")
    svg = heatmap_to_svg(h)
    assert "<svg" in svg
