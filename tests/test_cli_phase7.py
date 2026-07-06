"""Tests for Phase 7 CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from b2b_workflow_simulator.cli import main

# ---------------------------------------------------------------------------
# visualize-workflow
# ---------------------------------------------------------------------------


def test_visualize_mermaid_exits_zero():
    assert main(["visualize-workflow", "invoice-processing"]) == 0


def test_visualize_text_exits_zero():
    assert main(["visualize-workflow", "invoice-processing", "--format", "text"]) == 0


def test_visualize_before_variant():
    assert main(["visualize-workflow", "invoice-processing", "--variant", "before"]) == 0


def test_visualize_after_variant():
    assert main(["visualize-workflow", "invoice-processing", "--variant", "after"]) == 0


def test_visualize_output_file(tmp_path):
    out = str(tmp_path / "wf.mmd")
    ret = main(["visualize-workflow", "invoice-processing", "--output", out])
    assert ret == 0
    content = Path(out).read_text()
    assert "flowchart LR" in content


def test_visualize_text_output_file(tmp_path):
    out = str(tmp_path / "wf.txt")
    ret = main(["visualize-workflow", "invoice-processing", "--format", "text", "--output", out])
    assert ret == 0
    assert "[ENTRY]" in Path(out).read_text()


# ---------------------------------------------------------------------------
# roi-waterfall
# ---------------------------------------------------------------------------


def test_roi_waterfall_text_exits_zero():
    assert main(["roi-waterfall", "invoice-processing", "--cases", "50"]) == 0


def test_roi_waterfall_svg_output(tmp_path):
    out = str(tmp_path / "roi.svg")
    ret = main(["roi-waterfall", "invoice-processing", "--cases", "50",
                "--format", "svg", "--output", out])
    assert ret == 0
    content = Path(out).read_text()
    assert "<svg" in content


def test_roi_waterfall_with_implementation_cost(capsys):
    main(["roi-waterfall", "invoice-processing", "--cases", "50",
          "--implementation-cost", "5000"])
    out = capsys.readouterr().out
    assert "5,000" in out


# ---------------------------------------------------------------------------
# bottleneck-heatmap
# ---------------------------------------------------------------------------


def test_bottleneck_heatmap_text_exits_zero():
    assert main(["bottleneck-heatmap", "invoice-processing", "--cases", "50"]) == 0


def test_bottleneck_heatmap_svg_output(tmp_path):
    out = str(tmp_path / "heatmap.svg")
    ret = main(["bottleneck-heatmap", "invoice-processing", "--cases", "50",
                "--format", "svg", "--output", out])
    assert ret == 0
    assert "<svg" in Path(out).read_text()


def test_bottleneck_heatmap_before_variant():
    assert main(["bottleneck-heatmap", "invoice-processing", "--variant", "before",
                 "--cases", "50"]) == 0


# ---------------------------------------------------------------------------
# executive-snapshot
# ---------------------------------------------------------------------------


def test_executive_snapshot_exits_zero():
    assert main(["executive-snapshot", "invoice-processing", "--cases", "50"]) == 0


def test_executive_snapshot_contains_decision(capsys):
    main(["executive-snapshot", "invoice-processing", "--cases", "50"])
    out = capsys.readouterr().out
    assert "DECISION" in out


def test_executive_snapshot_html_output(tmp_path):
    out = str(tmp_path / "snap.html")
    ret = main(["executive-snapshot", "invoice-processing", "--cases", "50",
                "--html-output", out])
    assert ret == 0
    assert "<!DOCTYPE html>" in Path(out).read_text()


def test_executive_snapshot_with_implementation_cost(capsys):
    main(["executive-snapshot", "invoice-processing", "--cases", "50",
          "--implementation-cost", "8000"])
    out = capsys.readouterr().out
    assert "8,000" in out


def test_executive_snapshot_all_three_examples():
    for name in ["sales-lead-qualification", "invoice-processing",
                 "customer-support-ticket-resolution"]:
        assert main(["executive-snapshot", name, "--cases", "30"]) == 0


# ---------------------------------------------------------------------------
# consultant-packet
# ---------------------------------------------------------------------------


def test_consultant_packet_exits_zero(tmp_path):
    ret = main(["consultant-packet", "invoice-processing", "--cases", "50",
                "--output-dir", str(tmp_path)])
    assert ret == 0


def test_consultant_packet_creates_all_files(tmp_path):
    main(["consultant-packet", "invoice-processing", "--cases", "50",
          "--output-dir", str(tmp_path)])
    files = {f.name for f in tmp_path.iterdir()}
    assert "executive_snapshot.txt" in files
    assert "roi_waterfall.svg" in files
    assert "assumptions.json" in files
    assert "kpi_summary.json" in files
    assert "README.md" in files


def test_consultant_packet_valid_json_files(tmp_path):
    main(["consultant-packet", "invoice-processing", "--cases", "50",
          "--output-dir", str(tmp_path)])
    for jf in ["assumptions.json", "kpi_summary.json"]:
        data = json.loads((tmp_path / jf).read_text())
        assert isinstance(data, dict)


def test_consultant_packet_html_no_xss(tmp_path):
    main(["consultant-packet", "invoice-processing", "--cases", "50",
          "--output-dir", str(tmp_path)])
    html = (tmp_path / "executive_snapshot.html").read_text()
    assert "<script>" not in html


# ---------------------------------------------------------------------------
# generate-example-gallery
# ---------------------------------------------------------------------------


def test_generate_gallery_exits_zero(tmp_path):
    assert main(["generate-example-gallery", "--output-dir", str(tmp_path)]) == 0


def test_generate_gallery_creates_snapshots(tmp_path):
    main(["generate-example-gallery", "--output-dir", str(tmp_path)])
    files = {f.name for f in tmp_path.iterdir()}
    assert "sales_lead_snapshot.txt" in files
    assert "invoice_processing_snapshot.txt" in files
    assert "customer_support_snapshot.txt" in files


def test_generate_gallery_creates_svgs(tmp_path):
    main(["generate-example-gallery", "--output-dir", str(tmp_path)])
    assert (tmp_path / "invoice_processing_roi_waterfall.svg").exists()
    assert (tmp_path / "invoice_processing_bottleneck_heatmap.svg").exists()


def test_generate_gallery_deterministic(tmp_path):
    """Two identical runs should produce the same output."""
    d1 = tmp_path / "run1"
    d2 = tmp_path / "run2"
    main(["generate-example-gallery", "--output-dir", str(d1)])
    main(["generate-example-gallery", "--output-dir", str(d2)])
    for fname in ["invoice_processing_snapshot.txt"]:
        assert (d1 / fname).read_text() == (d2 / fname).read_text()


# ---------------------------------------------------------------------------
# --assumptions flag
# ---------------------------------------------------------------------------


def test_assumptions_flag_roi_waterfall(tmp_path):
    from b2b_workflow_simulator.assumptions import AssumptionProfile, save_assumption_profile
    profile = AssumptionProfile(num_cases=50, seed=1)
    path = str(tmp_path / "profile.json")
    save_assumption_profile(profile, path)
    ret = main(["roi-waterfall", "invoice-processing", "--assumptions", path])
    assert ret == 0


def test_assumptions_flag_executive_snapshot(tmp_path):
    from b2b_workflow_simulator.assumptions import AssumptionProfile, save_assumption_profile
    profile = AssumptionProfile(num_cases=50, seed=7, implementation_cost=3000.0)
    path = str(tmp_path / "profile.json")
    save_assumption_profile(profile, path)
    ret = main(["executive-snapshot", "invoice-processing", "--assumptions", path])
    assert ret == 0
