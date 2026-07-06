"""Scenario comparison matrix: cross-scenario KPI table for consulting prioritization.

The scenario matrix runs every registered scenario under one assumption
profile and presents a side-by-side comparison of key KPIs so consultants
can quickly identify the highest-impact automation opportunities.

Output is a plain-text table or a JSON array, suitable for inclusion in
presentations or further analysis.

No external dependencies.
"""

from __future__ import annotations

import json

from b2b_workflow_simulator.assumptions import apply_profile_to_workflow
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.risk import compute_risk
from b2b_workflow_simulator.scenarios import CATEGORY_LABELS, ScenarioDefinition, list_scenarios
from b2b_workflow_simulator.simulation import SimulationRunner

_RISK_BUCKETS = ((60.0, "High"), (30.0, "Moderate"), (0.0, "Low"))


def _risk_label(score: float) -> str:
    for threshold, label in _RISK_BUCKETS:
        if score >= threshold:
            return label
    return "Low"


def _run_matrix_row(scenario: ScenarioDefinition, profile_name: str) -> dict:
    """Run one scenario under the named profile and return a result dict."""
    profiles = {
        "base": scenario.default_assumption_profile,
        "conservative": scenario.conservative_assumption_profile,
        "aggressive": scenario.aggressive_assumption_profile,
    }
    profile = profiles.get(profile_name, scenario.default_assumption_profile)
    seed = profile.seed
    n = profile.num_cases

    before_wf = apply_profile_to_workflow(scenario.before_builder(), profile)
    after_wf = apply_profile_to_workflow(scenario.after_builder(), profile)

    before_kpi = SimulationRunner(seed=seed).run(before_wf, n, collect_events=False).kpi
    after_kpi = SimulationRunner(seed=seed).run(after_wf, n, collect_events=False).kpi
    diff = compare_workflows(before_kpi, after_kpi, profile.implementation_cost)
    risk = compute_risk(after_wf, after_kpi)

    cur = profile.currency_label
    return {
        "slug": scenario.slug,
        "name": scenario.name,
        "category": CATEGORY_LABELS.get(scenario.category, scenario.category),
        "profile": profile_name,
        "before_cost_per_case": round(before_kpi.avg_cost_per_case, 2),
        "after_cost_per_case": round(after_kpi.avg_cost_per_case, 2),
        "cost_delta": round(diff.cost_per_case.delta, 2),
        "before_completion_rate": round(before_kpi.completion_rate, 4),
        "after_completion_rate": round(after_kpi.completion_rate, 4),
        "cycle_time_delta_minutes": round(diff.cycle_time_minutes.delta, 1),
        "total_cost_savings": round(diff.roi.total_cost_savings, 2),
        "roi_percentage": round(diff.roi.roi_percentage, 1) if diff.roi.roi_percentage is not None else None,  # noqa: E501
        "risk_score": round(risk.overall_score, 1),
        "risk_level": _risk_label(risk.overall_score),
        "currency": cur,
    }


def build_scenario_matrix(
    profile_name: str = "base",
    scenario_slugs: list[str] | None = None,
) -> list[dict]:
    """Run every scenario and return a list of result dicts.

    Args:
        profile_name: ``"base"``, ``"conservative"``, or ``"aggressive"``.
        scenario_slugs: Optional subset of scenario slugs.  Defaults to all.

    Returns:
        List of result dicts, sorted by descending ``total_cost_savings``.
    """
    scenarios = list_scenarios()
    if scenario_slugs:
        scenarios = [s for s in scenarios if s.slug in scenario_slugs]
    rows = [_run_matrix_row(s, profile_name) for s in scenarios]
    return sorted(rows, key=lambda r: r["total_cost_savings"], reverse=True)


def matrix_to_text(rows: list[dict]) -> str:
    """Render the matrix rows as a plain-text table."""
    if not rows:
        return "No scenarios to display."

    cur = rows[0]["currency"] if rows else "$"
    col_name = max(len(r["name"]) for r in rows) + 2
    col_cat = 22
    lines: list[str] = [
        "=" * 110,
        f"SCENARIO MATRIX  (profile: {rows[0]['profile']})",
        "=" * 110,
        f"{'Scenario':<{col_name}} {'Category':<{col_cat}} "
        f"{'Before $/case':>14} {'After $/case':>14} "
        f"{'Savings':>10} {'ROI%':>6} {'Cycle Δ':>8} {'Risk':<10}",
        "-" * 110,
    ]
    for r in rows:
        roi = f"{r['roi_percentage']:+.1f}%" if r["roi_percentage"] is not None else "n/a"
        lines.append(
            f"{r['name']:<{col_name}} {r['category']:<{col_cat}} "
            f"{cur}{r['before_cost_per_case']:>13,.2f} {cur}{r['after_cost_per_case']:>13,.2f} "
            f"{cur}{r['total_cost_savings']:>9,.0f} {roi:>6} "
            f"{r['cycle_time_delta_minutes']:>6.1f}m {r['risk_level']:<10}"
        )
    lines += [
        "",
        f"Sorted by total cost savings ({cur}).  Risk = after-variant organizational risk score.",
        "All figures are directional simulation estimates; validate with real operational data.",
    ]
    return "\n".join(lines)


def matrix_to_json(rows: list[dict]) -> str:
    """Serialize the matrix rows to a JSON string."""
    return json.dumps(rows, indent=2)


__all__ = [
    "build_scenario_matrix",
    "matrix_to_json",
    "matrix_to_text",
]
