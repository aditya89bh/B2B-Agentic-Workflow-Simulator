"""Business policy engine: governance rules attachable to a workflow.

Workflows encode *what happens*; policies encode *what must be true* about
how it happens -- approval chains, routing constraints, escalation paths,
retry safety, business-hours constraints, mandatory human review, and
separation of duties. `evaluate_policies` checks a workflow's structure
against a set of policies and reports any violations, independent of
running a simulation.

Every policy type is a small, frozen dataclass so policy sets can be
defined declaratively (and, like workflows, could be serialized later
without any behavior attached to them). `evaluate_policies` is the single
place that knows how to check each kind.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.workflow import Workflow

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"


@dataclass(frozen=True)
class ApprovalPolicy:
    """Requires at least one of `required_before_node_ids` to precede `target_node_id`.

    Models rules like "invoices over the authorization threshold must pass
    through a controller/manager approval node before payment is scheduled".
    """

    name: str
    target_node_id: str
    required_before_node_ids: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class RoutingPolicy:
    """Restricts which nodes are allowed to directly follow `node_id`."""

    name: str
    node_id: str
    allowed_next_node_ids: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class EscalationPolicy:
    """Requires an AI-operated node to have a reachable human escalation path."""

    name: str
    node_id: str
    description: str = ""


@dataclass(frozen=True)
class RetryPolicy:
    """Caps retry loops: a node that can loop back to itself must have an escape edge.

    `max_attempts` is recorded for reporting purposes; the simulation
    engines do not currently enforce a hard per-node retry ceiling, so this
    policy's structural check instead verifies that any cycle containing
    `node_id` has at least one edge leaving the cycle, ruling out designs
    that could retry forever with no way out.
    """

    name: str
    node_id: str
    max_attempts: int
    description: str = ""


@dataclass(frozen=True)
class BusinessHoursPolicy:
    """Requires a pooled node's worker shifts to fall within an allowed daily window."""

    name: str
    node_id: str
    allowed_start_hour: float
    allowed_end_hour: float
    description: str = ""


@dataclass(frozen=True)
class MandatoryHumanReviewPolicy:
    """Requires `node_id` to be performed by a human actor (or a human team pool)."""

    name: str
    node_id: str
    description: str = ""


@dataclass(frozen=True)
class SeparationOfDutiesPolicy:
    """Requires two nodes to be performed by different actors."""

    name: str
    node_id_a: str
    node_id_b: str
    description: str = ""


Policy = (
    ApprovalPolicy
    | RoutingPolicy
    | EscalationPolicy
    | RetryPolicy
    | BusinessHoursPolicy
    | MandatoryHumanReviewPolicy
    | SeparationOfDutiesPolicy
)


@dataclass(frozen=True)
class PolicyViolation:
    """One instance of a workflow failing to satisfy an attached policy."""

    policy_name: str
    policy_kind: str
    node_id: str | None
    severity: str
    description: str


@dataclass
class PolicyEvaluation:
    """The result of checking every policy in a set against one workflow."""

    workflow_name: str
    policies_checked: int
    violations: list[PolicyViolation] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return not self.violations

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == SEVERITY_ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == SEVERITY_WARNING)


def _reverse_adjacency(workflow: Workflow) -> dict[str, list[str]]:
    reverse: dict[str, list[str]] = {node_id: [] for node_id in workflow.nodes}
    for edge in workflow.edges:
        reverse.setdefault(edge.target, []).append(edge.source)
    return reverse


def _can_reach(workflow: Workflow, source_node_id: str, target_node_id: str) -> bool:
    """Whether `target_node_id` is reachable from `source_node_id` via outgoing edges."""
    visited = {source_node_id}
    stack = [source_node_id]
    while stack:
        current = stack.pop()
        if current == target_node_id:
            return True
        for edge in workflow.outgoing_edges(current):
            if edge.target not in visited:
                visited.add(edge.target)
                stack.append(edge.target)
    return False


def _find_cycle_containing(workflow: Workflow, node_id: str) -> set[str] | None:
    """Return the node set of one cycle containing `node_id`, or None if acyclic there."""
    for edge in workflow.outgoing_edges(node_id):
        if edge.target == node_id:
            return {node_id}
        if _can_reach(workflow, edge.target, node_id):
            visited = {node_id}
            stack = [edge.target]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                for next_edge in workflow.outgoing_edges(current):
                    if next_edge.target == node_id or _can_reach(
                        workflow, next_edge.target, node_id
                    ):
                        stack.append(next_edge.target)
            return visited
    return None


def _check_approval_policy(workflow: Workflow, policy: ApprovalPolicy) -> list[PolicyViolation]:
    if any(
        _can_reach(workflow, gate_id, policy.target_node_id)
        for gate_id in policy.required_before_node_ids
    ):
        return []
    gates = ", ".join(policy.required_before_node_ids)
    return [
        PolicyViolation(
            policy.name,
            "approval",
            policy.target_node_id,
            SEVERITY_ERROR,
            f"'{policy.target_node_id}' is reachable without passing through "
            f"any required approval gate ({gates}).",
        )
    ]


def _check_routing_policy(workflow: Workflow, policy: RoutingPolicy) -> list[PolicyViolation]:
    violations = []
    for edge in workflow.outgoing_edges(policy.node_id):
        if edge.target not in policy.allowed_next_node_ids:
            violations.append(
                PolicyViolation(
                    policy.name,
                    "routing",
                    policy.node_id,
                    SEVERITY_ERROR,
                    f"'{policy.node_id}' routes to '{edge.target}', which is not in the "
                    f"allowed set {policy.allowed_next_node_ids}.",
                )
            )
    return violations


def _check_escalation_policy(
    workflow: Workflow, policy: EscalationPolicy
) -> list[PolicyViolation]:
    node = workflow.get_node(policy.node_id)
    actor = workflow.get_actor(node.actor_id)
    if actor.kind != "ai_agent":
        return []
    for edge in workflow.outgoing_edges(policy.node_id):
        target_node = workflow.get_node(edge.target)
        target_actor = workflow.get_actor(target_node.actor_id)
        if target_actor.kind in ("human", "actor_pool"):
            return []
        if _has_human_downstream(workflow, edge.target):
            return []
    return [
        PolicyViolation(
            policy.name,
            "escalation",
            policy.node_id,
            SEVERITY_ERROR,
            f"AI-operated node '{policy.node_id}' has no reachable human escalation path.",
        )
    ]


def _has_human_downstream(
    workflow: Workflow, node_id: str, _visited: set[str] | None = None
) -> bool:
    visited = _visited if _visited is not None else set()
    if node_id in visited:
        return False
    visited.add(node_id)
    node = workflow.get_node(node_id)
    actor = workflow.get_actor(node.actor_id)
    if actor.kind in ("human", "actor_pool"):
        return True
    return any(
        _has_human_downstream(workflow, edge.target, visited)
        for edge in workflow.outgoing_edges(node_id)
    )


def _check_retry_policy(workflow: Workflow, policy: RetryPolicy) -> list[PolicyViolation]:
    cycle = _find_cycle_containing(workflow, policy.node_id)
    if cycle is None:
        return []
    has_escape = any(
        edge.target not in cycle
        for member in cycle
        for edge in workflow.outgoing_edges(member)
    )
    if has_escape:
        return []
    return [
        PolicyViolation(
            policy.name,
            "retry",
            policy.node_id,
            SEVERITY_ERROR,
            f"'{policy.node_id}' is part of a retry loop {sorted(cycle)} with no edge "
            f"leaving the loop, so cases could retry indefinitely.",
        )
    ]


def _check_business_hours_policy(
    workflow: Workflow, policy: BusinessHoursPolicy
) -> list[PolicyViolation]:
    node = workflow.get_node(policy.node_id)
    actor = workflow.get_actor(node.actor_id)
    if not isinstance(actor, ActorPool):
        return []
    violations = []
    for worker in actor.workers:
        for shift in worker.shifts:
            if shift.start_hour < policy.allowed_start_hour or (
                shift.end_hour > policy.allowed_end_hour
            ):
                violations.append(
                    PolicyViolation(
                        policy.name,
                        "business_hours",
                        policy.node_id,
                        SEVERITY_WARNING,
                        f"Worker '{worker.worker_id}' shift '{shift.name}' "
                        f"({shift.start_hour:g}-{shift.end_hour:g}) falls outside the "
                        f"allowed window ({policy.allowed_start_hour:g}-"
                        f"{policy.allowed_end_hour:g}) for '{policy.node_id}'.",
                    )
                )
    return violations


def _check_mandatory_human_review_policy(
    workflow: Workflow, policy: MandatoryHumanReviewPolicy
) -> list[PolicyViolation]:
    node = workflow.get_node(policy.node_id)
    actor = workflow.get_actor(node.actor_id)
    if actor.kind in ("human", "actor_pool"):
        return []
    return [
        PolicyViolation(
            policy.name,
            "mandatory_human_review",
            policy.node_id,
            SEVERITY_ERROR,
            f"'{policy.node_id}' requires mandatory human review but is assigned to "
            f"AI actor '{actor.actor_id}'.",
        )
    ]


def _check_separation_of_duties_policy(
    workflow: Workflow, policy: SeparationOfDutiesPolicy
) -> list[PolicyViolation]:
    node_a = workflow.get_node(policy.node_id_a)
    node_b = workflow.get_node(policy.node_id_b)
    if node_a.actor_id != node_b.actor_id:
        return []
    return [
        PolicyViolation(
            policy.name,
            "separation_of_duties",
            policy.node_id_a,
            SEVERITY_ERROR,
            f"'{policy.node_id_a}' and '{policy.node_id_b}' must be performed by "
            f"different actors, but both are assigned to '{node_a.actor_id}'.",
        )
    ]


_CHECKERS = {
    ApprovalPolicy: _check_approval_policy,
    RoutingPolicy: _check_routing_policy,
    EscalationPolicy: _check_escalation_policy,
    RetryPolicy: _check_retry_policy,
    BusinessHoursPolicy: _check_business_hours_policy,
    MandatoryHumanReviewPolicy: _check_mandatory_human_review_policy,
    SeparationOfDutiesPolicy: _check_separation_of_duties_policy,
}


def evaluate_policies(workflow: Workflow, policies: list[Policy]) -> PolicyEvaluation:
    """Check every policy in `policies` against `workflow` and collect violations."""
    violations: list[PolicyViolation] = []
    for policy in policies:
        checker = _CHECKERS[type(policy)]
        violations.extend(checker(workflow, policy))
    return PolicyEvaluation(
        workflow_name=workflow.name, policies_checked=len(policies), violations=violations
    )


__all__ = [
    "ApprovalPolicy",
    "RoutingPolicy",
    "EscalationPolicy",
    "RetryPolicy",
    "BusinessHoursPolicy",
    "MandatoryHumanReviewPolicy",
    "SeparationOfDutiesPolicy",
    "Policy",
    "PolicyViolation",
    "PolicyEvaluation",
    "evaluate_policies",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
]
