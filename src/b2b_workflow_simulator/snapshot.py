"""Executive snapshot: a concise one-page stakeholder summary.

The snapshot is shorter and more opinionated than the full executive report.
It answers the four questions a decision-maker asks in the first five minutes:

  1. Should we do this? (headline)
  2. What changes? (before/after KPI table)
  3. How much does it save / cost? (ROI summary)
  4. What do we need to validate before committing? (next steps)

It also surfaces the top 3 bottlenecks, risks, and recommendations without
requiring the reader to understand the full simulation methodology.

No external dependencies.  Both plain-text and HTML outputs use stdlib only.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.redesign import RedesignDiff, compare_workflows
from b2b_workflow_simulator.report import build_risks


def _make_headline(diff: RedesignDiff) -> str:
    """Compose a one-sentence decision headline from the redesign diff."""
    cost_saved = diff.roi.total_cost_savings
    cr_delta = diff.completion_rate.delta
    ct_delta = diff.cycle_time_minutes.delta

    if cost_saved > 0 and cr_delta >= 0:
        return (
            f"Recommended: the redesigned workflow reduces cost by "
            f"${cost_saved:,.0f} across the simulated volume while maintaining "
            f"or improving completion rate."
        )
    elif cost_saved > 0 and cr_delta < 0:
        return (
            f"Conditional: cost falls by ${cost_saved:,.0f} but completion rate "
            f"drops by {abs(cr_delta):.1%}; validate the quality trade-off before rollout."
        )
    elif cost_saved <= 0 and ct_delta < 0:
        return (
            f"Not recommended yet: the redesign does not reduce cost under current "
            f"assumptions, though cycle time improves by {abs(ct_delta):.1f} min. "
            f"Revisit AI cost assumptions."
        )
    else:
        return (
            "Further analysis needed: cost and cycle time do not improve meaningfully "
            "under current simulation assumptions."
        )


_DEFAULT_NEXT_STEPS = [
    "Run with arrival_interval to model realistic queueing (current run is unconstrained).",
    "Validate AI error rates against actual production data before commitment.",
    "Pilot with one team or one process variant before full rollout.",
    "Review SLA requirements against the simulated cycle time distribution.",
    "Confirm implementation cost estimate with engineering and vendor quotes.",
]

_DEFAULT_ASSUMPTIONS = [
    "Cases are simulated with randomly sampled durations; results reflect expected values.",
    "AI error rates and costs are taken from the workflow definition; update for your context.",
    "Implementation cost (if supplied) is a one-time investment; recurring AI platform costs "
    "should be factored in separately.",
    "The 'after' workflow may require process change management not captured in the simulation.",
]


@dataclass
class ExecutiveSnapshot:
    """Concise stakeholder summary for one workflow redesign.

    Attributes:
        workflow_name: Human-readable name of the redesigned workflow.
        headline: One-sentence decision recommendation.
        before_kpi: KPI result from the baseline simulation run.
        after_kpi: KPI result from the redesigned simulation run.
        diff: Pre-computed :class:`~b2b_workflow_simulator.redesign.RedesignDiff`.
        top_bottlenecks: Top 3 bottleneck node names from the "after" workflow.
        top_risks: Top 3 risk strings.
        top_recommendations: Top 3 actionable recommendation strings.
        assumptions: Explicit assumptions underpinning the analysis.
        next_steps: What to validate before committing to the redesign.
    """

    workflow_name: str
    headline: str
    before_kpi: KPIResult
    after_kpi: KPIResult
    diff: RedesignDiff
    top_bottlenecks: list[str] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    top_recommendations: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def build_snapshot(
    before_kpi: KPIResult,
    after_kpi: KPIResult,
    implementation_cost: float | None = None,
    risk_assessment=None,
    recommendations=None,
    after_bottlenecks: list[tuple[str, float]] | None = None,
) -> ExecutiveSnapshot:
    """Build an :class:`ExecutiveSnapshot` from simulation results.

    Args:
        before_kpi: KPI result from the baseline run.
        after_kpi: KPI result from the redesigned run.
        implementation_cost: Optional one-time implementation cost.
        risk_assessment: Optional Phase 5 ``RiskAssessment``.  When supplied,
            the top risk factor descriptions are shown.
        recommendations: Optional Phase 5 ``RecommendationSet``.  When supplied,
            the top recommendation titles are shown.
        after_bottlenecks: Optional pre-computed bottleneck list
            ``[(node_id, minutes), ...]``.  Falls back to KPI top-3.

    Returns:
        A populated :class:`ExecutiveSnapshot`.
    """
    diff = compare_workflows(before_kpi, after_kpi, implementation_cost)
    headline = _make_headline(diff)

    bottlenecks = (
        after_bottlenecks
        if after_bottlenecks is not None
        else after_kpi.bottleneck_nodes(3)
    )
    top_bottlenecks = [f"{nid} ({mins:,.0f} min total)" for nid, mins in bottlenecks[:3]]

    top_risks = build_risks(diff)[:3]

    top_recs: list[str] = []
    if recommendations is not None and hasattr(recommendations, "recommendations"):
        top_recs = [r.title for r in recommendations.recommendations[:3]]
    if not top_recs:
        if diff.roi.total_cost_savings > 0:
            top_recs.append("Proceed with a controlled pilot rollout.")
        if diff.escalation_rate.after > 0.15:
            top_recs.append("Increase human capacity to absorb AI escalations.")
        top_recs = top_recs or ["Validate assumptions with a real-data pilot."]

    risk_list = top_risks

    return ExecutiveSnapshot(
        workflow_name=after_kpi.workflow_name,
        headline=headline,
        before_kpi=before_kpi,
        after_kpi=after_kpi,
        diff=diff,
        top_bottlenecks=top_bottlenecks,
        top_risks=risk_list,
        top_recommendations=top_recs,
        assumptions=list(_DEFAULT_ASSUMPTIONS),
        next_steps=list(_DEFAULT_NEXT_STEPS),
    )


def snapshot_to_text(snapshot: ExecutiveSnapshot) -> str:
    """Render an :class:`ExecutiveSnapshot` as a concise plain-text report.

    Args:
        snapshot: A built executive snapshot.

    Returns:
        A multi-line plain-text string designed for one-page printing.
    """
    diff = snapshot.diff
    roi = diff.roi
    before = snapshot.before_kpi
    after = snapshot.after_kpi

    lines: list[str] = [
        "=" * 64,
        f"EXECUTIVE SNAPSHOT: {snapshot.workflow_name}",
        "=" * 64,
        "",
        "DECISION",
        "-" * 64,
        snapshot.headline,
        "",
        "KPI SUMMARY",
        "-" * 64,
        f"{'Metric':<28} {'Before':>12} {'After':>12}",
        "-" * 54,
        f"{'Completion rate':<28} {before.completion_rate:>11.1%} {after.completion_rate:>11.1%}",
        f"{'Failure rate':<28} {before.failure_rate:>11.1%} {after.failure_rate:>11.1%}",
        f"{'Avg cost / case':<28} ${before.avg_cost_per_case:>10,.2f} "
        f"${after.avg_cost_per_case:>10,.2f}",
        f"{'Avg cycle time (min)':<28} {before.avg_cycle_time_minutes:>11,.1f} "
        f"{after.avg_cycle_time_minutes:>11,.1f}",
        f"{'Escalation rate':<28} {before.escalation_rate:>11.1%} {after.escalation_rate:>11.1%}",
        "",
        "ROI SUMMARY",
        "-" * 64,
        f"Total cost savings:  ${roi.total_cost_savings:,.2f}",
    ]
    if roi.roi_percentage is not None:
        lines.append(f"ROI percentage:      {roi.roi_percentage:+.1f}%")
    if roi.implementation_cost is not None:
        lines.append(f"Implementation cost: ${roi.implementation_cost:,.2f}")
        if roi.payback_feasible and roi.payback_in_cases is not None:
            lines.append(f"Payback:             ~{roi.payback_in_cases:,.0f} cases")
        else:
            lines.append("Payback:             Not reached under these assumptions")
    lines.append("")

    lines += ["TOP 3 BOTTLENECKS", "-" * 64]
    for i, b in enumerate(snapshot.top_bottlenecks, 1):
        lines.append(f"  {i}. {b}")
    lines.append("")

    lines += ["TOP 3 RISKS", "-" * 64]
    for i, r in enumerate(snapshot.top_risks, 1):
        lines.append(f"  {i}. {r}")
    lines.append("")

    lines += ["TOP 3 RECOMMENDATIONS", "-" * 64]
    for i, rec in enumerate(snapshot.top_recommendations, 1):
        lines.append(f"  {i}. {rec}")
    lines.append("")

    lines += ["ASSUMPTIONS", "-" * 64]
    for a in snapshot.assumptions:
        lines.append(f"  - {a}")
    lines.append("")

    lines += ["WHAT TO VALIDATE NEXT", "-" * 64]
    for ns in snapshot.next_steps:
        lines.append(f"  - {ns}")

    return "\n".join(lines)


def snapshot_to_html(snapshot: ExecutiveSnapshot) -> str:
    """Render an :class:`ExecutiveSnapshot` as a standalone HTML page.

    All user-supplied text is HTML-escaped.  No external assets.

    Args:
        snapshot: A built executive snapshot.

    Returns:
        A self-contained HTML string.
    """
    diff = snapshot.diff
    roi = diff.roi
    before = snapshot.before_kpi
    after = snapshot.after_kpi

    def e(v: object) -> str:
        return html.escape(str(v), quote=True)

    def _row(label: str, b: str, a: str, good_when_lower: bool = False) -> str:
        try:
            bv = float(b.replace("$", "").replace(",", "").replace("%", ""))
            av = float(a.replace("$", "").replace(",", "").replace("%", ""))
            improved = av < bv if good_when_lower else av > bv
            cls = ' class="pos"' if improved else ' class="neg"'
        except Exception:
            cls = ""
        return (
            f"<tr><td>{e(label)}</td><td>{e(b)}</td>"
            f"<td{cls}>{e(a)}</td></tr>"
        )

    roi_html = f"<li>Total cost savings: <strong>${roi.total_cost_savings:,.2f}</strong></li>"
    if roi.roi_percentage is not None:
        roi_html += f"<li>ROI: <strong>{roi.roi_percentage:+.1f}%</strong></li>"
    if roi.implementation_cost is not None:
        roi_html += f"<li>Implementation cost: ${roi.implementation_cost:,.2f}</li>"
        if roi.payback_feasible and roi.payback_in_cases is not None:
            roi_html += f"<li>Payback: ~{roi.payback_in_cases:,.0f} cases</li>"
        else:
            roi_html += "<li>Payback: not reached under these assumptions</li>"

    def _li_list(items: list[str]) -> str:
        return (
            "".join(f"<li>{e(item)}</li>" for item in items)
            if items else "<li>None identified.</li>"
        )

    style = """
<style>
  body{font-family:-apple-system,"Segoe UI",Arial,sans-serif;max-width:860px;
       margin:2rem auto;color:#1a1a1a;line-height:1.5;}
  h1{color:#0b2540;border-bottom:3px solid #0b2540;padding-bottom:.4rem;}
  h2{color:#0b2540;border-bottom:1px solid #e1e8ef;padding-bottom:.2rem;margin-top:1.8rem;}
  .headline{background:#f0f8ff;border-left:5px solid #0b2540;
            padding:.75rem 1rem;margin:1rem 0;font-weight:500;}
  table{border-collapse:collapse;width:100%;}
  th,td{border:1px solid #d0d7de;padding:.4rem .75rem;text-align:left;}
  th{background:#f4f6f8;}
  td.pos{color:#146c2e;font-weight:600;}
  td.neg{color:#b3261e;font-weight:600;}
  ul{margin:.5rem 0;padding-left:1.5rem;}
  li{margin-bottom:.3rem;}
  .note{font-size:.85em;color:#666;background:#fafafa;
        border:1px solid #e1e8ef;padding:.5rem .75rem;margin:.5rem 0;}
</style>"""

    body = f"""
<h1>Executive Snapshot: {e(snapshot.workflow_name)}</h1>

<h2>Decision</h2>
<div class="headline">{e(snapshot.headline)}</div>

<h2>KPI Summary</h2>
<table>
  <tr><th>Metric</th><th>Before</th><th>After</th></tr>
  {_row("Completion rate", f"{before.completion_rate:.1%}", f"{after.completion_rate:.1%}")}
  {_row("Failure rate", f"{before.failure_rate:.1%}", f"{after.failure_rate:.1%}",
         good_when_lower=True)}
  {_row("Avg cost / case", f"${before.avg_cost_per_case:,.2f}",
         f"${after.avg_cost_per_case:,.2f}", good_when_lower=True)}
  {_row("Avg cycle time (min)", f"{before.avg_cycle_time_minutes:,.1f}",
         f"{after.avg_cycle_time_minutes:,.1f}", good_when_lower=True)}
  {_row("Escalation rate", f"{before.escalation_rate:.1%}",
         f"{after.escalation_rate:.1%}", good_when_lower=True)}
</table>

<h2>ROI Summary</h2>
<ul>{roi_html}</ul>

<h2>Top 3 Bottlenecks</h2>
<ul>{_li_list(snapshot.top_bottlenecks)}</ul>

<h2>Top 3 Risks</h2>
<ul>{_li_list(snapshot.top_risks)}</ul>

<h2>Top 3 Recommendations</h2>
<ul>{_li_list(snapshot.top_recommendations)}</ul>

<h2>Assumptions</h2>
<ul>{_li_list(snapshot.assumptions)}</ul>

<h2>What to Validate Next</h2>
<ul>{_li_list(snapshot.next_steps)}</ul>

<div class="note">This snapshot is generated from simulation output.
All figures are directional estimates. Validate assumptions against
real operational data before committing to the redesign.</div>
"""
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        f'  <meta charset="utf-8">\n'
        f'  <title>Executive Snapshot: {e(snapshot.workflow_name)}</title>\n'
        f"{style}\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


__all__ = [
    "ExecutiveSnapshot",
    "build_snapshot",
    "snapshot_to_html",
    "snapshot_to_text",
]
