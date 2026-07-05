"""Executive assessment report: every Phase 5 analysis, in one place.

Where each individual engine (`policy`, `compliance`, `sla`, `risk`,
`recommendation`, `ai_adoption`) answers one question about a workflow,
`build_executive_assessment` runs them together against a single
`Workflow` and `KPIResult` and returns one `ExecutiveAssessment` bundling
every result. `generate_executive_report` and, in `html_report.py`,
`render_executive_html` turn that bundle into a single stakeholder-ready
document covering KPIs, ROI (when a redesign comparison is supplied),
SLA performance, compliance, policy violations, organizational risk,
recommendations, and AI adoption readiness.
"""

from __future__ import annotations

from dataclasses import dataclass

from b2b_workflow_simulator.ai_adoption import (
    RECOMMENDATION_LABELS,
    AIAdoptionAssessment,
    assess_ai_adoption,
)
from b2b_workflow_simulator.compliance import ComplianceReport
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.policy import PolicyEvaluation
from b2b_workflow_simulator.recommendation import (
    RecommendationSet,
    generate_recommendations,
)
from b2b_workflow_simulator.redesign import RedesignDiff
from b2b_workflow_simulator.risk import CATEGORIES, CATEGORY_LABELS, RiskAssessment, compute_risk
from b2b_workflow_simulator.sla import SLAReport
from b2b_workflow_simulator.workflow import Workflow

_TOP_RECOMMENDATIONS = 5
_TOP_RISK_FACTORS = 5


@dataclass
class ExecutiveAssessment:
    """Every Phase 5 analysis result for one workflow, bundled together."""

    workflow_name: str
    kpi: KPIResult
    risk_assessment: RiskAssessment
    recommendations: RecommendationSet
    ai_adoption: AIAdoptionAssessment
    redesign_diff: RedesignDiff | None = None
    policy_evaluation: PolicyEvaluation | None = None
    compliance_report: ComplianceReport | None = None
    sla_report: SLAReport | None = None


def build_executive_assessment(
    workflow: Workflow,
    kpi: KPIResult,
    redesign_diff: RedesignDiff | None = None,
    policy_evaluation: PolicyEvaluation | None = None,
    compliance_report: ComplianceReport | None = None,
    sla_report: SLAReport | None = None,
) -> ExecutiveAssessment:
    """Run every Phase 5 engine for `workflow`/`kpi` and bundle the results.

    `redesign_diff`, `policy_evaluation`, `compliance_report`, and
    `sla_report` are all optional: when supplied, they sharpen the
    corresponding sections of the report (ROI, policy violations,
    compliance, and SLA performance respectively) with real data instead
    of being omitted.
    """
    risk_assessment = compute_risk(workflow, kpi, policy_evaluation, compliance_report)
    recommendations = generate_recommendations(workflow, kpi, risk_assessment)
    ai_adoption = assess_ai_adoption(workflow, kpi, policy_evaluation)
    return ExecutiveAssessment(
        workflow_name=workflow.name,
        kpi=kpi,
        risk_assessment=risk_assessment,
        recommendations=recommendations,
        ai_adoption=ai_adoption,
        redesign_diff=redesign_diff,
        policy_evaluation=policy_evaluation,
        compliance_report=compliance_report,
        sla_report=sla_report,
    )


def _kpi_summary_lines(kpi: KPIResult) -> list[str]:
    return [
        f"Cases simulated: {kpi.total_cases}",
        f"Completion rate: {kpi.completion_rate:.1%}",
        f"Failure rate: {kpi.failure_rate:.1%}",
        f"Total cost: ${kpi.total_cost:,.2f}",
        f"Average cycle time: {kpi.avg_cycle_time_minutes:,.1f} minutes",
        f"Average wait time: {kpi.avg_wait_time_minutes:,.1f} minutes",
        f"Escalation rate: {kpi.escalation_rate:.1%}",
    ]


def _roi_lines(redesign_diff: RedesignDiff | None) -> list[str]:
    if redesign_diff is None:
        return ["No redesign comparison supplied; ROI section omitted."]
    lines = [
        f"Comparing '{redesign_diff.before_name}' against '{redesign_diff.after_name}'.",
        f"Total cost savings: ${redesign_diff.roi.total_cost_savings:,.2f}",
    ]
    if redesign_diff.roi.roi_percentage is not None:
        lines.append(f"ROI: {redesign_diff.roi.roi_percentage:+.1f}%")
    if redesign_diff.roi.implementation_cost is not None:
        lines.append(f"Implementation cost: ${redesign_diff.roi.implementation_cost:,.2f}")
        if redesign_diff.roi.payback_feasible and redesign_diff.roi.payback_in_cases is not None:
            lines.append(f"Payback: ~{redesign_diff.roi.payback_in_cases:,.0f} cases")
        else:
            lines.append("Payback: not reached under simulated assumptions")
    return lines


def _sla_lines(sla_report: SLAReport | None) -> list[str]:
    if sla_report is None:
        return ["No SLA rules supplied; SLA section omitted."]
    lines = [
        f"Attainment rate: {sla_report.attainment_rate:.1%}",
        f"Breaches: {sla_report.breach_count}",
        f"Average breach duration: {sla_report.average_breach_minutes:,.1f} minutes",
    ]
    if sla_report.total_penalty > 0:
        lines.append(f"Estimated financial penalty: ${sla_report.total_penalty:,.2f}")
    return lines


def _compliance_lines(compliance_report: ComplianceReport | None) -> list[str]:
    if compliance_report is None:
        return ["No compliance requirements supplied; compliance section omitted."]
    return [
        f"Compliance score: {compliance_report.compliance_score:.1f}%",
        f"Violations: {compliance_report.violation_count}",
        f"Audit findings: {len(compliance_report.audit_findings)}",
    ]


def _policy_lines(policy_evaluation: PolicyEvaluation | None) -> list[str]:
    if policy_evaluation is None:
        return ["No policies supplied; policy violation section omitted."]
    return [
        f"Policies checked: {policy_evaluation.policies_checked}",
        f"Violations: {policy_evaluation.violation_count} "
        f"({policy_evaluation.error_count} error(s), "
        f"{policy_evaluation.warning_count} warning(s))",
    ]


def _risk_lines(risk_assessment: RiskAssessment) -> list[str]:
    lines = [f"Overall risk score: {risk_assessment.overall_score:.1f}/100"]
    for category in CATEGORIES:
        score = risk_assessment.category_scores.get(category, 0.0)
        lines.append(f"  - {CATEGORY_LABELS[category]}: {score:.1f}/100")
    top_factors = risk_assessment.top_factors(_TOP_RISK_FACTORS)
    if top_factors:
        lines.append("Top risk factors:")
        lines.extend(f"  - {factor.description}" for factor in top_factors)
    return lines


def _recommendation_lines(recommendations: RecommendationSet) -> list[str]:
    if not recommendations.recommendations:
        return ["No actionable recommendations at this time."]
    lines = []
    for index, rec in enumerate(recommendations.recommendations[:_TOP_RECOMMENDATIONS], start=1):
        lines.append(f"{index}. {rec.title} [{rec.confidence} confidence]")
        lines.append(f"   {rec.reasoning}")
    remaining = len(recommendations.recommendations) - _TOP_RECOMMENDATIONS
    if remaining > 0:
        lines.append(f"...and {remaining} more recommendation(s).")
    return lines


def _ai_adoption_lines(ai_adoption: AIAdoptionAssessment) -> list[str]:
    return [
        f"Readiness index: {ai_adoption.readiness_index:.1f}/100",
        f"Recommendation: {RECOMMENDATION_LABELS[ai_adoption.recommendation]}",
        f"Automation readiness: {ai_adoption.automation_readiness:.1f}/100",
        f"AI maturity: {ai_adoption.ai_maturity:.1f}/100",
        f"Human dependency: {ai_adoption.human_dependency:.1f}/100",
        f"Governance: {ai_adoption.governance_score:.1f}/100",
        f"Explainability: {ai_adoption.explainability_score:.1f}/100",
        f"Rollout complexity: {ai_adoption.rollout_complexity:.1f}/100",
    ]


def generate_executive_report(assessment: ExecutiveAssessment) -> str:
    """Render `assessment` as a single plain-text executive report."""
    sections = [
        "=" * 60,
        f"EXECUTIVE ASSESSMENT REPORT: {assessment.workflow_name}",
        "=" * 60,
        "",
        "KPI SUMMARY",
        "-" * 60,
        *_kpi_summary_lines(assessment.kpi),
        "",
        "ROI",
        "-" * 60,
        *_roi_lines(assessment.redesign_diff),
        "",
        "SLA PERFORMANCE",
        "-" * 60,
        *_sla_lines(assessment.sla_report),
        "",
        "COMPLIANCE",
        "-" * 60,
        *_compliance_lines(assessment.compliance_report),
        "",
        "POLICY VIOLATIONS",
        "-" * 60,
        *_policy_lines(assessment.policy_evaluation),
        "",
        "ORGANIZATIONAL RISK",
        "-" * 60,
        *_risk_lines(assessment.risk_assessment),
        "",
        "RECOMMENDATIONS",
        "-" * 60,
        *_recommendation_lines(assessment.recommendations),
        "",
        "AI ADOPTION ASSESSMENT",
        "-" * 60,
        *_ai_adoption_lines(assessment.ai_adoption),
    ]
    return "\n".join(sections)


__all__ = [
    "ExecutiveAssessment",
    "build_executive_assessment",
    "generate_executive_report",
]
