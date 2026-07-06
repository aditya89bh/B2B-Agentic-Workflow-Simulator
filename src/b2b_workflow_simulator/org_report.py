"""Organizational digital twin reports: plain-text and HTML.

`generate_org_digital_twin_report` assembles all Phase 6 analysis
results into a single multi-section plain-text document.  Its HTML
counterpart lives in ``html_report.py`` as ``render_org_executive_html``.

The report structure follows the same pattern as Phase 5's
``executive_report.py``: build a bundle dataclass, render to text or
HTML, keep each renderer as a pure function of its input.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.budget import BUDGET_CATEGORY_LABELS, OrgBudget
from b2b_workflow_simulator.cross_workflow import CrossWorkflowResult
from b2b_workflow_simulator.growth import GrowthProjection
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.org_health import OrgHealthScore
from b2b_workflow_simulator.org_model import Organization
from b2b_workflow_simulator.restructuring import RestructuringImpact
from b2b_workflow_simulator.shared_resources import SharedResourcePool


@dataclass
class OrgDigitalTwinReport:
    """All Phase 6 analysis results for one organization, bundled together."""

    org: Organization
    kpi_results: dict[str, KPIResult] = field(default_factory=dict)
    org_budget: OrgBudget | None = None
    shared_resources: SharedResourcePool | None = None
    health_score: OrgHealthScore | None = None
    growth_projection: GrowthProjection | None = None
    restructuring_impacts: list[RestructuringImpact] = field(default_factory=list)
    cross_workflow_result: CrossWorkflowResult | None = None


def _org_structure_lines(org: Organization) -> list[str]:
    lines = [
        f"Organization: {org.name}  (id: {org.org_id})",
        f"  Departments:  {len(org.departments)}",
        f"  Teams:        {len(org.teams)}",
        f"  Roles:        {org.total_headcount()}  "
        f"({org.ai_agent_count()} AI agent(s), {org.manager_count()} manager(s))",
        f"  Workflows:    {len(org.workflow_ids)}",
    ]
    for dept in org.departments.values():
        teams = org.teams_for_department(dept.dept_id)
        headcount = org.department_headcount(dept.dept_id)
        lines.append(f"  ├─ {dept.name}  ({headcount} role(s), {len(teams)} team(s))")
    return lines


def _budget_lines(org_budget: OrgBudget | None) -> list[str]:
    if org_budget is None:
        return ["No budget data provided."]
    lines = [
        f"Total annual budget:   ${org_budget.total_budget:,.0f}",
        f"Total spent:           ${org_budget.total_spent:,.0f}",
        f"Remaining:             ${org_budget.total_remaining:,.0f}",
        f"Overall utilization:   {org_budget.overall_utilization:.1%}",
    ]
    overruns = org_budget.overrun_departments()
    if overruns:
        lines.append(f"Departments over budget: {', '.join(overruns)}")
    spend_by_cat = org_budget.spend_by_category()
    if spend_by_cat:
        lines.append("Spend by category:")
        for cat, amount in sorted(spend_by_cat.items(), key=lambda x: x[1], reverse=True):
            label = BUDGET_CATEGORY_LABELS.get(cat, cat)
            lines.append(f"  {label}: ${amount:,.0f}")
    return lines


def _resource_contention_lines(shared_resources: SharedResourcePool | None) -> list[str]:
    if shared_resources is None:
        return ["No shared resource data provided."]
    contentions = shared_resources.all_contentions()
    if not contentions:
        return ["No shared resources registered."]
    lines: list[str] = []
    for c in contentions[:5]:
        lines.append(
            f"  {c.resource_name:<30} ratio: {c.contention_ratio:.2f}  "
            f"risk: {c.overload_risk.upper()}"
        )
    bottlenecks = shared_resources.bottleneck_resources()
    if bottlenecks:
        names = ", ".join(c.resource_name for c in bottlenecks)
        lines.append(f"Bottleneck resources (demand > capacity): {names}")
    return lines


def _workflow_kpi_lines(kpi_results: dict[str, KPIResult]) -> list[str]:
    if not kpi_results:
        return ["No simulation results provided."]
    lines: list[str] = []
    for wf_id, kpi in kpi_results.items():
        lines.append(
            f"  {wf_id:<38} completion: {kpi.completion_rate:.1%}  "
            f"cost/case: ${kpi.avg_cost_per_case:,.2f}  "
            f"cycle: {kpi.avg_cycle_time_minutes:,.0f} min"
        )
    return lines


def _restructuring_summary_lines(impacts: list[RestructuringImpact]) -> list[str]:
    if not impacts:
        return ["No restructuring scenarios evaluated."]
    lines: list[str] = []
    for rank, impact in enumerate(impacts[:3], start=1):
        direction = "saves" if impact.is_cost_positive else "costs"
        amount = abs(impact.cost_impact)
        lines.append(
            f"  {rank}. {impact.scenario.description[:50]}: "
            f"{direction} ${amount:,.0f}/yr  risk Δ: {impact.risk_delta:+.1f}"
        )
    return lines


def _rollout_roadmap_lines(
    health_score: OrgHealthScore | None, impacts: list[RestructuringImpact]
) -> list[str]:
    lines: list[str] = []
    if health_score is not None:
        risks = health_score.top_risks(3)
        lines.append("Priority areas based on health score:")
        for i, risk in enumerate(risks, start=1):
            lines.append(f"  {i}. Address '{risk.name}' (score {risk.score:.0f}/100)")
    if impacts:
        lines.append("Top restructuring recommendation:")
        best = impacts[0]
        lines.append(f"  Consider: {best.scenario.description}")
        if best.recommendations:
            lines.append(f"  Next step: {best.recommendations[0]}")
    return lines


def generate_org_digital_twin_report(report: OrgDigitalTwinReport) -> str:
    """Render all Phase 6 analysis results as a single plain-text document.

    Args:
        report: A populated :class:`OrgDigitalTwinReport` bundle.

    Returns:
        A multi-line plain-text report string.
    """
    org = report.org
    sections: list[str] = [
        "=" * 60,
        f"ORGANIZATIONAL DIGITAL TWIN: {org.name}",
        "=" * 60,
        "",
        "ORGANIZATIONAL STRUCTURE",
        "-" * 60,
        *_org_structure_lines(org),
        "",
        "WORKFLOW SIMULATION RESULTS",
        "-" * 60,
        *_workflow_kpi_lines(report.kpi_results),
        "",
        "BUDGET ANALYSIS",
        "-" * 60,
        *_budget_lines(report.org_budget),
        "",
        "SHARED RESOURCE CONTENTION",
        "-" * 60,
        *_resource_contention_lines(report.shared_resources),
    ]

    if report.health_score is not None:
        sections += [
            "",
            "ORGANIZATIONAL HEALTH",
            "-" * 60,
            f"Overall score: {report.health_score.overall_score:.1f}/100  "
            f"Grade: {report.health_score.grade}",
            report.health_score.summary,
        ]

    if report.restructuring_impacts:
        sections += [
            "",
            "RESTRUCTURING SCENARIOS (TOP 3)",
            "-" * 60,
            *_restructuring_summary_lines(report.restructuring_impacts),
        ]

    if report.growth_projection is not None:
        first_bp = report.growth_projection.first_breaking_point()
        sections += [
            "",
            "GROWTH PROJECTION",
            "-" * 60,
            f"Base cases/month: {report.growth_projection.config.base_cases_per_month}  "
            f"Growth rate: {report.growth_projection.config.monthly_growth_rate:.1%}/month",
        ]
        if first_bp:
            sections.append(
                f"Breaking point detected at month {first_bp.month}: "
                f"{first_bp.breaking_point_reason}"
            )
        else:
            sections.append("No breaking points detected within 12-month horizon.")

    sections += [
        "",
        "ROLLOUT ROADMAP",
        "-" * 60,
        *_rollout_roadmap_lines(report.health_score, report.restructuring_impacts),
    ]

    return "\n".join(sections)


__all__ = [
    "OrgDigitalTwinReport",
    "generate_org_digital_twin_report",
]
