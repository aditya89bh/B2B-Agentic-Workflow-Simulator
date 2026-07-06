"""Organizational health score: a single composite signal across 8 dimensions.

The org health score summarizes how well an organization is positioned
to execute its workflows reliably, efficiently, and safely.  Each of the
eight dimensions addresses a distinct failure mode seen in real
transformations:

1. **Utilization balance** — Are actors spread evenly, or is one team
   drowning while another is idle?
2. **Queue pressure** — How much time do cases spend waiting vs. working?
3. **Budget pressure** — Is the organization spending within its means?
4. **Compliance risk** — Are workflows structurally compliant?
5. **SLA risk** — Are service-level targets being met?
6. **AI readiness** — How prepared is the org to adopt AI agents?
7. **Single points of failure** — Does the org rely on actors with no
   backup?
8. **Cross-team dependency load** — How many workflows span multiple
   teams, creating coordination overhead?

Each dimension produces a 0-100 score where **higher is healthier**.
The overall health score is the weighted average.  A grade is derived
from the overall score: A (≥90), B (≥80), C (≥70), D (≥60), F (<60).
"""

from __future__ import annotations

from dataclasses import dataclass

from b2b_workflow_simulator.budget import OrgBudget
from b2b_workflow_simulator.growth import GrowthProjection
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.org_model import Organization
from b2b_workflow_simulator.shared_resources import SharedResourcePool

UTILIZATION_BALANCE = "utilization_balance"
QUEUE_PRESSURE = "queue_pressure"
BUDGET_PRESSURE = "budget_pressure"
COMPLIANCE_RISK = "compliance_risk"
SLA_RISK = "sla_risk"
AI_READINESS = "ai_readiness"
SINGLE_POINT_OF_FAILURE = "single_point_of_failure"
CROSS_TEAM_DEPENDENCY = "cross_team_dependency"

HEALTH_FACTORS = (
    UTILIZATION_BALANCE,
    QUEUE_PRESSURE,
    BUDGET_PRESSURE,
    COMPLIANCE_RISK,
    SLA_RISK,
    AI_READINESS,
    SINGLE_POINT_OF_FAILURE,
    CROSS_TEAM_DEPENDENCY,
)

HEALTH_FACTOR_LABELS: dict[str, str] = {
    UTILIZATION_BALANCE: "Utilization Balance",
    QUEUE_PRESSURE: "Queue Pressure",
    BUDGET_PRESSURE: "Budget Pressure",
    COMPLIANCE_RISK: "Compliance Risk",
    SLA_RISK: "SLA Risk",
    AI_READINESS: "AI Readiness",
    SINGLE_POINT_OF_FAILURE: "Single Points of Failure",
    CROSS_TEAM_DEPENDENCY: "Cross-Team Dependency Load",
}

_FACTOR_WEIGHTS: dict[str, float] = {
    UTILIZATION_BALANCE: 1.5,
    QUEUE_PRESSURE: 1.5,
    BUDGET_PRESSURE: 1.0,
    COMPLIANCE_RISK: 1.0,
    SLA_RISK: 1.0,
    AI_READINESS: 1.0,
    SINGLE_POINT_OF_FAILURE: 1.5,
    CROSS_TEAM_DEPENDENCY: 0.5,
}

_GRADES = ((90.0, "A"), (80.0, "B"), (70.0, "C"), (60.0, "D"))


@dataclass(frozen=True)
class HealthFactor:
    """A single health dimension score with its explanation.

    Attributes:
        factor_id: One of the ``HEALTH_FACTORS`` constants.
        name: Human-readable dimension name.
        score: 0-100 health score for this dimension (higher = healthier).
        weight: Relative weight in the overall score.
        explanation: Plain-text explanation of how this score was derived.
    """

    factor_id: str
    name: str
    score: float
    weight: float
    explanation: str

    @property
    def weighted_score(self) -> float:
        """Score multiplied by weight."""
        return self.score * self.weight


@dataclass
class OrgHealthScore:
    """Composite health score for an organization.

    Attributes:
        org_id: The organization this score covers.
        org_name: Human-readable organization name.
        factors: The eight :class:`HealthFactor` objects.
    """

    org_id: str
    org_name: str
    factors: list[HealthFactor]

    @property
    def overall_score(self) -> float:
        """Weighted-average health score (0-100)."""
        total_weight = sum(f.weight for f in self.factors)
        if total_weight == 0:
            return 0.0
        return sum(f.weighted_score for f in self.factors) / total_weight

    @property
    def grade(self) -> str:
        """Letter grade derived from ``overall_score``."""
        score = self.overall_score
        for threshold, letter in _GRADES:
            if score >= threshold:
                return letter
        return "F"

    @property
    def summary(self) -> str:
        """One-sentence summary combining score, grade, and top risk."""
        top = self.top_risks(1)
        top_risk_name = top[0].name if top else "no critical risks"
        return (
            f"{self.org_name} scores {self.overall_score:.1f}/100 (grade {self.grade}); "
            f"the largest health risk is {top_risk_name}."
        )

    def top_risks(self, n: int = 3) -> list[HealthFactor]:
        """Return the ``n`` lowest-scoring health factors (worst first)."""
        return sorted(self.factors, key=lambda f: f.score)[:n]

    def factor(self, factor_id: str) -> HealthFactor | None:
        """Return the factor with the given ``factor_id``, or ``None``."""
        for f in self.factors:
            if f.factor_id == factor_id:
                return f
        return None


def _utilization_balance_score(kpi_results: dict[str, KPIResult]) -> tuple[float, str]:
    """Score 0-100: how balanced is actor utilization across all workflows?

    Penalises both overload (>90%) and underuse (<30%).
    """
    all_utils: list[float] = []
    for kpi in kpi_results.values():
        all_utils.extend(kpi.actor_utilization.values())
        all_utils.extend(kpi.pool_utilization.values())
    if not all_utils:
        return 70.0, "No capacity utilization data available; default score applied."
    overloaded = sum(1 for u in all_utils if u > 0.9)
    underused = sum(1 for u in all_utils if u < 0.3)
    total = len(all_utils)
    penalty = ((overloaded + underused) / total) * 100.0
    score = max(0.0, 100.0 - penalty)
    explanation = (
        f"{overloaded}/{total} actor(s) overloaded (>90%), "
        f"{underused}/{total} underutilized (<30%)."
    )
    return score, explanation


def _queue_pressure_score(kpi_results: dict[str, KPIResult]) -> tuple[float, str]:
    """Score 0-100: how much time do cases spend waiting vs. working?"""
    total_duration = sum(kpi.total_duration_minutes for kpi in kpi_results.values())
    total_wait = sum(kpi.total_wait_minutes for kpi in kpi_results.values())
    if total_duration == 0:
        return 75.0, "No duration data available; default score applied."
    wait_fraction = total_wait / total_duration
    score = max(0.0, 100.0 - wait_fraction * 200.0)
    explanation = (
        f"Total wait time is {total_wait:,.0f} min out of "
        f"{total_duration:,.0f} min total duration "
        f"({wait_fraction:.1%} wait fraction)."
    )
    return score, explanation


def _budget_pressure_score(org_budget: OrgBudget | None) -> tuple[float, str]:
    """Score 0-100: how healthy is the budget position?"""
    if org_budget is None:
        return 75.0, "No budget data provided; default score applied."
    pressure = org_budget.budget_pressure_score()
    score = max(0.0, 100.0 - pressure)
    overruns = org_budget.overrun_departments()
    explanation = (
        f"Overall budget utilization: {org_budget.overall_utilization:.1%}. "
        + (f"{len(overruns)} department(s) over budget." if overruns else "No overruns.")
    )
    return score, explanation


def _compliance_risk_score(kpi_results: dict[str, KPIResult]) -> tuple[float, str]:
    """Score 0-100: proxy for structural compliance risk from KPI signals."""
    total_failures = sum(kpi.failed_cases for kpi in kpi_results.values())
    total_cases = sum(kpi.total_cases for kpi in kpi_results.values())
    if total_cases == 0:
        return 75.0, "No case data available; default score applied."
    failure_rate = total_failures / total_cases
    score = max(0.0, 100.0 - failure_rate * 150.0)
    explanation = (
        f"Across all workflows, {total_failures}/{total_cases} cases failed "
        f"({failure_rate:.1%} failure rate)."
    )
    return score, explanation


def _sla_risk_score(kpi_results: dict[str, KPIResult]) -> tuple[float, str]:
    """Score 0-100: proxy for SLA risk based on average cycle time distribution."""
    all_avg_cts: list[float] = [
        kpi.avg_cycle_time_minutes for kpi in kpi_results.values() if kpi.total_cases > 0
    ]
    if not all_avg_cts:
        return 75.0, "No cycle time data available; default score applied."
    max_ct = max(all_avg_cts)
    escalation_total = sum(kpi.total_escalations for kpi in kpi_results.values())
    total_cases = sum(kpi.total_cases for kpi in kpi_results.values())
    esc_rate = escalation_total / total_cases if total_cases > 0 else 0.0
    score = max(0.0, 100.0 - esc_rate * 100.0 - (max_ct / 1000.0) * 5.0)
    explanation = (
        f"Peak average cycle time: {max_ct:,.1f} min. "
        f"Escalation rate: {esc_rate:.1%}."
    )
    return score, explanation


def _ai_readiness_score(org: Organization, kpi_results: dict[str, KPIResult]) -> tuple[float, str]:
    """Score 0-100: how ready is the org to adopt AI agents?"""
    ai_roles = org.ai_agent_count()
    total_roles = org.total_headcount()
    ai_fraction = ai_roles / total_roles if total_roles > 0 else 0.0
    total_escalations = sum(kpi.total_escalations for kpi in kpi_results.values())
    total_cases = sum(kpi.total_cases for kpi in kpi_results.values())
    esc_rate = total_escalations / total_cases if total_cases > 0 else 0.0
    readiness = (ai_fraction * 50.0) + max(0.0, 50.0 - esc_rate * 100.0)
    score = min(100.0, max(0.0, readiness))
    explanation = (
        f"{ai_roles}/{total_roles} roles are AI agents ({ai_fraction:.1%}). "
        f"AI escalation rate: {esc_rate:.1%}."
    )
    return score, explanation


def _spof_score(org: Organization, kpi_results: dict[str, KPIResult]) -> tuple[float, str]:
    """Score 0-100: inverse of single-point-of-failure exposure.

    A SPOF actor is one with no peer (only one actor covers a node
    across all workflows) AND high utilization.
    """
    all_actor_utils: dict[str, float] = {}
    for kpi in kpi_results.values():
        for actor_id, util in kpi.actor_utilization.items():
            all_actor_utils[actor_id] = max(all_actor_utils.get(actor_id, 0.0), util)

    spof_count = sum(1 for u in all_actor_utils.values() if u > 0.8)
    total = len(all_actor_utils)
    if total == 0:
        return 80.0, "No utilization data available; default score applied."
    spof_fraction = spof_count / total
    score = max(0.0, 100.0 - spof_fraction * 150.0)
    explanation = (
        f"{spof_count}/{total} actor(s) have >80% utilization and represent "
        "potential single points of failure."
    )
    return score, explanation


def _cross_team_dependency_score(org: Organization) -> tuple[float, str]:
    """Score 0-100: lower dependency load between teams is healthier."""
    n_teams = len(org.teams)
    n_workflows = len(org.workflow_ids)
    if n_teams == 0 or n_workflows == 0:
        return 80.0, "No cross-team dependency data available; default score applied."
    team_per_workflow = n_workflows / max(n_teams, 1)
    score = min(100.0, max(0.0, 100.0 - (team_per_workflow - 1.0) * 20.0))
    explanation = (
        f"{n_workflows} workflow(s) span {n_teams} team(s) "
        f"({team_per_workflow:.1f} workflows/team on average)."
    )
    return score, explanation


def compute_org_health(
    org: Organization,
    org_budget: OrgBudget | None,
    shared_resources: SharedResourcePool | None,
    kpi_results: dict[str, KPIResult],
    growth_projection: GrowthProjection | None = None,
) -> OrgHealthScore:
    """Compute the organizational health score across all 8 dimensions.

    Args:
        org: The organization to score.
        org_budget: Optional budget model; improves budget pressure
            accuracy when provided.
        shared_resources: Optional shared resource pool; not currently
            used in scoring but reserved for future refinement.
        kpi_results: KPI results keyed by workflow ID, used for
            utilization, queue pressure, compliance proxy, and SLA proxy.
        growth_projection: Optional growth forecast; reserved for future
            refinement.

    Returns:
        An :class:`OrgHealthScore` with 8 :class:`HealthFactor` objects.
    """
    factor_data = [
        (UTILIZATION_BALANCE, _utilization_balance_score(kpi_results)),
        (QUEUE_PRESSURE, _queue_pressure_score(kpi_results)),
        (BUDGET_PRESSURE, _budget_pressure_score(org_budget)),
        (COMPLIANCE_RISK, _compliance_risk_score(kpi_results)),
        (SLA_RISK, _sla_risk_score(kpi_results)),
        (AI_READINESS, _ai_readiness_score(org, kpi_results)),
        (SINGLE_POINT_OF_FAILURE, _spof_score(org, kpi_results)),
        (CROSS_TEAM_DEPENDENCY, _cross_team_dependency_score(org)),
    ]
    factors = [
        HealthFactor(
            factor_id=fid,
            name=HEALTH_FACTOR_LABELS[fid],
            score=score,
            weight=_FACTOR_WEIGHTS[fid],
            explanation=explanation,
        )
        for fid, (score, explanation) in factor_data
    ]
    return OrgHealthScore(org_id=org.org_id, org_name=org.name, factors=factors)


def generate_org_health_report(health_score: OrgHealthScore) -> str:
    """Render an :class:`OrgHealthScore` as a plain-text report.

    Args:
        health_score: A computed org health score.

    Returns:
        A multi-line plain-text report string.
    """
    lines: list[str] = [
        "=" * 60,
        f"ORGANIZATIONAL HEALTH SCORE: {health_score.org_name}",
        "=" * 60,
        "",
        f"Overall score: {health_score.overall_score:.1f}/100  Grade: {health_score.grade}",
        f"Summary: {health_score.summary}",
        "",
        "Dimension Scores:",
        "-" * 60,
    ]
    for factor in sorted(health_score.factors, key=lambda f: f.score):
        lines.append(f"  {factor.name:<32} {factor.score:>6.1f}/100")
        lines.append(f"    {factor.explanation}")
    lines += [
        "",
        "Top Risks:",
        "-" * 60,
    ]
    for i, risk in enumerate(health_score.top_risks(3), start=1):
        lines.append(f"  {i}. {risk.name}: {risk.score:.1f}/100 — {risk.explanation}")
    return "\n".join(lines)


__all__ = [
    "AI_READINESS",
    "BUDGET_PRESSURE",
    "COMPLIANCE_RISK",
    "CROSS_TEAM_DEPENDENCY",
    "HEALTH_FACTOR_LABELS",
    "HEALTH_FACTORS",
    "HealthFactor",
    "OrgHealthScore",
    "QUEUE_PRESSURE",
    "SLA_RISK",
    "SINGLE_POINT_OF_FAILURE",
    "UTILIZATION_BALANCE",
    "compute_org_health",
    "generate_org_health_report",
]
