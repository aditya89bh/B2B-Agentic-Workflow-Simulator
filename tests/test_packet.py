"""Tests for the consultant packet export."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.examples import invoice_processing
from b2b_workflow_simulator.packet import generate_packet
from b2b_workflow_simulator.simulation import SimulationRunner


def _make_packet(tmpdir, profile=None):
    if profile is None:
        profile = AssumptionProfile(num_cases=100, seed=42, implementation_cost=5000.0)
    before_wf = invoice_processing.build_before_workflow()
    after_wf = invoice_processing.build_after_workflow()
    before_r = SimulationRunner(seed=profile.seed).run(
        before_wf, profile.num_cases, collect_events=False
    )
    after_r = SimulationRunner(seed=profile.seed).run(
        after_wf, profile.num_cases, collect_events=False
    )
    dest = Path(tmpdir)
    files = generate_packet(
        "invoice-processing", before_wf, after_wf, before_r, after_r, profile, dest
    )
    return dest, files


_EXPECTED_FILES = {
    "README.md", "executive_snapshot.txt", "executive_snapshot.html",
    "workflow_before.mmd", "workflow_after.mmd", "roi_waterfall.svg",
    "bottleneck_heatmap.svg", "assumptions.json", "kpi_summary.json",
    "recommendations.txt",
}


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_packet_creates_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, _ = _make_packet(tmpdir + "/newdir")
        assert dest.is_dir()


def test_packet_creates_all_expected_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, files = _make_packet(tmpdir)
        created = {f.name for f in dest.iterdir()}
        assert _EXPECTED_FILES == created


def test_packet_returns_file_mapping():
    with tempfile.TemporaryDirectory() as tmpdir:
        _, files = _make_packet(tmpdir)
        for filename in _EXPECTED_FILES:
            assert filename in files
            assert files[filename].exists()


# ---------------------------------------------------------------------------
# Content validity
# ---------------------------------------------------------------------------


def test_assumptions_json_is_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, _ = _make_packet(tmpdir)
        data = json.loads((dest / "assumptions.json").read_text())
    assert "num_cases" in data
    assert "seed" in data


def test_kpi_summary_json_is_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, _ = _make_packet(tmpdir)
        data = json.loads((dest / "kpi_summary.json").read_text())
    assert "before" in data and "after" in data
    assert "completion_rate" in data["before"]


def test_mermaid_files_start_with_flowchart():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, _ = _make_packet(tmpdir)
        for fname in ("workflow_before.mmd", "workflow_after.mmd"):
            content = (dest / fname).read_text()
            assert content.startswith("flowchart LR"), fname


def test_svg_files_are_valid_svg():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, _ = _make_packet(tmpdir)
        for fname in ("roi_waterfall.svg", "bottleneck_heatmap.svg"):
            content = (dest / fname).read_text()
            assert "<svg" in content and "</svg>" in content, fname


def test_readme_mentions_key_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, _ = _make_packet(tmpdir)
        readme = (dest / "README.md").read_text()
    for filename in _EXPECTED_FILES - {"README.md"}:
        assert filename in readme, f"{filename!r} not mentioned in README.md"


def test_snapshot_html_is_html():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, _ = _make_packet(tmpdir)
        html = (dest / "executive_snapshot.html").read_text()
    assert "<!DOCTYPE html>" in html


# ---------------------------------------------------------------------------
# File name safety (no path traversal)
# ---------------------------------------------------------------------------


def test_no_unsafe_filenames():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest, files = _make_packet(tmpdir)
        for filename in files:
            assert "/" not in filename
            assert "\\" not in filename
            assert ".." not in filename


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


def test_packet_is_reproducible():
    """Same seed should produce identical kpi_summary.json."""
    profile = AssumptionProfile(num_cases=100, seed=7)
    with tempfile.TemporaryDirectory() as d1:
        with tempfile.TemporaryDirectory() as d2:
            _make_packet(d1, profile)
            _make_packet(d2, profile)
            data1 = json.loads((Path(d1) / "kpi_summary.json").read_text())
            data2 = json.loads((Path(d2) / "kpi_summary.json").read_text())
    assert data1["before"]["completed_cases"] == data2["before"]["completed_cases"]
    assert data1["after"]["completed_cases"] == data2["after"]["completed_cases"]
