"""Organizational risk engine: turn workflow structure and KPIs into risk scores.

Six risk categories are modeled, each scored 0-100 (higher is riskier) from
a combination of workflow structure (actors, graph shape) and simulated
KPIs (failure rate, utilization, escalation rate):

    operational: failure rate and queueing/wait time.
    compliance: policy and compliance-requirement violations, if supplied.
    ai_failure: AI agent error rates, escalation rates, and missing
        human-fallback paths.
    staffing: overloaded actors/pools relative to their capacity.
    process_complexity: graph size, branching, and retry loops.
    single_point_of_failure: single (non-pooled) actors that many stages
        of the process depend on.

Every category score is backed by a list of `RiskFactor` entries, so a
report can explain *why* a category scored the way it did rather than
just stating a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.compliance import ComplianceReport
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.policy import PolicyEvaluation
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.workflow import Workflow

OPERATIONAL = "operational"
COMPLIANCE = "compliance"
AI_FAILURE = "ai_failure"
STAFFING = "staffing"
PROCESS_COMPLEXITY = "process_complexity"
SINGLE_POINT_OF_FAILURE = "single_point_of_failure"

CATEGORIES = (
    OPERATIONAL,
    COMPLIANCE,
    AI_FAILURE,
    STAFFING,
    PROCESS_COMPLEXITY,
    SINGLE_POINT_OF_FAILURE,
)

_OVERLOAD_UTILIZATION_THRESHOLD = 0.90


@dataclass(frozen=True)
class RiskFactor:
    """One contributing reason a risk category scored the way it did."""

    category: str
    node_id: str | None
    description: str
    weight: float


@dataclass
class RiskAssessment:
    """The full risk picture for one workflow: category scores plus explanations."""

    workflow_name: str
    category_scores: dict[str, float] = field(default_factory=dict)
    factors: list[RiskFactor] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Average of every category score, 0-100."""
        if not self.category_scores:
            return 0.0
        return sum(self.category_scores.values()) / len(self.category_scores)

    def factors_for(self, category: str) -> list[RiskFactor]:
        return [factor for factor in self.factors if factor.category == category]

    def top_factors(self, top_n: int = 5) -> list[RiskFactor]:
        """The highest-weighted risk factors across every category."""
        return sorted(self.factors, key=lambda factor: factor.weight, reverse=True)[:top_n]


def _capped_score(factors: list[RiskFactor]) -> float:
    return min(100.0, sum(factor.weight for factor in factors))


def _operational_factors(kpi: KPIResult) -> list[RiskFactor]:
    factors = []
    if kpi.failure_rate > 0:
        factors.append(
            RiskFactor(
                OPERATIONAL,
                None,
                f"{kpi.failure_rate:.1%} of cases end in failure.",
                min(100.0, kpi.failure_rate * 150.0),
            )
        )
    if kpi.avg_cycle_time_minutes > 0:
        wait_ratio = kpi.avg_wait_time_minutes / kpi.avg_cycle_time_minutes
        if wait_ratio > 0:
            factors.append(
                RiskFactor(
                    OPERATIONAL,
                    None,
                    f"Queueing accounts for {wait_ratio:.1%} of average cycle time.",
                    min(50.0, wait_ratio * 50.0),
                )
            )
    return factors


def _compliance_factors(
    policy_evaluation: PolicyEvaluation | None,
    compliance_report: ComplianceReport | None,
) -> list[RiskFactor]:
    factors = []
    if policy_evaluation is not None and policy_evaluation.violation_count > 0:
        policy_weight = (
            policy_evaluation.error_count * 20.0 + policy_evaluation.warning_count * 5.0
        )
        factors.append(
            RiskFactor(
                COMPLIANCE,
                None,
                f"{policy_evaluation.violation_count} business policy violation(s) detected "
                f"({policy_evaluation.error_count} error(s), "
                f"{policy_evaluation.warning_count} warning(s)).",
                min(60.0, policy_weight),
            )
        )
    if compliance_report is not None and compliance_report.violation_count > 0:
        gap = 100.0 - compliance_report.compliance_score
        factors.append(
            RiskFactor(
                COMPLIANCE,
                None,
                f"Compliance score is {compliance_report.compliance_score:.1f}% "
                f"({compliance_report.violation_count} requirement(s) unmet).",
                min(60.0, gap),
            )
        )
    return factors


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


def _ai_failure_factors(workflow: Workflow) -> list[RiskFactor]:
    factors = []
    for node in workflow.nodes.values():
        actor = workflow.get_actor(node.actor_id)
        if not isinstance(actor, AIAgentActor):
            continue
        if actor.error_rate > 0:
            factors.append(
                RiskFactor(
                    AI_FAILURE,
                    node.node_id,
                    f"'{node.node_id}' runs on AI agent '{actor.actor_id}' with a "
                    f"{actor.error_rate:.1%} error rate.",
                    min(40.0, actor.error_rate * 100.0),
                )
            )
        if actor.escalation_rate > 0:
            factors.append(
                RiskFactor(
                    AI_FAILURE,
                    node.node_id,
                    f"'{node.node_id}' escalates to a human "
                    f"{actor.escalation_rate:.1%} of the time.",
                    min(20.0, actor.escalation_rate * 40.0),
                )
            )
        if not _has_human_fallback(workflow, node.node_id, set()):
            factors.append(
                RiskFactor(
                    AI_FAILURE,
                    node.node_id,
                    f"'{node.node_id}' has no reachable human fallback if the AI agent fails.",
                    30.0,
                )
            )
    return factors


def _staffing_factors(workflow: Workflow, kpi: KPIResult) -> list[RiskFactor]:
    factors = []
    for actor_id, utilization in kpi.actor_utilization.items():
        if utilization >= _OVERLOAD_UTILIZATION_THRESHOLD:
            factors.append(
                RiskFactor(
                    STAFFING,
                    None,
                    f"Actor '{actor_id}' is running at {utilization:.1%} utilization, "
                    "leaving little slack for demand spikes.",
                    min(50.0, (utilization - _OVERLOAD_UTILIZATION_THRESHOLD) * 500.0 + 20.0),
                )
            )
    for pool_id, utilization in kpi.pool_utilization.items():
        if utilization >= _OVERLOAD_UTILIZATION_THRESHOLD:
            factors.append(
                RiskFactor(
                    STAFFING,
                    None,
                    f"Pool '{pool_id}' is running at {utilization:.1%} utilization "
                    "across its workers.",
                    min(50.0, (utilization - _OVERLOAD_UTILIZATION_THRESHOLD) * 500.0 + 20.0),
                )
            )
    return factors


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


def _complexity_factors(workflow: Workflow) -> list[RiskFactor]:
    factors = []
    node_count = len(workflow.nodes)
    edge_count = len(workflow.edges)
    if node_count > 8:
        factors.append(
            RiskFactor(
                PROCESS_COMPLEXITY,
                None,
                f"Workflow has {node_count} stages, making it harder to reason about "
                "end to end.",
                min(40.0, (node_count - 8) * 3.0),
            )
        )
    branching = edge_count / node_count if node_count else 0.0
    if branching > 1.3:
        factors.append(
            RiskFactor(
                PROCESS_COMPLEXITY,
                None,
                f"Average branching factor is {branching:.1f} edges per node, indicating "
                "many conditional paths.",
                min(30.0, (branching - 1.3) * 30.0),
            )
        )
    cyclic_nodes = [node_id for node_id in workflow.nodes if _is_in_cycle(workflow, node_id)]
    if cyclic_nodes:
        factors.append(
            RiskFactor(
                PROCESS_COMPLEXITY,
                None,
                f"{len(cyclic_nodes)} node(s) participate in a retry/rework loop: "
                f"{sorted(cyclic_nodes)}.",
                min(30.0, len(cyclic_nodes) * 10.0),
            )
        )
    return factors


def _spof_factors(workflow: Workflow) -> list[RiskFactor]:
    dependent_nodes: dict[str, list[str]] = {}
    for node in workflow.nodes.values():
        actor = workflow.get_actor(node.actor_id)
        if isinstance(actor, ActorPool):
            continue
        dependent_nodes.setdefault(node.actor_id, []).append(node.node_id)
        for actor_id in node.additional_actor_ids:
            secondary = workflow.get_actor(actor_id)
            if not isinstance(secondary, ActorPool):
                dependent_nodes.setdefault(actor_id, []).append(node.node_id)

    factors = []
    for actor_id, node_ids in dependent_nodes.items():
        if len(node_ids) < 2:
            continue
        factors.append(
            RiskFactor(
                SINGLE_POINT_OF_FAILURE,
                None,
                f"Actor '{actor_id}' is the sole performer of {len(node_ids)} stage(s) "
                f"{sorted(set(node_ids))}; unavailability halts all of them.",
                min(60.0, (len(node_ids) - 1) * 15.0),
            )
        )
    return factors


def compute_risk(
    workflow: Workflow,
    kpi: KPIResult,
    policy_evaluation: PolicyEvaluation | None = None,
    compliance_report: ComplianceReport | None = None,
) -> RiskAssessment:
    """Score every risk category for `workflow` given its simulated `kpi`.

    `policy_evaluation` and `compliance_report` are optional: when
    provided, they sharpen the compliance category score with real
    violation data instead of leaving it at zero.
    """
    factors: list[RiskFactor] = []
    factors += _operational_factors(kpi)
    factors += _compliance_factors(policy_evaluation, compliance_report)
    factors += _ai_failure_factors(workflow)
    factors += _staffing_factors(workflow, kpi)
    factors += _complexity_factors(workflow)
    factors += _spof_factors(workflow)

    category_scores = {
        category: _capped_score([f for f in factors if f.category == category])
        for category in CATEGORIES
    }
    return RiskAssessment(
        workflow_name=workflow.name, category_scores=category_scores, factors=factors
    )


_CATEGORY_LABELS = {
    OPERATIONAL: "Operational",
    COMPLIANCE: "Compliance",
    AI_FAILURE: "AI Failure",
    STAFFING: "Staffing",
    PROCESS_COMPLEXITY: "Process Complexity",
    SINGLE_POINT_OF_FAILURE: "Single Point of Failure",
}


def generate_risk_report(assessment: RiskAssessment) -> str:
    """Render `assessment` as a plain-text organizational risk report."""
    lines = [
        f"Organizational Risk Assessment: {assessment.workflow_name}",
        "=" * 60,
        f"Overall risk score: {assessment.overall_score:.1f}/100",
        "",
        "Category scores:",
    ]
    for category in CATEGORIES:
        score = assessment.category_scores.get(category, 0.0)
        lines.append(f"  - {_CATEGORY_LABELS[category]}: {score:.1f}/100")

    lines.append("")
    lines.append("Risk factors:")
    if not assessment.factors:
        lines.append("  No risk factors identified.")
    for category in CATEGORIES:
        category_factors = assessment.factors_for(category)
        if not category_factors:
            continue
        lines.append(f"  {_CATEGORY_LABELS[category]}:")
        for factor in sorted(category_factors, key=lambda f: f.weight, reverse=True):
            lines.append(f"    - {factor.description} (weight: {factor.weight:.1f})")

    return "\n".join(lines)


__all__ = [
    "OPERATIONAL",
    "COMPLIANCE",
    "AI_FAILURE",
    "STAFFING",
    "PROCESS_COMPLEXITY",
    "SINGLE_POINT_OF_FAILURE",
    "CATEGORIES",
    "RiskFactor",
    "RiskAssessment",
    "compute_risk",
    "generate_risk_report",
]
