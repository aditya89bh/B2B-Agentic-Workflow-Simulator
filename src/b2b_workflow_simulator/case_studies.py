"""Case study output generator: build a full deliverable directory for every scenario.

``generate_case_study`` creates a structured directory for one scenario
containing executive snapshots, ROI waterfalls, Mermaid diagrams, KPI
JSON, assumption files, and consultant packet subdirectories for all
three assumption profiles (base, conservative, aggressive).

``generate_all_case_studies`` iterates over every registered scenario.

No external dependencies — all output is plain text, JSON, SVG, or Mermaid.
"""

from __future__ import annotations

import json
from pathlib import Path

from b2b_workflow_simulator.assumptions import apply_profile_to_workflow
from b2b_workflow_simulator.heatmap import build_bottleneck_heatmap, heatmap_to_svg
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.packet import generate_packet
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.scenarios import ScenarioDefinition, list_scenarios
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.snapshot import build_snapshot, snapshot_to_text
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


def _run_scenario_profile(scenario: ScenarioDefinition, profile_name: str):
    """Run before/after for one scenario/profile.

    Returns ``(before_wf, after_wf, before_result, after_result, profile)``.
    Both ``SimulationResult`` objects are returned (not just kpi) so callers
    that need the full result (e.g. for consultant packet generation) can use
    them directly.
    """
    profiles = {
        "base": scenario.default_assumption_profile,
        "conservative": scenario.conservative_assumption_profile,
        "aggressive": scenario.aggressive_assumption_profile,
    }
    profile = profiles[profile_name]
    before_wf = apply_profile_to_workflow(scenario.before_builder(), profile)
    after_wf = apply_profile_to_workflow(scenario.after_builder(), profile)
    runner = SimulationRunner(seed=profile.seed)
    before_r = runner.run(before_wf, profile.num_cases, collect_events=False)
    after_r = SimulationRunner(seed=profile.seed).run(
        after_wf, profile.num_cases, collect_events=False
    )
    return before_wf, after_wf, before_r, after_r, profile


def _build_scenario_readme(
    scenario: ScenarioDefinition, base_kpi_before: KPIResult, base_kpi_after: KPIResult
) -> str:
    diff = compare_workflows(base_kpi_before, base_kpi_after,
                             scenario.default_assumption_profile.implementation_cost)
    cur = scenario.default_assumption_profile.currency_label
    lines = [
        f"# Case Study: {scenario.name}",
        "",
        f"**Category:** {CATEGORY_LABELS.get(scenario.category, scenario.category)}",
        f"**Target users:** {scenario.target_users}",
        "",
        "## Overview",
        "",
        scenario.description,
        "",
        "## What the simulation suggests",
        "",
        f"- Total cost savings: {cur}{diff.roi.total_cost_savings:,.2f}",
        f"- Completion rate: {base_kpi_before.completion_rate:.1%} → {base_kpi_after.completion_rate:.1%}",  # noqa: E501
        f"- Average cycle time: {base_kpi_before.avg_cycle_time_minutes:.1f} min → {base_kpi_after.avg_cycle_time_minutes:.1f} min",  # noqa: E501
        f"- AI escalation rate in after variant: {base_kpi_after.escalation_rate:.1%}",
        "",
        "## Key assumptions",
        "",
        f"Base profile: {scenario.default_assumption_profile.description}",
        f"Cases simulated: {scenario.default_assumption_profile.num_cases}",
        "",
        "## What must be validated with real data",
        "",
        *[f"- {lim}" for lim in scenario.limitations],
        "",
        "## When this scenario is useful",
        "",
        f"- Presenting AI transformation ROI for {scenario.target_users}",
        "- Stress-testing assumptions before committing to implementation",
        "- Comparing this scenario against others in the scenario matrix",
        "",
        "## When not to use this scenario",
        "",
        "- When your process differs substantially from the modeled workflow structure",
        "- Without calibrating durations, error rates, and costs to your real data",
        "- As a substitute for operational measurement or process mining",
        "",
        "## Files in this case study",
        "",
        "| File | Description |",
        "|---|---|",
        "| `executive_snapshot_base.txt` | One-page summary (base profile) |",
        "| `executive_snapshot_conservative.txt` | One-page summary (conservative profile) |",
        "| `executive_snapshot_aggressive.txt` | One-page summary (aggressive profile) |",
        "| `roi_waterfall_base.svg` | ROI decomposition (base profile) |",
        "| `bottleneck_heatmap_base.svg` | Node pressure heatmap (base profile) |",
        "| `workflow_before.mmd` | Mermaid flowchart — before |",
        "| `workflow_after.mmd` | Mermaid flowchart — after |",
        "| `assumptions_base.json` | Base profile parameters |",
        "| `assumptions_conservative.json` | Conservative profile parameters |",
        "| `assumptions_aggressive.json` | Aggressive profile parameters |",
        "| `kpi_summary_base.json` | Structured KPI output (base) |",
        "| `kpi_summary_conservative.json` | Structured KPI output (conservative) |",
        "| `kpi_summary_aggressive.json` | Structured KPI output (aggressive) |",
        "| `consultant_packet_base/` | Complete consultant packet (base profile) |",
        "| `consultant_packet_conservative/` | Complete consultant packet (conservative profile) |",
        "| `consultant_packet_aggressive/` | Complete consultant packet (aggressive profile) |",
        "",
        "## Commands to reproduce",
        "",
        *[f"```bash\n{cmd}\n```" for cmd in scenario.recommended_commands],
        "",
        "---",
        "",
        "*All figures are directional simulation estimates.*",
        "*Validate assumptions with real operational data before using in stakeholder decisions.*",
    ]
    return "\n".join(lines)


from b2b_workflow_simulator.scenarios import CATEGORY_LABELS  # noqa: E402


def generate_case_study(
    scenario: ScenarioDefinition,
    output_dir: Path,
    profiles: list[str] | None = None,
) -> dict[str, Path]:
    """Generate all case study files for ``scenario`` in ``output_dir``.

    For each requested profile this creates:

    - ``executive_snapshot_<profile>.txt``
    - ``assumptions_<profile>.json``
    - ``kpi_summary_<profile>.json``
    - ``consultant_packet_<profile>/`` — a complete consultant packet directory

    Plus these files shared across profiles (using the base profile):

    - ``README.md``
    - ``workflow_before.mmd``, ``workflow_after.mmd``
    - ``roi_waterfall_base.svg``, ``bottleneck_heatmap_base.svg``

    Args:
        scenario: The scenario definition to generate outputs for.
        output_dir: Target directory (created if absent).
        profiles: Which profiles to include.  Defaults to
            ``["base", "conservative", "aggressive"]``.

    Returns:
        Dict mapping filename/dirname → Path for every artifact written.
    """
    if profiles is None:
        profiles = ["base", "conservative", "aggressive"]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}

    def write(filename: str, content: str) -> Path:
        p = output_dir / filename
        p.write_text(content)
        files[filename] = p
        return p

    base_bwf, base_awf, base_before_r, base_after_r, base_profile = (
        _run_scenario_profile(scenario, "base")
    )
    base_bkpi = base_before_r.kpi
    base_akpi = base_after_r.kpi

    write("workflow_before.mmd", to_mermaid(base_bwf))
    write("workflow_after.mmd", to_mermaid(base_awf))

    waterfall = build_roi_waterfall(
        base_bkpi, base_akpi,
        implementation_cost=base_profile.implementation_cost,
        currency=base_profile.currency_label,
    )
    write("roi_waterfall_base.svg", waterfall_to_svg(waterfall))

    heatmap = build_bottleneck_heatmap(base_awf, base_akpi)
    write("bottleneck_heatmap_base.svg", heatmap_to_svg(heatmap))

    write("README.md", _build_scenario_readme(scenario, base_bkpi, base_akpi))

    for profile_name in profiles:
        bwf, awf, before_r, after_r, profile = _run_scenario_profile(scenario, profile_name)
        bkpi, akpi = before_r.kpi, after_r.kpi

        snap = build_snapshot(bkpi, akpi, implementation_cost=profile.implementation_cost)
        write(f"executive_snapshot_{profile_name}.txt", snapshot_to_text(snap))
        write(
            f"assumptions_{profile_name}.json",
            json.dumps(profile.to_dict(), indent=2) + "\n",
        )
        write(
            f"kpi_summary_{profile_name}.json",
            json.dumps(
                {"before": _kpi_to_dict(bkpi), "after": _kpi_to_dict(akpi)}, indent=2
            ) + "\n",
        )

        packet_dir = output_dir / f"consultant_packet_{profile_name}"
        generate_packet(
            scenario.slug,
            bwf, awf,
            before_r, after_r,
            profile,
            packet_dir,
        )
        files[f"consultant_packet_{profile_name}"] = packet_dir

    return files


def generate_all_case_studies(
    output_dir: Path,
    scenario_slugs: list[str] | None = None,
    profiles: list[str] | None = None,
) -> dict[str, dict[str, Path]]:
    """Generate case studies for all (or selected) scenarios.

    Args:
        output_dir: Root directory; one subdirectory per scenario.
        scenario_slugs: Optional list of slugs to generate.  Defaults to
            all registered scenarios.
        profiles: Which profiles to include per scenario.

    Returns:
        Dict mapping scenario slug → per-scenario file dict.
    """
    scenarios = list_scenarios()
    if scenario_slugs:
        scenarios = [s for s in scenarios if s.slug in scenario_slugs]

    results: dict[str, dict[str, Path]] = {}
    for scenario in scenarios:
        scenario_dir = Path(output_dir) / scenario.slug
        results[scenario.slug] = generate_case_study(scenario, scenario_dir, profiles)
    return results


__all__ = [
    "generate_all_case_studies",
    "generate_case_study",
]
