"""Static HTML rendering of a `RedesignDiff` or `WorkflowPortfolio`.

Reports are single, self-contained HTML files with inline CSS: no
frontend framework, no external assets, nothing that requires a server
to view. Every piece of interpolated text is escaped via the stdlib
`html` module, so workflow names, node ids, or descriptions containing
special characters cannot break the page.
"""

from __future__ import annotations

import html

from b2b_workflow_simulator.ai_adoption import RECOMMENDATION_LABELS, AIAdoptionAssessment
from b2b_workflow_simulator.capacity_planning import (
    BALANCED,
    OVERLOADED,
    UNDERUTILIZED,
    CapacityPlan,
    HiringSimulationResult,
)
from b2b_workflow_simulator.compliance import ComplianceReport
from b2b_workflow_simulator.executive_report import ExecutiveAssessment
from b2b_workflow_simulator.monte_carlo import (
    COMPARISON_METRICS,
    KPI_METRICS,
    METRIC_LABELS,
    MetricStats,
    MonteCarloComparisonResult,
    MonteCarloResult,
    build_comparison_variability_summary,
    build_variability_summary,
    format_stat_value,
)
from b2b_workflow_simulator.policy import SEVERITY_ERROR, PolicyEvaluation
from b2b_workflow_simulator.portfolio import WorkflowPortfolio
from b2b_workflow_simulator.recommendation import RecommendationSet
from b2b_workflow_simulator.redesign import MetricDelta, RedesignDiff
from b2b_workflow_simulator.report import (
    build_recommendation,
    build_risks,
    format_metric_value,
    format_percent_change,
)
from b2b_workflow_simulator.risk import CATEGORIES, CATEGORY_LABELS, RiskAssessment
from b2b_workflow_simulator.sensitivity_grid import SensitivityGridResult
from b2b_workflow_simulator.sla import SLAReport

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
      td.region-safe { background: #e6f4ea; color: #146c2e; font-weight: 600; }
      td.region-negative { background: #fdecea; color: #b3261e; font-weight: 600; }
      td.region-unstable { background: #3a3a3a; color: #ffffff; font-weight: 600; }
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


def _stats_table(metric_stats: dict[str, MetricStats], metrics: list[str]) -> str:
    rows = []
    for metric in metrics:
        stats = metric_stats.get(metric)
        label = _escape(METRIC_LABELS.get(metric, metric))
        if stats is None or stats.sample_count == 0:
            rows.append(f"<tr><td>{label}</td><td colspan='6'>n/a</td></tr>")
            continue
        rows.append(
            "<tr>"
            f"<td>{label}</td>"
            f"<td>{_escape(format_stat_value(metric, stats.mean))}</td>"
            f"<td>{_escape(format_stat_value(metric, stats.minimum))}</td>"
            f"<td>{_escape(format_stat_value(metric, stats.maximum))}</td>"
            f"<td>{_escape(format_stat_value(metric, stats.median))}</td>"
            f"<td>{_escape(format_stat_value(metric, stats.p10))}</td>"
            f"<td>{_escape(format_stat_value(metric, stats.p90))}</td>"
            "</tr>"
        )
    return (
        "<table>\n"
        "  <tr><th>Metric</th><th>Mean</th><th>Min</th><th>Max</th>"
        "<th>Median</th><th>P10</th><th>P90</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def render_monte_carlo_html(result: MonteCarloResult) -> str:
    """Render a `MonteCarloResult` as a standalone HTML report."""
    summary_items = "".join(
        f"<li>{_escape(line)}</li>" for line in build_variability_summary(result)
    )
    body = f"""
  <h1>Monte Carlo Simulation Analysis</h1>
  <p class="subtitle">{_escape(result.workflow_name)} &mdash; {result.num_runs} simulated runs</p>

  <h2>Executive Summary</h2>
  <ul>{summary_items}</ul>

  <h2>Metric Distribution</h2>
  {_stats_table(result.metric_stats, list(KPI_METRICS))}
"""
    return _page(f"{result.workflow_name} - Monte Carlo Report", body)


def render_monte_carlo_comparison_html(result: MonteCarloComparisonResult) -> str:
    """Render a `MonteCarloComparisonResult` as a standalone HTML report."""
    summary_items = "".join(
        f"<li>{_escape(line)}</li>" for line in build_comparison_variability_summary(result)
    )
    body = f"""
  <h1>Monte Carlo Redesign Comparison</h1>
  <p class="subtitle">{_escape(result.before_name)} vs {_escape(result.after_name)}
  &mdash; {result.num_runs} simulated runs</p>

  <h2>Executive Summary</h2>
  <ul>{summary_items}</ul>

  <h2>Metric Distribution</h2>
  {_stats_table(result.metric_stats, list(COMPARISON_METRICS))}
"""
    return _page(f"{result.before_name} vs {result.after_name} - Monte Carlo Comparison", body)


def _grid_roi_table(result: SensitivityGridResult) -> str:
    header_cells = "".join(f"<th>{_escape(f'{x:.4g}')}</th>" for x in result.x_values)
    rows = []
    for y_value in result.y_values:
        cells = []
        for x_value in result.x_values:
            point = result.point_at(x_value, y_value)
            roi = point.diff.roi.roi_percentage
            roi_str = f"{roi:+.1f}%" if roi is not None else "n/a"
            region = result.classify_region(x_value, y_value)
            cells.append(f'<td class="region-{region}">{_escape(roi_str)}</td>')
        rows.append(f"<tr><th>{_escape(f'{y_value:.4g}')}</th>" + "".join(cells) + "</tr>")
    corner = _escape(f"{result.y_parameter} \\ {result.x_parameter}")
    return (
        "<table>\n"
        f"  <tr><th>{corner}</th>{header_cells}</tr>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def render_sensitivity_grid_html(result: SensitivityGridResult) -> str:
    """Render a `SensitivityGridResult` as a standalone HTML report with a colored ROI matrix."""
    total = len(result.points)
    safe = len(result.safe_region_points())
    negative = len(result.negative_region_points())
    unstable = len(result.unstable_region_points())
    region_summary = f"""
  <ul>
    <li>Safe operating region: {safe}/{total} combinations</li>
    <li>Negative ROI region: {negative}/{total} combinations</li>
    <li>Unstable region: {unstable}/{total} combinations</li>
  </ul>
"""
    body = f"""
  <h1>Multi-Parameter Sensitivity Analysis</h1>
  <p class="subtitle">{_escape(result.x_parameter)} (columns) &times;
  {_escape(result.y_parameter)} (rows) &mdash; {total} combinations simulated</p>

  <h2>ROI Matrix</h2>
  {_grid_roi_table(result)}

  <h2>Operating Regions</h2>
  {region_summary}
"""
    return _page(
        f"{result.x_parameter} x {result.y_parameter} - Sensitivity Grid Report", body
    )


_STATUS_CLASS = {
    OVERLOADED: "region-negative",
    UNDERUTILIZED: "region-unstable",
    BALANCED: "region-safe",
}


def _capacity_table(plan: CapacityPlan) -> str:
    if not plan.recommendations:
        return "<p>No capacity-aware utilization data was recorded for this run.</p>"
    rows = []
    for rec in plan.recommendations:
        css_class = _STATUS_CLASS.get(rec.status, "")
        rows.append(
            "<tr>"
            f"<td>{_escape(rec.resource_id)}</td>"
            f"<td>{_escape(rec.resource_kind)}</td>"
            f"<td>{rec.current_utilization:.1%}</td>"
            f'<td class="{css_class}">{_escape(rec.status)}</td>'
            f"<td>{rec.current_headcount}</td>"
            f"<td>{rec.recommended_headcount}</td>"
            "</tr>"
        )
    return (
        "<table>\n"
        "  <tr><th>Resource</th><th>Kind</th><th>Utilization</th><th>Status</th>"
        "<th>Current</th><th>Recommended</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def render_capacity_html(plan: CapacityPlan) -> str:
    """Render a `CapacityPlan` as a standalone HTML staffing report."""
    rationale_items = "".join(f"<li>{_escape(rec.rationale)}</li>" for rec in plan.recommendations)
    body = f"""
  <h1>Capacity Planning Analysis</h1>
  <p class="subtitle">{_escape(plan.workflow_name)} &mdash; target utilization
  {plan.target_utilization:.0%}</p>

  <h2>Staffing Recommendations</h2>
  {_capacity_table(plan)}

  <h2>Details</h2>
  <ul>{rationale_items}</ul>
"""
    return _page(f"{plan.workflow_name} - Capacity Plan", body)


def render_hiring_html(result: HiringSimulationResult) -> str:
    """Render a `HiringSimulationResult` as a standalone HTML before/after report."""
    body = f"""
  <h1>Hiring Simulation</h1>
  <p class="subtitle">{_escape(result.workflow_name)} &mdash; pool {_escape(result.pool_id)}</p>

  <h2>Proposed Headcount Change</h2>
  <p>{result.baseline_worker_count} &rarr; {result.proposed_worker_count} worker(s)</p>

  <h2>Impact</h2>
  <table>
    <tr><th>Metric</th><th>Baseline</th><th>Proposed</th></tr>
    <tr><td>Utilization</td><td>{result.baseline_utilization:.1%}</td>
        <td>{result.proposed_utilization:.1%}</td></tr>
    <tr><td>Max queue depth</td><td>{result.baseline_max_queue_depth}</td>
        <td>{result.proposed_max_queue_depth}</td></tr>
    <tr><td>Average wait (minutes)</td><td>{result.baseline_avg_wait_minutes:,.1f}</td>
        <td>{result.proposed_avg_wait_minutes:,.1f}</td></tr>
  </table>
"""
    return _page(f"{result.workflow_name} - Hiring Simulation", body)


def _violation_table(evaluation: PolicyEvaluation) -> str:
    if not evaluation.violations:
        return "<p>No violations to report.</p>"
    rows = []
    for violation in evaluation.violations:
        css_class = "region-negative" if violation.severity == SEVERITY_ERROR else "region-unstable"
        node_label = violation.node_id or "-"
        rows.append(
            "<tr>"
            f"<td>{_escape(violation.policy_name)}</td>"
            f"<td>{_escape(violation.policy_kind)}</td>"
            f"<td>{_escape(node_label)}</td>"
            f'<td class="{css_class}">{_escape(violation.severity)}</td>'
            f"<td>{_escape(violation.description)}</td>"
            "</tr>"
        )
    return (
        "<table>\n"
        "  <tr><th>Policy</th><th>Kind</th><th>Node</th><th>Severity</th>"
        "<th>Description</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def render_policy_html(evaluation: PolicyEvaluation) -> str:
    """Render a `PolicyEvaluation` as a standalone HTML governance report."""
    status = "Compliant" if evaluation.is_compliant else "Violations found"
    policy_word = "policy" if evaluation.policies_checked == 1 else "policies"
    body = f"""
  <h1>Policy Compliance Analysis</h1>
  <p class="subtitle">{_escape(evaluation.workflow_name)} &mdash;
  {evaluation.policies_checked} {policy_word} checked</p>

  <p class="callout"><strong>{_escape(status)}</strong>
  &mdash; {evaluation.error_count} error(s), {evaluation.warning_count} warning(s)</p>

  <h2>Violations</h2>
  {_violation_table(evaluation)}
"""
    return _page(f"{evaluation.workflow_name} - Policy Compliance", body)


def _compliance_violation_table(report: ComplianceReport) -> str:
    if not report.violations:
        return "<p>No violations to report.</p>"
    rows = [
        "<tr>"
        f"<td>{_escape(v.requirement_name)}</td>"
        f"<td>{_escape(v.requirement_kind)}</td>"
        f'<td class="region-negative">{_escape(v.node_id or "-")}</td>'
        f"<td>{_escape(v.description)}</td>"
        "</tr>"
        for v in report.violations
    ]
    return (
        "<table>\n"
        "  <tr><th>Requirement</th><th>Kind</th><th>Node</th><th>Description</th></tr>\n"
        + "\n".join(rows)
        + "\n</table>"
    )


def _compliance_findings_list(report: ComplianceReport) -> str:
    if not report.audit_findings:
        return "<p>No audit findings recorded.</p>"
    items = "".join(
        f"<li><strong>{_escape(f.requirement_name)}</strong>: {_escape(f.finding)}</li>"
        for f in report.audit_findings
    )
    return f"<ul>{items}</ul>"


def render_compliance_html(report: ComplianceReport) -> str:
    """Render a `ComplianceReport` as a standalone HTML audit-ready report."""
    body = f"""
  <h1>Compliance Analysis</h1>
  <p class="subtitle">{_escape(report.workflow_name)} &mdash;
  {report.requirements_checked} requirement(s) checked</p>

  <p class="callout"><strong>Compliance score: {report.compliance_score:.1f}%</strong>
  &mdash; {report.violation_count} violation(s)</p>

  <h2>Violations</h2>
  {_compliance_violation_table(report)}

  <h2>Audit Findings</h2>
  {_compliance_findings_list(report)}
"""
    return _page(f"{report.workflow_name} - Compliance Report", body)


def _sla_breach_cause_list(report: SLAReport) -> str:
    causes = report.breach_causes()
    if not causes:
        return "<p>No breaches recorded.</p>"
    items = "".join(
        f"<li>{_escape(name)}: {count} breach(es)</li>" for name, count in sorted(causes.items())
    )
    return f"<ul>{items}</ul>"


def render_sla_html(report: SLAReport) -> str:
    """Render an `SLAReport` as a standalone HTML service-level report."""
    penalty_line = (
        f"<p>Estimated financial penalty: ${report.total_penalty:,.2f}</p>"
        if report.total_penalty > 0
        else ""
    )
    body = f"""
  <h1>SLA Performance Analysis</h1>
  <p class="subtitle">{_escape(report.workflow_name)} &mdash;
  {report.rules_checked} rule(s) across {report.cases_evaluated} case(s)</p>

  <p class="callout"><strong>Attainment rate: {report.attainment_rate:.1%}</strong>
  &mdash; {report.breach_count} breach(es), averaging
  {report.average_breach_minutes:,.1f} minute(s) over deadline</p>
  {penalty_line}

  <h2>Breach Causes</h2>
  {_sla_breach_cause_list(report)}
"""
    return _page(f"{report.workflow_name} - SLA Report", body)


def _risk_category_table(assessment: RiskAssessment) -> str:
    rows = "".join(
        f"<tr><td>{_escape(CATEGORY_LABELS[category])}</td>"
        f"<td>{assessment.category_scores.get(category, 0.0):.1f}/100</td></tr>"
        for category in CATEGORIES
    )
    return f"<table>\n  <tr><th>Category</th><th>Score</th></tr>\n{rows}\n</table>"


def _risk_factor_list(assessment: RiskAssessment) -> str:
    if not assessment.factors:
        return "<p>No risk factors identified.</p>"
    sections = []
    for category in CATEGORIES:
        factors = assessment.factors_for(category)
        if not factors:
            continue
        items = "".join(
            f"<li>{_escape(factor.description)} (weight: {factor.weight:.1f})</li>"
            for factor in sorted(factors, key=lambda f: f.weight, reverse=True)
        )
        sections.append(f"<h3>{_escape(CATEGORY_LABELS[category])}</h3><ul>{items}</ul>")
    return "".join(sections)


def render_risk_html(assessment: RiskAssessment) -> str:
    """Render a `RiskAssessment` as a standalone HTML organizational risk report."""
    body = f"""
  <h1>Organizational Risk Assessment</h1>
  <p class="subtitle">{_escape(assessment.workflow_name)}</p>

  <p class="callout"><strong>Overall risk score: {assessment.overall_score:.1f}/100</strong></p>

  <h2>Category Scores</h2>
  {_risk_category_table(assessment)}

  <h2>Risk Factors</h2>
  {_risk_factor_list(assessment)}
"""
    return _page(f"{assessment.workflow_name} - Risk Assessment", body)


def render_recommendation_html(recommendation_set: RecommendationSet) -> str:
    """Render a `RecommendationSet` as a standalone HTML report."""
    if not recommendation_set.recommendations:
        cards = "<p>No actionable recommendations at this time.</p>"
    else:
        cards = "".join(
            f"""
  <div class="callout">
    <p><strong>{index}. {_escape(rec.title)}</strong>
    &mdash; {_escape(rec.confidence)} confidence</p>
    <p>{_escape(rec.reasoning)}</p>
    <ul>
      <li>Affected KPIs: {_escape(", ".join(rec.affected_kpis))}</li>
      <li>Expected benefit: {_escape(rec.expected_benefit)}</li>
    </ul>
  </div>
"""
            for index, rec in enumerate(recommendation_set.recommendations, start=1)
        )

    body = f"""
  <h1>Recommendations</h1>
  <p class="subtitle">{_escape(recommendation_set.workflow_name)} &mdash;
  {len(recommendation_set)} recommendation(s)</p>
  {cards}
"""
    return _page(f"{recommendation_set.workflow_name} - Recommendations", body)


def render_ai_adoption_html(assessment: AIAdoptionAssessment) -> str:
    """Render an `AIAdoptionAssessment` as a standalone HTML report."""
    reasoning_items = "".join(f"<li>{_escape(reason)}</li>" for reason in assessment.reasoning)
    body = f"""
  <h1>AI Adoption Assessment</h1>
  <p class="subtitle">{_escape(assessment.workflow_name)}</p>

  <p class="callout"><strong>Readiness index: {assessment.readiness_index:.1f}/100</strong>
  &mdash; Recommendation: <strong>{_escape(RECOMMENDATION_LABELS[assessment.recommendation])}
  </strong></p>

  <h2>Scores</h2>
  <table>
    <tr><th>Dimension</th><th>Score</th></tr>
    <tr><td>Automation readiness</td><td>{assessment.automation_readiness:.1f}/100</td></tr>
    <tr><td>AI maturity</td><td>{assessment.ai_maturity:.1f}/100</td></tr>
    <tr><td>Human dependency</td><td>{assessment.human_dependency:.1f}/100</td></tr>
    <tr><td>Governance</td><td>{assessment.governance_score:.1f}/100</td></tr>
    <tr><td>Explainability</td><td>{assessment.explainability_score:.1f}/100</td></tr>
    <tr><td>Rollout complexity</td><td>{assessment.rollout_complexity:.1f}/100</td></tr>
  </table>

  <h2>Reasoning</h2>
  <ul>{reasoning_items}</ul>
"""
    return _page(f"{assessment.workflow_name} - AI Adoption Assessment", body)


def _executive_kpi_list(kpi) -> str:
    items = [
        f"<li>Cases simulated: {kpi.total_cases}</li>",
        f"<li>Completion rate: {kpi.completion_rate:.1%}</li>",
        f"<li>Failure rate: {kpi.failure_rate:.1%}</li>",
        f"<li>Total cost: ${kpi.total_cost:,.2f}</li>",
        f"<li>Average cycle time: {kpi.avg_cycle_time_minutes:,.1f} minutes</li>",
        f"<li>Average wait time: {kpi.avg_wait_time_minutes:,.1f} minutes</li>",
        f"<li>Escalation rate: {kpi.escalation_rate:.1%}</li>",
    ]
    return f"<ul>{''.join(items)}</ul>"


def _executive_roi_section(diff: RedesignDiff | None) -> str:
    if diff is None:
        return "<p>No redesign comparison supplied; ROI section omitted.</p>"
    items = [
        f"<li>Comparing '{_escape(diff.before_name)}' against "
        f"'{_escape(diff.after_name)}'.</li>",
        f"<li>Total cost savings: ${diff.roi.total_cost_savings:,.2f}</li>",
    ]
    if diff.roi.roi_percentage is not None:
        items.append(f"<li>ROI: {diff.roi.roi_percentage:+.1f}%</li>")
    if diff.roi.implementation_cost is not None:
        items.append(f"<li>Implementation cost: ${diff.roi.implementation_cost:,.2f}</li>")
        if diff.roi.payback_feasible and diff.roi.payback_in_cases is not None:
            items.append(f"<li>Payback: ~{diff.roi.payback_in_cases:,.0f} cases</li>")
        else:
            items.append("<li>Payback: not reached under simulated assumptions</li>")
    return f"<ul>{''.join(items)}</ul>"


def _executive_sla_section(sla_report: SLAReport | None) -> str:
    if sla_report is None:
        return "<p>No SLA rules supplied; SLA section omitted.</p>"
    penalty_line = (
        f"<li>Estimated financial penalty: ${sla_report.total_penalty:,.2f}</li>"
        if sla_report.total_penalty > 0
        else ""
    )
    return (
        "<ul>"
        f"<li>Attainment rate: {sla_report.attainment_rate:.1%}</li>"
        f"<li>Breaches: {sla_report.breach_count}</li>"
        f"<li>Average breach duration: {sla_report.average_breach_minutes:,.1f} minutes</li>"
        f"{penalty_line}"
        "</ul>"
    )


def _executive_compliance_section(compliance_report: ComplianceReport | None) -> str:
    if compliance_report is None:
        return "<p>No compliance requirements supplied; compliance section omitted.</p>"
    return (
        "<ul>"
        f"<li>Compliance score: {compliance_report.compliance_score:.1f}%</li>"
        f"<li>Violations: {compliance_report.violation_count}</li>"
        f"<li>Audit findings: {len(compliance_report.audit_findings)}</li>"
        "</ul>"
    )


def _executive_policy_section(policy_evaluation: PolicyEvaluation | None) -> str:
    if policy_evaluation is None:
        return "<p>No policies supplied; policy violation section omitted.</p>"
    return (
        "<ul>"
        f"<li>Policies checked: {policy_evaluation.policies_checked}</li>"
        f"<li>Violations: {policy_evaluation.violation_count} "
        f"({policy_evaluation.error_count} error(s), "
        f"{policy_evaluation.warning_count} warning(s))</li>"
        "</ul>"
    )


def _executive_recommendation_section(recommendations, top_n: int = 5) -> str:
    if not recommendations.recommendations:
        return "<p>No actionable recommendations at this time.</p>"
    cards = "".join(
        f"""
  <div class="callout">
    <p><strong>{index}. {_escape(rec.title)}</strong>
    &mdash; {_escape(rec.confidence)} confidence</p>
    <p>{_escape(rec.reasoning)}</p>
  </div>
"""
        for index, rec in enumerate(recommendations.recommendations[:top_n], start=1)
    )
    remaining = len(recommendations.recommendations) - top_n
    if remaining > 0:
        cards += f"<p>...and {remaining} more recommendation(s).</p>"
    return cards


def _executive_ai_adoption_section(ai_adoption: AIAdoptionAssessment) -> str:
    return f"""
  <p class="callout"><strong>Readiness index: {ai_adoption.readiness_index:.1f}/100</strong>
  &mdash; Recommendation: <strong>
  {_escape(RECOMMENDATION_LABELS[ai_adoption.recommendation])}</strong></p>
  <ul>
    <li>Automation readiness: {ai_adoption.automation_readiness:.1f}/100</li>
    <li>AI maturity: {ai_adoption.ai_maturity:.1f}/100</li>
    <li>Human dependency: {ai_adoption.human_dependency:.1f}/100</li>
    <li>Governance: {ai_adoption.governance_score:.1f}/100</li>
    <li>Explainability: {ai_adoption.explainability_score:.1f}/100</li>
    <li>Rollout complexity: {ai_adoption.rollout_complexity:.1f}/100</li>
  </ul>
"""


def render_executive_html(assessment: ExecutiveAssessment) -> str:
    """Render an `ExecutiveAssessment` as a single standalone HTML report.

    This combines KPI, ROI, SLA, compliance, policy, organizational risk,
    recommendation, and AI adoption sections into one document, mirroring
    `executive_report.generate_executive_report`'s plain-text structure.
    """
    body = f"""
  <h1>Executive Assessment Report</h1>
  <p class="subtitle">{_escape(assessment.workflow_name)}</p>

  <h2>KPI Summary</h2>
  {_executive_kpi_list(assessment.kpi)}

  <h2>ROI</h2>
  {_executive_roi_section(assessment.redesign_diff)}

  <h2>SLA Performance</h2>
  {_executive_sla_section(assessment.sla_report)}

  <h2>Compliance</h2>
  {_executive_compliance_section(assessment.compliance_report)}

  <h2>Policy Violations</h2>
  {_executive_policy_section(assessment.policy_evaluation)}

  <h2>Organizational Risk</h2>
  <p class="callout"><strong>Overall risk score:
  {assessment.risk_assessment.overall_score:.1f}/100</strong></p>
  {_risk_category_table(assessment.risk_assessment)}
  {_risk_factor_list(assessment.risk_assessment)}

  <h2>Recommendations</h2>
  {_executive_recommendation_section(assessment.recommendations)}

  <h2>AI Adoption Assessment</h2>
  {_executive_ai_adoption_section(assessment.ai_adoption)}
"""
    return _page(f"{assessment.workflow_name} - Executive Assessment", body)


__all__ = [
    "render_diff_html",
    "render_portfolio_html",
    "render_monte_carlo_html",
    "render_monte_carlo_comparison_html",
    "render_sensitivity_grid_html",
    "render_capacity_html",
    "render_hiring_html",
    "render_policy_html",
    "render_compliance_html",
    "render_sla_html",
    "render_risk_html",
    "render_recommendation_html",
    "render_ai_adoption_html",
    "render_executive_html",
]
