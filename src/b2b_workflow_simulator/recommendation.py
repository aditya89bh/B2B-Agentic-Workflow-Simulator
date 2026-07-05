"""Recommendation engine: turn KPIs and structure into actionable advice.

Where `kpi.py` and `risk.py` report *what* is happening, this module
explains *what to do about it*. Every `Recommendation` names a concrete
action (automate a task, add staffing, redesign an escalation path, ...),
grounded in observable data already produced elsewhere in the simulator:
`KPIResult`, `RiskAssessment`, and workflow structure.

Recommendations are heuristic, not proof: each one names its reasoning
so a human reviewer can accept, reject, or refine it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.risk import AI_FAILURE, STAFFING, RiskAssessment
from b2b_workflow_simulator.workflow import Workflow

AUTOMATE_TASK = "automate_task"
KEEP_HUMAN_REVIEW = "keep_human_review"
INCREASE_STAFFING = "increase_staffing"
REDUCE_STAFFING = "reduce_staffing"
MERGE_ACTIVITIES = "merge_activities"
SPLIT_ACTIVITIES = "split_activities"
INTRODUCE_MEMORY_AGENT = "introduce_memory_enabled_agent"
INTRODUCE_APPROVAL_GATE = "introduce_approval_gate"
REMOVE_APPROVAL = "remove_unnecessary_approval"
REDESIGN_ESCALATION = "redesign_escalation_path"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

_HIGH_FREQUENCY_THRESHOLD = 0.8
_LOW_UTILIZATION_THRESHOLD = 0.2
_LONG_DURATION_MULTIPLIER = 2.0
_APPROVAL_KEYWORD = "approv"
_SENSITIVE_KEYWORDS = ("payment", "disbursement", "refund", "contract", "payout")
_MIN_VISITS_FOR_APPROVAL_REVIEW = 5


@dataclass(frozen=True)
class Recommendation:
    """One actionable, explainable suggestion for improving a workflow."""

    kind: str
    node_id: str | None
    title: str
    reasoning: str
    affected_kpis: tuple[str, ...]
    expected_benefit: str
    confidence: str


@dataclass
class RecommendationSet:
    """Every recommendation generated for one workflow, in priority order."""

    workflow_name: str
    recommendations: list[Recommendation] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.recommendations)

    def of_kind(self, kind: str) -> list[Recommendation]:
        return [r for r in self.recommendations if r.kind == kind]


def _node_average_duration(kpi: KPIResult, node_id: str) -> float:
    visits = kpi.node_visit_counts.get(node_id, 0)
    if visits == 0:
        return 0.0
    return kpi.node_total_duration_minutes.get(node_id, 0.0) / visits


def _average_duration_across_nodes(kpi: KPIResult) -> float:
    durations = [
        _node_average_duration(kpi, node_id) for node_id in kpi.node_visit_counts if node_id
    ]
    durations = [d for d in durations if d > 0]
    if not durations:
        return 0.0
    return sum(durations) / len(durations)


def _recommend_automation(workflow: Workflow, kpi: KPIResult) -> list[Recommendation]:
    recommendations = []
    for node in workflow.nodes.values():
        actor = workflow.get_actor(node.actor_id)
        if not isinstance(actor, HumanActor):
            continue
        visits = kpi.node_visit_counts.get(node.node_id, 0)
        if kpi.total_cases == 0 or visits == 0:
            continue
        frequency = visits / kpi.total_cases
        if frequency < _HIGH_FREQUENCY_THRESHOLD:
            continue
        if _APPROVAL_KEYWORD in node.name.lower() or _APPROVAL_KEYWORD in node.node_id.lower():
            continue
        recommendations.append(
            Recommendation(
                kind=AUTOMATE_TASK,
                node_id=node.node_id,
                title=f"Automate '{node.name}'",
                reasoning=(
                    f"'{node.node_id}' runs on nearly every case "
                    f"({frequency:.0%} of cases) and is performed by a human actor "
                    "with no approval semantics, making it a strong candidate for "
                    "automation."
                ),
                affected_kpis=("total_cost", "avg_cycle_time_minutes", "actor_utilization"),
                expected_benefit=(
                    "Reduced cost per case and shorter cycle time by removing manual "
                    "effort from a high-frequency step."
                ),
                confidence=CONFIDENCE_MEDIUM,
            )
        )
    return recommendations


def _recommend_keep_human_review(
    workflow: Workflow, risk_assessment: RiskAssessment | None
) -> list[Recommendation]:
    recommendations = []
    for node in workflow.nodes.values():
        actor = workflow.get_actor(node.actor_id)
        if not isinstance(actor, AIAgentActor):
            continue
        if actor.error_rate < 0.1 and actor.escalation_rate < 0.1:
            continue
        risk_note = ""
        if risk_assessment is not None:
            ai_factors = [
                f for f in risk_assessment.factors_for(AI_FAILURE) if f.node_id == node.node_id
            ]
            if ai_factors:
                risk_note = f" Flagged by risk assessment: {ai_factors[0].description}"
        recommendations.append(
            Recommendation(
                kind=KEEP_HUMAN_REVIEW,
                node_id=node.node_id,
                title=f"Keep human review on '{node.name}'",
                reasoning=(
                    f"AI agent '{actor.actor_id}' at '{node.node_id}' has a "
                    f"{actor.error_rate:.1%} error rate and {actor.escalation_rate:.1%} "
                    f"escalation rate, too high to run fully autonomously.{risk_note}"
                ),
                affected_kpis=("failure_rate", "total_escalations"),
                expected_benefit=(
                    "Avoids downstream failures and rework by catching AI mistakes "
                    "before they reach customers or systems of record."
                ),
                confidence=CONFIDENCE_HIGH,
            )
        )
    return recommendations


def _recommend_staffing_changes(
    workflow: Workflow, kpi: KPIResult, risk_assessment: RiskAssessment | None
) -> list[Recommendation]:
    recommendations = []
    for actor_id, utilization in kpi.actor_utilization.items():
        if risk_assessment is not None and any(
            f.category == STAFFING for f in risk_assessment.factors_for(STAFFING)
        ):
            confidence = CONFIDENCE_HIGH
        else:
            confidence = CONFIDENCE_MEDIUM
        if utilization >= 0.9:
            recommendations.append(
                Recommendation(
                    kind=INCREASE_STAFFING,
                    node_id=None,
                    title=f"Increase staffing for '{actor_id}'",
                    reasoning=(
                        f"Actor '{actor_id}' is running at {utilization:.1%} utilization, "
                        "leaving little slack before queueing delays cascade."
                    ),
                    affected_kpis=("avg_wait_time_minutes", "avg_cycle_time_minutes"),
                    expected_benefit="Reduced queueing delay and improved SLA attainment.",
                    confidence=confidence,
                )
            )
        elif 0 < utilization < _LOW_UTILIZATION_THRESHOLD:
            recommendations.append(
                Recommendation(
                    kind=REDUCE_STAFFING,
                    node_id=None,
                    title=f"Reduce staffing for '{actor_id}'",
                    reasoning=(
                        f"Actor '{actor_id}' is running at only {utilization:.1%} "
                        "utilization, indicating more capacity than current demand needs."
                    ),
                    affected_kpis=("total_cost",),
                    expected_benefit="Lower fixed labor cost without harming throughput.",
                    confidence=CONFIDENCE_LOW,
                )
            )
    for pool_id, utilization in kpi.pool_utilization.items():
        if utilization >= 0.9:
            recommendations.append(
                Recommendation(
                    kind=INCREASE_STAFFING,
                    node_id=None,
                    title=f"Add workers to pool '{pool_id}'",
                    reasoning=(
                        f"Pool '{pool_id}' is running at {utilization:.1%} utilization "
                        "across its workers."
                    ),
                    affected_kpis=("avg_wait_time_minutes", "avg_cycle_time_minutes"),
                    expected_benefit="Reduced queueing delay for work routed through this pool.",
                    confidence=CONFIDENCE_MEDIUM,
                )
            )
        elif 0 < utilization < _LOW_UTILIZATION_THRESHOLD:
            recommendations.append(
                Recommendation(
                    kind=REDUCE_STAFFING,
                    node_id=None,
                    title=f"Reduce workers in pool '{pool_id}'",
                    reasoning=(
                        f"Pool '{pool_id}' is running at only {utilization:.1%} utilization."
                    ),
                    affected_kpis=("total_cost",),
                    expected_benefit="Lower fixed labor cost without harming throughput.",
                    confidence=CONFIDENCE_LOW,
                )
            )
    return recommendations


def _recommend_merges(workflow: Workflow, kpi: KPIResult) -> list[Recommendation]:
    recommendations = []
    for edge in workflow.edges:
        if edge.probability < 1.0:
            continue
        source = workflow.get_node(edge.source)
        target = workflow.get_node(edge.target)
        if source.actor_id != target.actor_id:
            continue
        if source.is_terminal:
            continue
        if len(workflow.outgoing_edges(source.node_id)) != 1:
            continue
        recommendations.append(
            Recommendation(
                kind=MERGE_ACTIVITIES,
                node_id=source.node_id,
                title=f"Merge '{source.name}' and '{target.name}'",
                reasoning=(
                    f"'{source.node_id}' always flows directly into '{target.node_id}' and "
                    "both run on the same actor, so splitting them into two steps only "
                    "adds handoff overhead."
                ),
                affected_kpis=("avg_cycle_time_minutes",),
                expected_benefit="Fewer handoffs and less recorded overhead per case.",
                confidence=CONFIDENCE_LOW,
            )
        )
    return recommendations


def _recommend_splits(workflow: Workflow, kpi: KPIResult) -> list[Recommendation]:
    recommendations = []
    average_duration = _average_duration_across_nodes(kpi)
    if average_duration <= 0:
        return recommendations
    for node in workflow.nodes.values():
        duration = _node_average_duration(kpi, node.node_id)
        if duration <= average_duration * _LONG_DURATION_MULTIPLIER:
            continue
        recommendations.append(
            Recommendation(
                kind=SPLIT_ACTIVITIES,
                node_id=node.node_id,
                title=f"Split '{node.name}' into smaller steps",
                reasoning=(
                    f"'{node.node_id}' averages {duration:.1f} minutes, more than "
                    f"{_LONG_DURATION_MULTIPLIER:.0f}x the workflow average of "
                    f"{average_duration:.1f} minutes, suggesting it bundles multiple "
                    "distinct pieces of work."
                ),
                affected_kpis=("avg_cycle_time_minutes", "actor_utilization"),
                expected_benefit=(
                    "Improved schedulability and the option to parallelize or "
                    "reassign part of the work to a different actor."
                ),
                confidence=CONFIDENCE_LOW,
            )
        )
    return recommendations


def _recommend_memory_agents(workflow: Workflow) -> list[Recommendation]:
    recommendations = []
    for node in workflow.nodes.values():
        actor = workflow.get_actor(node.actor_id)
        if not isinstance(actor, AIAgentActor):
            continue
        if actor.escalation_rate >= 0.15 and actor.error_rate < 0.05:
            recommendations.append(
                Recommendation(
                    kind=INTRODUCE_MEMORY_AGENT,
                    node_id=node.node_id,
                    title=f"Introduce a memory-enabled agent for '{node.name}'",
                    reasoning=(
                        f"AI agent '{actor.actor_id}' at '{node.node_id}' has a low error "
                        f"rate ({actor.error_rate:.1%}) but a high escalation rate "
                        f"({actor.escalation_rate:.1%}), suggesting escalations stem from "
                        "missing context or history rather than poor task execution."
                    ),
                    affected_kpis=("total_escalations", "avg_cycle_time_minutes"),
                    expected_benefit=(
                        "Fewer unnecessary escalations by giving the agent access to "
                        "prior case context."
                    ),
                    confidence=CONFIDENCE_LOW,
                )
            )
    return recommendations


def _recommend_approval_gates(workflow: Workflow) -> list[Recommendation]:
    recommendations = []
    for node in workflow.nodes.values():
        label = f"{node.node_id} {node.name}".lower()
        if not any(keyword in label for keyword in _SENSITIVE_KEYWORDS):
            continue
        if _APPROVAL_KEYWORD in label:
            continue
        has_upstream_approval = _has_upstream_keyword(workflow, node.node_id, _APPROVAL_KEYWORD)
        if has_upstream_approval:
            continue
        recommendations.append(
            Recommendation(
                kind=INTRODUCE_APPROVAL_GATE,
                node_id=node.node_id,
                title=f"Introduce an approval gate before '{node.name}'",
                reasoning=(
                    f"'{node.node_id}' appears to perform a financially or contractually "
                    "sensitive action with no upstream approval step in its path."
                ),
                affected_kpis=("failure_rate",),
                expected_benefit="Reduced risk of unauthorized or erroneous high-impact actions.",
                confidence=CONFIDENCE_LOW,
            )
        )
    return recommendations


def _has_upstream_keyword(workflow: Workflow, node_id: str, keyword: str, visited=None) -> bool:
    if visited is None:
        visited = set()
    for other in workflow.nodes.values():
        if other.node_id in visited:
            continue
        for edge in workflow.outgoing_edges(other.node_id):
            if edge.target != node_id:
                continue
            visited.add(other.node_id)
            label = f"{other.node_id} {other.name}".lower()
            if keyword in label:
                return True
            if _has_upstream_keyword(workflow, other.node_id, keyword, visited):
                return True
    return False


def _recommend_approval_removal(workflow: Workflow, kpi: KPIResult) -> list[Recommendation]:
    recommendations = []
    for node in workflow.nodes.values():
        label = f"{node.node_id} {node.name}".lower()
        if _APPROVAL_KEYWORD not in label:
            continue
        visits = kpi.node_visit_counts.get(node.node_id, 0)
        failures = kpi.node_failure_counts.get(node.node_id, 0)
        if visits < _MIN_VISITS_FOR_APPROVAL_REVIEW:
            continue
        if failures > 0:
            continue
        recommendations.append(
            Recommendation(
                kind=REMOVE_APPROVAL,
                node_id=node.node_id,
                title=f"Reconsider the approval gate at '{node.name}'",
                reasoning=(
                    f"'{node.node_id}' was executed {visits} time(s) and never produced "
                    "a rejection or failure, suggesting it may be a rubber-stamp step "
                    "rather than a meaningful control."
                ),
                affected_kpis=("avg_cycle_time_minutes", "avg_wait_time_minutes"),
                expected_benefit=(
                    "Faster cycle time by removing an approval that consistently adds "
                    "delay without changing the outcome."
                ),
                confidence=CONFIDENCE_LOW,
            )
        )
    return recommendations


def _recommend_escalation_redesign(workflow: Workflow, kpi: KPIResult) -> list[Recommendation]:
    recommendations = []
    if kpi.total_cases == 0 or kpi.escalation_rate < 0.2:
        return recommendations
    for node in workflow.nodes.values():
        actor = workflow.get_actor(node.actor_id)
        if not isinstance(actor, AIAgentActor):
            continue
        if actor.escalation_rate < 0.2:
            continue
        if not _is_in_cycle(workflow, node.node_id):
            continue
        recommendations.append(
            Recommendation(
                kind=REDESIGN_ESCALATION,
                node_id=node.node_id,
                title=f"Redesign the escalation path from '{node.name}'",
                reasoning=(
                    f"'{node.node_id}' escalates {actor.escalation_rate:.1%} of the time "
                    "and sits inside a retry loop, risking cases cycling back to the same "
                    "point that already failed once."
                ),
                affected_kpis=("total_escalations", "avg_cycle_time_minutes"),
                expected_benefit=(
                    "Shorter resolution time by routing escalations to a distinct "
                    "resolution path instead of back through the same loop."
                ),
                confidence=CONFIDENCE_MEDIUM,
            )
        )
    return recommendations


def _is_in_cycle(workflow: Workflow, node_id: str) -> bool:
    visited = {node_id}
    stack = [edge.target for edge in workflow.outgoing_edges(node_id)]
    while stack:
        current = stack.pop()
        if current == node_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(edge.target for edge in workflow.outgoing_edges(current))
    return False


def generate_recommendations(
    workflow: Workflow,
    kpi: KPIResult,
    risk_assessment: RiskAssessment | None = None,
) -> RecommendationSet:
    """Generate every applicable recommendation for `workflow` given `kpi`.

    `risk_assessment`, when supplied, sharpens reasoning and confidence
    for staffing- and AI-related recommendations with real risk factors
    rather than re-deriving them from scratch.
    """
    recommendations: list[Recommendation] = []
    recommendations += _recommend_automation(workflow, kpi)
    recommendations += _recommend_keep_human_review(workflow, risk_assessment)
    recommendations += _recommend_staffing_changes(workflow, kpi, risk_assessment)
    recommendations += _recommend_merges(workflow, kpi)
    recommendations += _recommend_splits(workflow, kpi)
    recommendations += _recommend_memory_agents(workflow)
    recommendations += _recommend_approval_gates(workflow)
    recommendations += _recommend_approval_removal(workflow, kpi)
    recommendations += _recommend_escalation_redesign(workflow, kpi)

    _CONFIDENCE_RANK = {CONFIDENCE_HIGH: 2, CONFIDENCE_MEDIUM: 1, CONFIDENCE_LOW: 0}
    recommendations.sort(key=lambda r: _CONFIDENCE_RANK[r.confidence], reverse=True)

    return RecommendationSet(workflow_name=workflow.name, recommendations=recommendations)


def generate_recommendation_report(recommendation_set: RecommendationSet) -> str:
    """Render `recommendation_set` as a plain-text recommendation report."""
    lines = [
        f"Recommendations: {recommendation_set.workflow_name}",
        "=" * 60,
        f"{len(recommendation_set)} recommendation(s) generated.",
        "",
    ]
    if not recommendation_set.recommendations:
        lines.append("No actionable recommendations at this time.")
        return "\n".join(lines)

    for index, rec in enumerate(recommendation_set.recommendations, start=1):
        lines.append(f"{index}. {rec.title} [{rec.confidence} confidence]")
        lines.append(f"   Reasoning: {rec.reasoning}")
        lines.append(f"   Affected KPIs: {', '.join(rec.affected_kpis)}")
        lines.append(f"   Expected benefit: {rec.expected_benefit}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "AUTOMATE_TASK",
    "KEEP_HUMAN_REVIEW",
    "INCREASE_STAFFING",
    "REDUCE_STAFFING",
    "MERGE_ACTIVITIES",
    "SPLIT_ACTIVITIES",
    "INTRODUCE_MEMORY_AGENT",
    "INTRODUCE_APPROVAL_GATE",
    "REMOVE_APPROVAL",
    "REDESIGN_ESCALATION",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_MEDIUM",
    "CONFIDENCE_LOW",
    "Recommendation",
    "RecommendationSet",
    "generate_recommendations",
    "generate_recommendation_report",
]
