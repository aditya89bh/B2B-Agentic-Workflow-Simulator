"""AI adoption assessment: how ready is a workflow for more AI automation?

Six scores (0-100, higher is better except where noted) summarize different
angles on adoption readiness:

    automation_readiness: how much of the process is already automatable,
        combining current AI coverage with process stability.
    ai_maturity: how well any *existing* AI usage is performing (low error
        and escalation rates indicate mature, trustworthy automation).
    human_dependency: how much of the workload still requires a human
        (higher means more dependency, i.e. worse for further automation).
    governance_score: whether AI usage is adequately controlled, either
        via an attached `PolicyEvaluation` or, absent one, whether every
        AI step has a reachable human fallback.
    explainability_score: how predictable AI behavior is, proxied by how
        rarely it needs to escalate for human judgment.
    rollout_complexity: how hard the workflow's structure would be to
        roll a change out to (higher means more complex).

These combine into a single `readiness_index` and a rollout
recommendation: pilot, phased rollout, full deployment, or not
recommended.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.policy import PolicyEvaluation
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.workflow import Workflow

PILOT = "pilot"
PHASED_ROLLOUT = "phased_rollout"
FULL_DEPLOYMENT = "full_deployment"
NOT_RECOMMENDED = "not_recommended"

_LOW_GOVERNANCE_THRESHOLD = 40.0
_FULL_DEPLOYMENT_THRESHOLD = 75.0
_PHASED_ROLLOUT_THRESHOLD = 55.0
_PILOT_THRESHOLD = 35.0


@dataclass(frozen=True)
class AIAdoptionAssessment:
    """The full AI adoption picture for one workflow."""

    workflow_name: str
    automation_readiness: float
    ai_maturity: float
    human_dependency: float
    governance_score: float
    explainability_score: float
    rollout_complexity: float
    readiness_index: float
    recommendation: str
    reasoning: tuple[str, ...] = field(default_factory=tuple)


def _ai_actors(workflow: Workflow) -> list[AIAgentActor]:
    seen: dict[str, AIAgentActor] = {}
    for node in workflow.nodes.values():
        actor = workflow.get_actor(node.actor_id)
        if isinstance(actor, AIAgentActor):
            seen[actor.actor_id] = actor
    return list(seen.values())


def _has_human_fallback(workflow: Workflow, node_id: str, visited: set[str]) -> bool:
    if node_id in visited:
        return False
    visited.add(node_id)
    node = workflow.get_node(node_id)
    actor = workflow.get_actor(node.actor_id)
    if actor.kind in ("human", "actor_pool"):
        return True
    return any(
        _has_human_fallback(workflow, edge.target, visited)
        for edge in workflow.outgoing_edges(node_id)
    )


def _ai_node_count(workflow: Workflow) -> int:
    return sum(
        1
        for node in workflow.nodes.values()
        if isinstance(workflow.get_actor(node.actor_id), AIAgentActor)
    )


def _automation_readiness(workflow: Workflow, kpi: KPIResult) -> float:
    total_nodes = len(workflow.nodes)
    if total_nodes == 0:
        return 0.0
    ai_fraction = _ai_node_count(workflow) / total_nodes
    stability_bonus = (1.0 - kpi.failure_rate) * 30.0
    return min(100.0, ai_fraction * 70.0 + stability_bonus)


def _ai_maturity(ai_actors: list[AIAgentActor]) -> float:
    if not ai_actors:
        return 0.0
    penalty = sum(actor.error_rate * 100.0 + actor.escalation_rate * 50.0 for actor in ai_actors)
    penalty /= len(ai_actors)
    return max(0.0, 100.0 - penalty)


def _human_dependency(workflow: Workflow, kpi: KPIResult) -> float:
    total_visits = sum(kpi.node_visit_counts.values())
    if total_visits > 0:
        human_visits = sum(
            visits
            for node_id, visits in kpi.node_visit_counts.items()
            if node_id in workflow.nodes
            and isinstance(workflow.get_actor(workflow.get_node(node_id).actor_id), HumanActor)
        )
        return (human_visits / total_visits) * 100.0
    total_nodes = len(workflow.nodes)
    if total_nodes == 0:
        return 0.0
    human_nodes = sum(
        1
        for node in workflow.nodes.values()
        if isinstance(workflow.get_actor(node.actor_id), HumanActor)
    )
    return (human_nodes / total_nodes) * 100.0


def _governance_score(
    workflow: Workflow,
    ai_actors: list[AIAgentActor],
    policy_evaluation: PolicyEvaluation | None,
) -> tuple[float, str]:
    if policy_evaluation is not None:
        penalty = policy_evaluation.error_count * 15.0 + policy_evaluation.warning_count * 5.0
        score = max(0.0, 100.0 - penalty)
        return score, (
            f"Governance score derived from {policy_evaluation.violation_count} attached "
            "policy violation(s)."
        )
    if not ai_actors:
        return 100.0, "No AI agents are present, so there is nothing to govern yet."
    ai_node_ids = [
        node.node_id
        for node in workflow.nodes.values()
        if isinstance(workflow.get_actor(node.actor_id), AIAgentActor)
    ]
    with_fallback = sum(
        1 for node_id in ai_node_ids if _has_human_fallback(workflow, node_id, set())
    )
    score = (with_fallback / len(ai_node_ids)) * 100.0 if ai_node_ids else 100.0
    return score, (
        f"{with_fallback}/{len(ai_node_ids)} AI step(s) have a reachable human fallback "
        "(no policy evaluation was supplied, so this structural check was used instead)."
    )


def _explainability_score(ai_actors: list[AIAgentActor]) -> float:
    if not ai_actors:
        return 100.0
    avg_escalation = sum(actor.escalation_rate for actor in ai_actors) / len(ai_actors)
    return max(0.0, 100.0 - avg_escalation * 100.0)


def _rollout_complexity(workflow: Workflow, kpi: KPIResult) -> float:
    node_count = len(workflow.nodes)
    edge_count = len(workflow.edges)
    branching = edge_count / node_count if node_count else 0.0
    complexity = max(0.0, (node_count - 3) * 4.0)
    complexity += max(0.0, (branching - 1.0) * 20.0)
    complexity += kpi.multi_resource_task_count * 5.0
    return min(100.0, complexity)


def _recommend(readiness_index: float, governance_score: float) -> tuple[str, str]:
    if governance_score < _LOW_GOVERNANCE_THRESHOLD:
        return (
            PILOT,
            f"Governance score ({governance_score:.1f}) is below the "
            f"{_LOW_GOVERNANCE_THRESHOLD:.0f} safety threshold, so rollout is capped at a "
            "pilot regardless of overall readiness.",
        )
    if readiness_index >= _FULL_DEPLOYMENT_THRESHOLD:
        return (
            FULL_DEPLOYMENT,
            f"Readiness index ({readiness_index:.1f}) clears the "
            f"{_FULL_DEPLOYMENT_THRESHOLD:.0f} threshold with adequate governance.",
        )
    if readiness_index >= _PHASED_ROLLOUT_THRESHOLD:
        return (
            PHASED_ROLLOUT,
            f"Readiness index ({readiness_index:.1f}) supports a phased rollout rather "
            "than immediate full deployment.",
        )
    if readiness_index >= _PILOT_THRESHOLD:
        return (
            PILOT,
            f"Readiness index ({readiness_index:.1f}) is moderate; a limited pilot is "
            "recommended before wider investment.",
        )
    return (
        NOT_RECOMMENDED,
        f"Readiness index ({readiness_index:.1f}) is too low to recommend AI adoption "
        "at this time.",
    )


def assess_ai_adoption(
    workflow: Workflow,
    kpi: KPIResult,
    policy_evaluation: PolicyEvaluation | None = None,
) -> AIAdoptionAssessment:
    """Assess `workflow`'s readiness for AI adoption given its simulated `kpi`.

    `policy_evaluation`, when supplied, sharpens the governance score with
    real policy violation data instead of the structural human-fallback
    heuristic used otherwise.
    """
    ai_actors = _ai_actors(workflow)

    automation_readiness = _automation_readiness(workflow, kpi)
    ai_maturity = _ai_maturity(ai_actors)
    human_dependency = _human_dependency(workflow, kpi)
    governance_score, governance_reason = _governance_score(workflow, ai_actors, policy_evaluation)
    explainability_score = _explainability_score(ai_actors)
    rollout_complexity = _rollout_complexity(workflow, kpi)

    maturity_component = ai_maturity if ai_actors else automation_readiness
    readiness_index = (
        sum(
            [
                automation_readiness,
                maturity_component,
                governance_score,
                explainability_score,
                100.0 - human_dependency,
                100.0 - rollout_complexity,
            ]
        )
        / 6.0
    )

    recommendation, recommendation_reason = _recommend(readiness_index, governance_score)

    reasoning = [
        f"Automation readiness is {automation_readiness:.1f}/100 "
        f"based on current AI coverage and case failure rate.",
        f"AI maturity is {ai_maturity:.1f}/100 "
        + (
            "based on existing agent error and escalation rates."
            if ai_actors
            else "(no AI agents are in use yet, so there is no track record)."
        ),
        f"Human dependency is {human_dependency:.1f}/100 "
        "(share of task volume still requiring a human actor).",
        governance_reason,
        f"Explainability score is {explainability_score:.1f}/100 "
        + (
            "based on how often AI agents escalate rather than resolve autonomously."
            if ai_actors
            else "(no AI agents are in use yet)."
        ),
        f"Rollout complexity is {rollout_complexity:.1f}/100 "
        "based on workflow size, branching, and multi-resource coordination.",
        recommendation_reason,
    ]

    return AIAdoptionAssessment(
        workflow_name=workflow.name,
        automation_readiness=automation_readiness,
        ai_maturity=ai_maturity,
        human_dependency=human_dependency,
        governance_score=governance_score,
        explainability_score=explainability_score,
        rollout_complexity=rollout_complexity,
        readiness_index=readiness_index,
        recommendation=recommendation,
        reasoning=tuple(reasoning),
    )


_RECOMMENDATION_LABELS = {
    PILOT: "Pilot",
    PHASED_ROLLOUT: "Phased rollout",
    FULL_DEPLOYMENT: "Full deployment",
    NOT_RECOMMENDED: "Not recommended",
}


def generate_ai_adoption_report(assessment: AIAdoptionAssessment) -> str:
    """Render `assessment` as a plain-text AI adoption report."""
    lines = [
        f"AI Adoption Assessment: {assessment.workflow_name}",
        "=" * 60,
        f"Readiness index: {assessment.readiness_index:.1f}/100",
        f"Recommendation: {_RECOMMENDATION_LABELS[assessment.recommendation]}",
        "",
        "Scores:",
        f"  - Automation readiness: {assessment.automation_readiness:.1f}/100",
        f"  - AI maturity: {assessment.ai_maturity:.1f}/100",
        f"  - Human dependency: {assessment.human_dependency:.1f}/100",
        f"  - Governance: {assessment.governance_score:.1f}/100",
        f"  - Explainability: {assessment.explainability_score:.1f}/100",
        f"  - Rollout complexity: {assessment.rollout_complexity:.1f}/100",
        "",
        "Reasoning:",
    ]
    lines.extend(f"  - {reason}" for reason in assessment.reasoning)
    return "\n".join(lines)


__all__ = [
    "PILOT",
    "PHASED_ROLLOUT",
    "FULL_DEPLOYMENT",
    "NOT_RECOMMENDED",
    "AIAdoptionAssessment",
    "assess_ai_adoption",
    "generate_ai_adoption_report",
]
