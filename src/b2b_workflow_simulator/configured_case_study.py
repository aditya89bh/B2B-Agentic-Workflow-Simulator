"""Configured scenario case-study export: client-specific deliverable directory.

``generate_configured_case_study`` builds a full output directory from a
:class:`~b2b_workflow_simulator.scenario_config.ScenarioConfig`, including all
the standard case-study artifacts plus the config itself, a config diff, and
a client-specific README.

All outputs clearly state they are based on user-provided calibrated
assumptions, not validated truth.

No external dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path

from b2b_workflow_simulator.config_diff import (
    build_config_diff,
    config_diff_to_json,
    config_diff_to_text,
)
from b2b_workflow_simulator.heatmap import build_bottleneck_heatmap, heatmap_to_svg
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.scenario_config import ScenarioConfig, apply_scenario_config
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.snapshot import build_snapshot, snapshot_to_html, snapshot_to_text
from b2b_workflow_simulator.visualization import to_mermaid
from b2b_workflow_simulator.waterfall import build_roi_waterfall, waterfall_to_svg


def _kpi_to_dict(kpi: KPIResult) -> dict:
    return {
        "workflow_name": kpi.workflow_name,
        "total_cases": kpi.total_cases,
        "completed_cases": kpi.completed_cases,
        "failed_cases": kpi.failed_cases,
        "completion_rate": round(kpi.completion_rate, 4),
        "failure_rate": round(kpi.failure_rate, 4),
        "total_cost": round(kpi.total_cost, 4),
        "avg_cost_per_case": round(kpi.avg_cost_per_case, 4),
        "avg_cycle_time_minutes": round(kpi.avg_cycle_time_minutes, 4),
        "avg_wait_time_minutes": round(kpi.avg_wait_time_minutes, 4),
        "escalation_rate": round(kpi.escalation_rate, 4),
    }


def configured_case_study_readme(
    config: ScenarioConfig,
    diff,
    before_kpi: KPIResult,
    after_kpi: KPIResult,
) -> str:
    """Build the README.md for a configured case study.

    Args:
        config: The :class:`~b2b_workflow_simulator.scenario_config.ScenarioConfig`.
        diff: A :class:`~b2b_workflow_simulator.config_diff.ConfigDiff`.
        before_kpi: KPI from the configured "before" workflow.
        after_kpi: KPI from the configured "after" workflow.

    Returns:
        Markdown string.
    """
    from b2b_workflow_simulator.scenarios import CATEGORY_LABELS, get_scenario
    scenario = get_scenario(config.base_scenario_slug)
    d = compare_workflows(before_kpi, after_kpi, None)
    cur = "$"
    lines = [
        f"# Configured Case Study: {config.configured_name}",
        "",
        f"**Client:** {config.client_name or '(not specified)'}",
        f"**Base scenario:** {scenario.name} (`{config.base_scenario_slug}`)",
        f"**Category:** {CATEGORY_LABELS.get(scenario.category, scenario.category)}",
        f"**Profile:** {config.profile_name}",
        f"**Created by:** {config.created_by or '(not specified)'}",
        f"**Config version:** {config.version}",
        "",
        "## Overview",
        "",
        config.description or scenario.description,
        "",
        "## Base scenario used",
        "",
        f"{scenario.name} — {scenario.description}",
        f"Target users: {scenario.target_users}",
        "",
        "## What was customized",
        "",
        f"- Actor overrides: {len(config.actor_overrides)} actor(s) modified",
        f"- Node overrides: {len(config.node_overrides)} node(s) modified",
        f"- Edge overrides: {len(config.edge_overrides)} edge(s) modified",
    ]
    if diff.has_high_risk_changes:
        lines.append("- ⚠ **High-risk assumption changes present** (see config_diff.txt)")
    lines += [
        "",
        "## Before vs after result summary (configured)",
        "",
        f"- Completion rate: {before_kpi.completion_rate:.1%} → {after_kpi.completion_rate:.1%}",
        f"- Avg cost per case: {cur}{before_kpi.avg_cost_per_case:,.2f} → {cur}{after_kpi.avg_cost_per_case:,.2f}",  # noqa: E501
        f"- Total cost savings: {cur}{d.roi.total_cost_savings:,.2f}",
        f"- Avg cycle time: {before_kpi.avg_cycle_time_minutes:.1f} min → {after_kpi.avg_cycle_time_minutes:.1f} min",  # noqa: E501
        "",
        "## Key assumptions",
        "",
        f"- Profile: {config.profile_name}",
        f"- Cases simulated: {before_kpi.total_cases}",
    ]
    if config.notes:
        lines += ["", "## Notes", "", config.notes]
    lines += [
        "",
        "## What changed from the base scenario",
        "",
        "See `config_diff.txt` for a full breakdown of overridden parameters.",
        "",
        "## What must be validated with real data",
        "",
        *[f"- {lim}" for lim in (config.limitations or scenario.limitations)],
        "",
        "## When not to rely on this output",
        "",
        "- When input data quality is poor (garbage in, garbage out).",
        "- Without having your process owner validate the stage durations and error rates.",
        "- As a substitute for pilot measurement or process mining.",
        "- When regulatory requirements are not yet fully understood.",
        "",
        "## Files in this case study",
        "",
        "| File | Description |",
        "|---|---|",
        "| `executive_snapshot.txt` | One-page stakeholder summary |",
        "| `executive_snapshot.html` | Same summary as HTML |",
        "| `workflow_before.mmd` | Mermaid flowchart (before, with overrides) |",
        "| `workflow_after.mmd` | Mermaid flowchart (after, with overrides) |",
        "| `roi_waterfall.svg` | ROI decomposition chart |",
        "| `bottleneck_heatmap.svg` | Node pressure heatmap |",
        "| `assumptions.json` | Assumption profile parameters |",
        "| `config.json` | Full ScenarioConfig (all overrides) |",
        "| `config_diff.txt` | What changed from the base scenario |",
        "| `config_diff.json` | Same diff as machine-readable JSON |",
        "| `kpi_summary.json` | Structured KPI output |",
        "| `recommendations.txt` | Plain-text recommendations |",
        "",
        "## Commands to reproduce",
        "",
        "```bash",
        f"b2b-simulator run-config path/to/{config.configured_slug}.json",
        f"b2b-simulator config-snapshot path/to/{config.configured_slug}.json",
        f"b2b-simulator config-case-study path/to/{config.configured_slug}.json --output-dir case_study/",  # noqa: E501
        "```",
        "",
        "---",
        "",
        "*This case study is based on user-provided calibrated assumptions.*",
        "*All figures are directional estimates — validate with real operational data*",
        "*before making investment decisions.*",
    ]
    return "\n".join(lines)


def generate_configured_case_study(
    config: ScenarioConfig,
    output_dir: Path,
    scenario=None,
) -> dict[str, Path]:
    """Generate a client-specific case study directory from a ``ScenarioConfig``.

    Args:
        config: The scenario configuration to use.
        output_dir: Target directory (created if absent).
        scenario: Optional pre-loaded scenario definition.

    Returns:
        Dict mapping filename → Path for every file written.
    """
    from b2b_workflow_simulator.scenarios import get_scenario

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}

    if scenario is None:
        scenario = get_scenario(config.base_scenario_slug)

    def write(filename: str, content: str) -> Path:
        p = output_dir / filename
        p.write_text(content)
        files[filename] = p
        return p

    # Apply config to get configured workflows
    before_wf, after_wf = apply_scenario_config(config, scenario)

    # Get profile for simulation parameters
    profiles = {
        "base": scenario.default_assumption_profile,
        "conservative": scenario.conservative_assumption_profile,
        "aggressive": scenario.aggressive_assumption_profile,
    }
    profile = profiles[config.profile_name]

    # Run simulations
    before_r = SimulationRunner(seed=profile.seed).run(
        before_wf, profile.num_cases, collect_events=False
    )
    after_r = SimulationRunner(seed=profile.seed).run(
        after_wf, profile.num_cases, collect_events=False
    )
    before_kpi = before_r.kpi
    after_kpi = after_r.kpi

    # Build diff
    diff = build_config_diff(config, scenario)

    # Mermaid diagrams
    write("workflow_before.mmd", to_mermaid(before_wf))
    write("workflow_after.mmd", to_mermaid(after_wf))

    # ROI waterfall
    waterfall = build_roi_waterfall(
        before_kpi, after_kpi,
        implementation_cost=profile.implementation_cost,
        currency=profile.currency_label,
    )
    write("roi_waterfall.svg", waterfall_to_svg(waterfall))

    # Bottleneck heatmap
    heatmap = build_bottleneck_heatmap(after_wf, after_kpi)
    write("bottleneck_heatmap.svg", heatmap_to_svg(heatmap))

    # Executive snapshot
    snap = build_snapshot(before_kpi, after_kpi, implementation_cost=profile.implementation_cost)
    write("executive_snapshot.txt", snapshot_to_text(snap))
    write("executive_snapshot.html", snapshot_to_html(snap))

    # Assumptions + config
    write("assumptions.json", json.dumps(profile.to_dict(), indent=2) + "\n")
    write("config.json", json.dumps(config.to_dict(), indent=2) + "\n")

    # Config diff
    write("config_diff.txt", config_diff_to_text(diff))
    write("config_diff.json", config_diff_to_json(diff))

    # KPI summary
    write(
        "kpi_summary.json",
        json.dumps(
            {"before": _kpi_to_dict(before_kpi), "after": _kpi_to_dict(after_kpi)}, indent=2
        ) + "\n",
    )

    # Recommendations
    from b2b_workflow_simulator.packet import _build_recommendations_txt
    write("recommendations.txt", _build_recommendations_txt(before_kpi, after_kpi))

    # README
    write("README.md", configured_case_study_readme(config, diff, before_kpi, after_kpi))

    return files


__all__ = [
    "configured_case_study_readme",
    "generate_configured_case_study",
]
