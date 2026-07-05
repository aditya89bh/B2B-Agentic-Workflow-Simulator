"""Plain-text ROI report generation from a `RedesignDiff` or `WorkflowPortfolio`."""

from __future__ import annotations

from b2b_workflow_simulator.portfolio import WorkflowPortfolio
from b2b_workflow_simulator.redesign import MetricDelta, RedesignDiff

_PERCENT_METRICS = {"Completion rate", "Failure rate", "Escalation rate"}
_CURRENCY_METRICS = {"Total cost", "Cost per case"}


def format_metric_value(metric: MetricDelta, value: float) -> str:
    if metric.label in _PERCENT_METRICS:
        return f"{value:.1%}"
    if metric.label in _CURRENCY_METRICS:
        return f"${value:,.2f}"
    return f"{value:,.1f}"


def format_percent_change(metric: MetricDelta) -> str:
    if metric.percent_change is None:
        return "n/a"
    return f"{metric.percent_change:+.1f}%"


def _build_executive_summary(diff: RedesignDiff) -> list[str]:
    lines = [
        f"Comparing '{diff.before_name}' against '{diff.after_name}'.",
        (
            f"Completion rate moves from {diff.completion_rate.before:.1%} to "
            f"{diff.completion_rate.after:.1%}, and average cost per case moves from "
            f"${diff.cost_per_case.before:,.2f} to ${diff.cost_per_case.after:,.2f}."
        ),
    ]
    if diff.roi.roi_percentage is not None:
        direction = "reduces" if diff.roi.total_cost_savings >= 0 else "increases"
        lines.append(
            f"The redesign {direction} total simulated cost by "
            f"{abs(diff.roi.roi_percentage):.1f}% (${abs(diff.roi.total_cost_savings):,.2f} "
            "across the simulated case volume)."
        )
    if diff.roi.implementation_cost is not None:
        if diff.roi.payback_feasible and diff.roi.payback_in_cases is not None:
            lines.append(
                f"At an implementation cost of ${diff.roi.implementation_cost:,.2f}, payback "
                f"is reached after approximately {diff.roi.payback_in_cases:,.0f} cases."
            )
        else:
            lines.append(
                f"At an implementation cost of ${diff.roi.implementation_cost:,.2f}, the "
                "redesign does not recover its cost under the simulated assumptions."
            )
    return lines


def _build_kpi_table(diff: RedesignDiff) -> list[str]:
    header = f"{'Metric':<22}{'Before':>16}{'After':>16}{'Change':>14}"
    lines = [header, "-" * len(header)]
    for metric in diff.metrics:
        before_str = format_metric_value(metric, metric.before)
        after_str = format_metric_value(metric, metric.after)
        change_str = format_percent_change(metric)
        lines.append(f"{metric.label:<22}{before_str:>16}{after_str:>16}{change_str:>14}")
    return lines


def _build_bottlenecks_section(diff: RedesignDiff) -> list[str]:
    lines = ["Before (top time-consuming stages):"]
    for node_id, minutes in diff.before_bottlenecks:
        lines.append(f"  - {node_id}: {minutes:,.1f} minutes")
    lines.append("After (top time-consuming stages):")
    for node_id, minutes in diff.after_bottlenecks:
        lines.append(f"  - {node_id}: {minutes:,.1f} minutes")
    return lines


def _build_utilization_section(diff: RedesignDiff) -> list[str]:
    lines = []
    if diff.before_utilization:
        lines.append("Before:")
        for actor_id, utilization in sorted(diff.before_utilization.items()):
            lines.append(f"  - {actor_id}: {utilization:.1%}")
    if diff.after_utilization:
        lines.append("After:")
        for actor_id, utilization in sorted(diff.after_utilization.items()):
            lines.append(f"  - {actor_id}: {utilization:.1%}")
    if not lines:
        lines.append("No capacity data available (run with arrival_interval_minutes set).")
    return lines


def build_risks(diff: RedesignDiff) -> list[str]:
    risks = []
    if diff.failure_rate.delta > 0:
        risks.append(
            f"Failure rate increases by {diff.failure_rate.delta:.1%} in the redesign; "
            "confirm the root cause before rollout."
        )
    if diff.escalation_rate.after > 0.2:
        risks.append(
            f"AI escalation rate is {diff.escalation_rate.after:.1%} in the redesign; "
            "ensure enough human capacity is staffed to absorb escalations."
        )
    for actor_id, utilization in diff.after_utilization.items():
        if utilization > 0.9:
            risks.append(
                f"Actor '{actor_id}' is projected at {utilization:.1%} utilization after "
                "the redesign; this stage may become a new bottleneck under peak load."
            )
    if diff.completion_rate.delta < 0:
        risks.append(
            f"Completion rate drops by {abs(diff.completion_rate.delta):.1%} in the redesign; "
            "validate that this trade-off is acceptable."
        )
    if not risks:
        risks.append("No material risks identified from the simulated metrics.")
    return risks


def build_recommendation(diff: RedesignDiff) -> str:
    cost_improved = diff.roi.total_cost_savings > 0
    quality_maintained = diff.completion_rate.delta >= 0 and diff.failure_rate.delta <= 0
    payback_ok = diff.roi.implementation_cost is None or diff.roi.payback_feasible

    if cost_improved and quality_maintained and payback_ok:
        return (
            "Recommend proceeding with a pilot rollout. The redesign reduces cost and "
            "cycle time without degrading completion or failure rates."
        )
    if cost_improved and not quality_maintained:
        return (
            "Recommend a limited pilot with close monitoring. The redesign reduces cost, "
            "but completion or failure rates move in the wrong direction and should be "
            "validated with real data before a full rollout."
        )
    if not cost_improved:
        return (
            "Recommend further redesign iteration before adoption. The simulated "
            "redesign does not produce a net cost improvement under current assumptions."
        )
    return "Recommend a limited pilot to validate results before a full rollout."


def generate_report(diff: RedesignDiff) -> str:
    """Render a `RedesignDiff` as a plain-text report for non-technical stakeholders.

    The report is organized into sections a consultant or operations
    leader can skim independently: an executive summary, a full KPI delta
    table, bottleneck stages before and after, actor utilization, risks
    surfaced from the simulated metrics, and a closing recommendation.
    """
    sections = [
        "=" * 60,
        "WORKFLOW REDESIGN ANALYSIS",
        "=" * 60,
        "",
        "EXECUTIVE SUMMARY",
        "-" * 60,
        *_build_executive_summary(diff),
        "",
        "KPI COMPARISON",
        "-" * 60,
        *_build_kpi_table(diff),
        "",
        "BOTTLENECKS",
        "-" * 60,
        *_build_bottlenecks_section(diff),
        "",
        "ACTOR UTILIZATION",
        "-" * 60,
        *_build_utilization_section(diff),
        "",
        "RISKS",
        "-" * 60,
        *[f"  - {risk}" for risk in build_risks(diff)],
        "",
        "RECOMMENDATION",
        "-" * 60,
        build_recommendation(diff),
    ]
    return "\n".join(sections)


def _build_portfolio_executive_summary(portfolio: WorkflowPortfolio) -> list[str]:
    summary = portfolio.summary()
    lines = [
        f"Portfolio '{portfolio.name}' covers {summary.workflow_count} workflow "
        f"redesign(s) evaluated together."
    ]
    if summary.total_before_cost > 0:
        direction = "reduce" if summary.total_cost_savings >= 0 else "increase"
        lines.append(
            f"Across the simulated volumes, the redesigns {direction} total cost by "
            f"${abs(summary.total_cost_savings):,.2f}"
            + (
                f" ({abs(summary.portfolio_roi_percentage):.1f}%)."
                if summary.portfolio_roi_percentage is not None
                else "."
            )
        )
    if summary.total_wait_minutes_saved != 0:
        direction = "falls" if summary.total_wait_minutes_saved >= 0 else "rises"
        lines.append(
            f"Total customer/case wait time {direction} by "
            f"{abs(summary.total_wait_minutes_saved):,.1f} minutes across the portfolio."
        )
    if summary.total_implementation_cost > 0:
        if summary.payback_feasible and summary.payback_in_periods is not None:
            lines.append(
                f"At a combined implementation cost of ${summary.total_implementation_cost:,.2f}, "
                f"the portfolio pays back in approximately {summary.payback_in_periods:.2f} "
                "simulated case-volume periods (e.g. months, if each workflow was simulated "
                "at its typical monthly volume)."
            )
        else:
            lines.append(
                f"At a combined implementation cost of ${summary.total_implementation_cost:,.2f}, "
                "the portfolio does not recover its cost under the simulated assumptions."
            )
    return lines


def _build_portfolio_ranking_table(portfolio: WorkflowPortfolio, by: str) -> list[str]:
    ranked = portfolio.ranked(by=by)
    name_width = max([len("Workflow")] + [len(entry.name) for entry in ranked]) + 2
    header = f"{'Rank':<6}{'Workflow':<{name_width}}{'Cost Savings':>16}{'ROI %':>10}"
    lines = [header, "-" * len(header)]
    for rank, entry in enumerate(ranked, start=1):
        savings = f"${entry.diff.roi.total_cost_savings:,.2f}"
        roi = (
            f"{entry.diff.roi.roi_percentage:+.1f}%"
            if entry.diff.roi.roi_percentage is not None
            else "n/a"
        )
        lines.append(f"{rank:<6}{entry.name:<{name_width}}{savings:>16}{roi:>10}")
    return lines


def _build_portfolio_aggregate_section(portfolio: WorkflowPortfolio) -> list[str]:
    summary = portfolio.summary()
    lines = [
        f"Total before cost:        ${summary.total_before_cost:,.2f}",
        f"Total after cost:         ${summary.total_after_cost:,.2f}",
        f"Total cost savings:       ${summary.total_cost_savings:,.2f}",
        (
            f"Portfolio ROI:            {summary.portfolio_roi_percentage:+.1f}%"
            if summary.portfolio_roi_percentage is not None
            else "Portfolio ROI:            n/a"
        ),
        f"Total wait time saved:    {summary.total_wait_minutes_saved:,.1f} minutes",
    ]
    if summary.total_implementation_cost > 0:
        lines.append(f"Total implementation cost: ${summary.total_implementation_cost:,.2f}")
        lines.append(
            f"Payback (case-volume periods): {summary.payback_in_periods:.2f}"
            if summary.payback_feasible and summary.payback_in_periods is not None
            else "Payback (case-volume periods): not reached"
        )
    return lines


def _build_portfolio_risks_section(portfolio: WorkflowPortfolio) -> list[str]:
    lines = []
    for entry in portfolio.entries:
        for risk in build_risks(entry.diff):
            if risk == "No material risks identified from the simulated metrics.":
                continue
            lines.append(f"[{entry.name}] {risk}")
    if not lines:
        lines.append("No material risks identified from the simulated metrics.")
    return lines


def _build_rollout_order_section(portfolio: WorkflowPortfolio, by: str) -> list[str]:
    lines = []
    for rank, entry in enumerate(portfolio.ranked(by=by), start=1):
        lines.append(
            f"{rank}. {entry.name} "
            f"(${entry.diff.roi.total_cost_savings:,.2f} savings, "
            f"{entry.diff.roi.roi_percentage:+.1f}% ROI)"
            if entry.diff.roi.roi_percentage is not None
            else f"{rank}. {entry.name} (${entry.diff.roi.total_cost_savings:,.2f} savings)"
        )
    return lines


def generate_portfolio_report(
    portfolio: WorkflowPortfolio, rank_by: str = "total_cost_savings"
) -> str:
    """Render a `WorkflowPortfolio` as a plain-text report for stakeholders.

    The report ranks workflows by `rank_by` (see
    `b2b_workflow_simulator.portfolio.RANK_BY_OPTIONS`), then presents an
    executive summary, the ranking table, aggregate ROI and payback,
    consolidated risks from every workflow, and a recommended rollout
    order matching the ranking.
    """
    sections = [
        "=" * 60,
        "WORKFLOW PORTFOLIO ANALYSIS",
        "=" * 60,
        "",
        "EXECUTIVE SUMMARY",
        "-" * 60,
        *_build_portfolio_executive_summary(portfolio),
        "",
        "WORKFLOW RANKING",
        "-" * 60,
        *_build_portfolio_ranking_table(portfolio, rank_by),
        "",
        "AGGREGATE ROI & PAYBACK",
        "-" * 60,
        *_build_portfolio_aggregate_section(portfolio),
        "",
        "RISKS",
        "-" * 60,
        *[f"  - {risk}" for risk in _build_portfolio_risks_section(portfolio)],
        "",
        "RECOMMENDED ROLLOUT ORDER",
        "-" * 60,
        *_build_rollout_order_section(portfolio, rank_by),
    ]
    return "\n".join(sections)


__all__ = [
    "generate_report",
    "generate_portfolio_report",
    "format_metric_value",
    "format_percent_change",
    "build_risks",
    "build_recommendation",
]
