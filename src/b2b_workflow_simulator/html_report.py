"""Static HTML rendering of a `RedesignDiff` or `WorkflowPortfolio`.

Reports are single, self-contained HTML files with inline CSS: no
frontend framework, no external assets, nothing that requires a server
to view. Every piece of interpolated text is escaped via the stdlib
`html` module, so workflow names, node ids, or descriptions containing
special characters cannot break the page.
"""

from __future__ import annotations

import html

from b2b_workflow_simulator.portfolio import WorkflowPortfolio
from b2b_workflow_simulator.redesign import MetricDelta, RedesignDiff
from b2b_workflow_simulator.report import (
    build_recommendation,
    build_risks,
    format_metric_value,
    format_percent_change,
)

_STYLE = """
    <style>
      body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; margin: 2rem auto;
             max-width: 900px; color: #1a1a1a; line-height: 1.5; }
      h1 { color: #0b2540; margin-bottom: 0.25rem; }
      h2 { color: #0b2540; border-bottom: 2px solid #e1e8ef; padding-bottom: 0.25rem;
           margin-top: 2rem; }
      p.subtitle { color: #4a5a6a; margin-top: 0; }
      table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
      th, td { border: 1px solid #d0d7de; padding: 0.5rem 0.75rem; text-align: left; }
      th { background: #f4f6f8; }
      td.positive { color: #146c2e; font-weight: 600; }
      td.negative { color: #b3261e; font-weight: 600; }
      ul { margin: 0.5rem 0; padding-left: 1.5rem; }
      li { margin-bottom: 0.35rem; }
      .callout { background: #f4f6f8; border-left: 4px solid #0b2540; padding: 0.75rem 1rem;
                 margin: 1rem 0; }
      .rank { font-weight: 600; color: #0b2540; }
    </style>
"""

_GOOD_WHEN_LOWER = {
    "Failure rate",
    "Total cost",
    "Cost per case",
    "Cycle time (minutes)",
    "Wait time (minutes)",
}


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _metric_delta_class(metric: MetricDelta) -> str:
    is_good = (metric.delta <= 0) if metric.label in _GOOD_WHEN_LOWER else (metric.delta >= 0)
    return "positive" if is_good else "negative"


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{_escape(title)}</title>\n"
        f"{_STYLE}"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def _metrics_table(diff: RedesignDiff) -> str:
    rows = []
    for metric in diff.metrics:
        delta_class = _metric_delta_class(metric)
        change_str = _escape(format_percent_change(metric))
        rows.append(
            "<tr>"
            f"<td>{_escape(metric.label)}</td>"
            f"<td>{_escape(format_metric_value(metric, metric.before))}</td>"
            f"<td>{_escape(format_metric_value(metric, metric.after))}</td>"
            f'<td class="{delta_class}">{change_str}</td>'
            "</tr>"
        )
    return (
        "<table>\n"
        "  <tr><th>Metric</th><th>Before</th><th>After</th><th>Change</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def _bottleneck_list(bottlenecks: list[tuple[str, float]]) -> str:
    if not bottlenecks:
        return "<p>No bottleneck data available.</p>"
    items = "".join(
        f"<li>{_escape(node_id)}: {minutes:,.1f} minutes</li>" for node_id, minutes in bottlenecks
    )
    return f"<ul>{items}</ul>"


def _utilization_list(utilization: dict[str, float]) -> str:
    if not utilization:
        return "<p>No capacity data available.</p>"
    items = "".join(
        f"<li>{_escape(actor_id)}: {value:.1%}</li>"
        for actor_id, value in sorted(utilization.items())
    )
    return f"<ul>{items}</ul>"


def render_diff_html(diff: RedesignDiff) -> str:
    """Render a `RedesignDiff` as a standalone HTML report."""
    risks = "".join(f"<li>{_escape(risk)}</li>" for risk in build_risks(diff))
    roi_lines = [f"<li>Total cost savings: ${diff.roi.total_cost_savings:,.2f}</li>"]
    if diff.roi.roi_percentage is not None:
        roi_lines.append(f"<li>ROI: {diff.roi.roi_percentage:+.1f}%</li>")
    if diff.roi.implementation_cost is not None:
        roi_lines.append(f"<li>Implementation cost: ${diff.roi.implementation_cost:,.2f}</li>")
        if diff.roi.payback_feasible and diff.roi.payback_in_cases is not None:
            roi_lines.append(f"<li>Payback: ~{diff.roi.payback_in_cases:,.0f} cases</li>")
        else:
            roi_lines.append("<li>Payback: not reached under simulated assumptions</li>")

    body = f"""
  <h1>Workflow Redesign Analysis</h1>
  <p class="subtitle">Comparing <strong>{_escape(diff.before_name)}</strong> against
  <strong>{_escape(diff.after_name)}</strong></p>

  <h2>KPI Comparison</h2>
  {_metrics_table(diff)}

  <h2>ROI Summary</h2>
  <ul>{"".join(roi_lines)}</ul>

  <h2>Bottlenecks</h2>
  <p><strong>Before:</strong></p>
  {_bottleneck_list(diff.before_bottlenecks)}
  <p><strong>After:</strong></p>
  {_bottleneck_list(diff.after_bottlenecks)}

  <h2>Actor Utilization</h2>
  <p><strong>Before:</strong></p>
  {_utilization_list(diff.before_utilization)}
  <p><strong>After:</strong></p>
  {_utilization_list(diff.after_utilization)}

  <h2>Risks</h2>
  <ul>{risks}</ul>

  <h2>Recommendation</h2>
  <div class="callout">{_escape(build_recommendation(diff))}</div>
"""
    return _page(f"{diff.after_name} - Redesign Report", body)


def _ranking_table(portfolio: WorkflowPortfolio, rank_by: str) -> str:
    rows = []
    for rank, entry in enumerate(portfolio.ranked(by=rank_by), start=1):
        roi = entry.diff.roi.roi_percentage
        roi_str = f"{roi:+.1f}%" if roi is not None else "n/a"
        rows.append(
            "<tr>"
            f'<td class="rank">{rank}</td>'
            f"<td>{_escape(entry.name)}</td>"
            f"<td>${entry.diff.roi.total_cost_savings:,.2f}</td>"
            f"<td>{_escape(roi_str)}</td>"
            "</tr>"
        )
    return (
        "<table>\n"
        "  <tr><th>Rank</th><th>Workflow</th><th>Cost Savings</th><th>ROI %</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def render_portfolio_html(portfolio: WorkflowPortfolio, rank_by: str = "total_cost_savings") -> str:
    """Render a `WorkflowPortfolio` as a standalone HTML report."""
    summary = portfolio.summary()

    aggregate_lines = [
        f"<li>Total before cost: ${summary.total_before_cost:,.2f}</li>",
        f"<li>Total after cost: ${summary.total_after_cost:,.2f}</li>",
        f"<li>Total cost savings: ${summary.total_cost_savings:,.2f}</li>",
    ]
    if summary.portfolio_roi_percentage is not None:
        aggregate_lines.append(f"<li>Portfolio ROI: {summary.portfolio_roi_percentage:+.1f}%</li>")
    aggregate_lines.append(
        f"<li>Total wait time saved: {summary.total_wait_minutes_saved:,.1f} minutes</li>"
    )
    if summary.total_implementation_cost > 0:
        aggregate_lines.append(
            f"<li>Total implementation cost: ${summary.total_implementation_cost:,.2f}</li>"
        )
        if summary.payback_feasible and summary.payback_in_periods is not None:
            aggregate_lines.append(
                f"<li>Payback: ~{summary.payback_in_periods:.2f} simulated case-volume periods</li>"
            )
        else:
            aggregate_lines.append("<li>Payback: not reached under simulated assumptions</li>")

    risks = []
    for entry in portfolio.entries:
        for risk in build_risks(entry.diff):
            if risk == "No material risks identified from the simulated metrics.":
                continue
            risks.append(f"<li>[{_escape(entry.name)}] {_escape(risk)}</li>")
    if not risks:
        risks.append("<li>No material risks identified from the simulated metrics.</li>")

    rollout = "".join(
        f"<li>{_escape(entry.name)} (${entry.diff.roi.total_cost_savings:,.2f} savings)</li>"
        for entry in portfolio.ranked(by=rank_by)
    )

    body = f"""
  <h1>Workflow Portfolio Analysis</h1>
  <p class="subtitle">{_escape(portfolio.name)} &mdash; {summary.workflow_count} workflow(s)</p>

  <h2>Workflow Ranking</h2>
  {_ranking_table(portfolio, rank_by)}

  <h2>Aggregate ROI &amp; Payback</h2>
  <ul>{"".join(aggregate_lines)}</ul>

  <h2>Risks</h2>
  <ul>{"".join(risks)}</ul>

  <h2>Recommended Rollout Order</h2>
  <ol>{rollout}</ol>
"""
    return _page(f"{portfolio.name} - Portfolio Report", body)


__all__ = ["render_diff_html", "render_portfolio_html"]
