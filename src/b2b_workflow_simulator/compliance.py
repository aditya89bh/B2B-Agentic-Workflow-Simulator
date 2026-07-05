"""Compliance engine: regulatory and audit requirements attachable to a workflow.

Where `policy.py` encodes internal governance rules ("controller must
approve before payment"), this module encodes external regulatory and
audit obligations: GDPR-style consent gates, financial approval chains,
segregation of duties for SOX-style controls, mandatory documentation,
record retention, and regulatory checkpoints. `evaluate_compliance`
checks a workflow against a set of these requirements and produces both
hard violations (things that are structurally wrong) and audit findings
(informational observations useful to an auditor, regardless of whether
anything failed).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.workflow import Workflow


@dataclass(frozen=True)
class GDPRApprovalRequirement:
    """Requires consent/approval to precede a node that processes personal data."""

    name: str
    personal_data_node_id: str
    consent_node_ids: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class AuditRequirement:
    """Requires a node to carry the metadata fields needed to reconstruct an audit trail."""

    name: str
    node_id: str
    required_metadata_keys: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class FinancialApprovalChainRequirement:
    """Requires a sequence of distinct approval nodes to precede a financial action node."""

    name: str
    node_id: str
    approval_chain_node_ids: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class SegregationOfDutiesRequirement:
    """Requires two nodes to be performed by different actors, for regulatory controls."""

    name: str
    node_id_a: str
    node_id_b: str
    description: str = ""


@dataclass(frozen=True)
class MandatoryDocumentationRequirement:
    """Requires a node to carry specific business documentation metadata fields."""

    name: str
    node_id: str
    required_metadata_keys: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class RecordRetentionRequirement:
    """Flags that records produced at a node must be retained for a minimum period."""

    name: str
    node_id: str
    retention_days: int
    description: str = ""


@dataclass(frozen=True)
class RegulatoryCheckpointRequirement:
    """Flags a node as a checkpoint reviewed under a named regulation."""

    name: str
    node_id: str
    regulation_reference: str
    description: str = ""


ComplianceRequirement = (
    GDPRApprovalRequirement
    | AuditRequirement
    | FinancialApprovalChainRequirement
    | SegregationOfDutiesRequirement
    | MandatoryDocumentationRequirement
    | RecordRetentionRequirement
    | RegulatoryCheckpointRequirement
)


@dataclass(frozen=True)
class ComplianceViolation:
    """One instance of a workflow failing to satisfy a compliance requirement."""

    requirement_name: str
    requirement_kind: str
    node_id: str | None
    description: str


@dataclass(frozen=True)
class AuditFinding:
    """An informational observation recorded for an auditor, independent of pass/fail."""

    requirement_name: str
    requirement_kind: str
    node_id: str | None
    finding: str


@dataclass
class ComplianceReport:
    """The result of checking every requirement in a set against one workflow."""

    workflow_name: str
    requirements_checked: int
    violations: list[ComplianceViolation] = field(default_factory=list)
    audit_findings: list[AuditFinding] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return not self.violations

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def compliance_score(self) -> float:
        """Percentage (0-100) of distinct requirements with no violation."""
        if self.requirements_checked == 0:
            return 100.0
        failing = {violation.requirement_name for violation in self.violations}
        satisfied = self.requirements_checked - len(failing)
        return max(0.0, satisfied / self.requirements_checked) * 100.0


def _reachable(workflow: Workflow, source_node_id: str, target_node_id: str) -> bool:
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


def _check_gdpr(
    workflow: Workflow, requirement: GDPRApprovalRequirement
) -> tuple[list[ComplianceViolation], list[AuditFinding]]:
    satisfied = any(
        _reachable(workflow, consent_id, requirement.personal_data_node_id)
        for consent_id in requirement.consent_node_ids
    )
    if satisfied:
        return [], []
    return (
        [
            ComplianceViolation(
                requirement.name,
                "gdpr_approval",
                requirement.personal_data_node_id,
                f"'{requirement.personal_data_node_id}' processes personal data without a "
                f"preceding consent/approval gate from {requirement.consent_node_ids}.",
            )
        ],
        [],
    )


def _check_audit(
    workflow: Workflow, requirement: AuditRequirement
) -> tuple[list[ComplianceViolation], list[AuditFinding]]:
    node = workflow.get_node(requirement.node_id)
    missing = [key for key in requirement.required_metadata_keys if key not in node.metadata]
    violations = []
    if missing:
        violations.append(
            ComplianceViolation(
                requirement.name,
                "audit",
                requirement.node_id,
                f"'{requirement.node_id}' is missing required audit metadata: {missing}.",
            )
        )
    finding = AuditFinding(
        requirement.name,
        "audit",
        requirement.node_id,
        f"'{requirement.node_id}' executions are captured in the event log "
        f"(actor, timestamp, outcome) plus metadata {list(node.metadata)}.",
    )
    return violations, [finding]


def _check_financial_approval_chain(
    workflow: Workflow, requirement: FinancialApprovalChainRequirement
) -> tuple[list[ComplianceViolation], list[AuditFinding]]:
    chain = requirement.approval_chain_node_ids
    checkpoints = (*chain, requirement.node_id)
    for earlier, later in zip(checkpoints, checkpoints[1:], strict=False):
        if not _reachable(workflow, earlier, later):
            return (
                [
                    ComplianceViolation(
                        requirement.name,
                        "financial_approval_chain",
                        requirement.node_id,
                        f"Approval chain broken: '{earlier}' cannot reach '{later}' before "
                        f"'{requirement.node_id}' executes.",
                    )
                ],
                [],
            )
    return (
        [],
        [
            AuditFinding(
                requirement.name,
                "financial_approval_chain",
                requirement.node_id,
                f"Financial action '{requirement.node_id}' is gated by approval chain "
                f"{chain}.",
            )
        ],
    )


def _check_segregation_of_duties(
    workflow: Workflow, requirement: SegregationOfDutiesRequirement
) -> tuple[list[ComplianceViolation], list[AuditFinding]]:
    node_a = workflow.get_node(requirement.node_id_a)
    node_b = workflow.get_node(requirement.node_id_b)
    if node_a.actor_id != node_b.actor_id:
        return [], []
    return (
        [
            ComplianceViolation(
                requirement.name,
                "segregation_of_duties",
                requirement.node_id_a,
                f"'{requirement.node_id_a}' and '{requirement.node_id_b}' must be performed "
                f"by different actors, but both are assigned to '{node_a.actor_id}'.",
            )
        ],
        [],
    )


def _check_mandatory_documentation(
    workflow: Workflow, requirement: MandatoryDocumentationRequirement
) -> tuple[list[ComplianceViolation], list[AuditFinding]]:
    node = workflow.get_node(requirement.node_id)
    missing = [key for key in requirement.required_metadata_keys if key not in node.metadata]
    if not missing:
        return [], []
    return (
        [
            ComplianceViolation(
                requirement.name,
                "mandatory_documentation",
                requirement.node_id,
                f"'{requirement.node_id}' is missing required documentation fields: {missing}.",
            )
        ],
        [],
    )


def _check_record_retention(
    workflow: Workflow, requirement: RecordRetentionRequirement
) -> tuple[list[ComplianceViolation], list[AuditFinding]]:
    workflow.get_node(requirement.node_id)  # validates the node exists
    finding = AuditFinding(
        requirement.name,
        "record_retention",
        requirement.node_id,
        f"Records produced at '{requirement.node_id}' must be retained for "
        f"{requirement.retention_days} day(s).",
    )
    return [], [finding]


def _check_regulatory_checkpoint(
    workflow: Workflow, requirement: RegulatoryCheckpointRequirement
) -> tuple[list[ComplianceViolation], list[AuditFinding]]:
    workflow.get_node(requirement.node_id)  # validates the node exists
    finding = AuditFinding(
        requirement.name,
        "regulatory_checkpoint",
        requirement.node_id,
        f"'{requirement.node_id}' is a regulatory checkpoint under "
        f"{requirement.regulation_reference}.",
    )
    return [], [finding]


_CHECKERS = {
    GDPRApprovalRequirement: _check_gdpr,
    AuditRequirement: _check_audit,
    FinancialApprovalChainRequirement: _check_financial_approval_chain,
    SegregationOfDutiesRequirement: _check_segregation_of_duties,
    MandatoryDocumentationRequirement: _check_mandatory_documentation,
    RecordRetentionRequirement: _check_record_retention,
    RegulatoryCheckpointRequirement: _check_regulatory_checkpoint,
}


def evaluate_compliance(
    workflow: Workflow, requirements: list[ComplianceRequirement]
) -> ComplianceReport:
    """Check every requirement in `requirements` against `workflow`."""
    violations: list[ComplianceViolation] = []
    findings: list[AuditFinding] = []
    for requirement in requirements:
        checker = _CHECKERS[type(requirement)]
        requirement_violations, requirement_findings = checker(workflow, requirement)
        violations.extend(requirement_violations)
        findings.extend(requirement_findings)
    return ComplianceReport(
        workflow_name=workflow.name,
        requirements_checked=len(requirements),
        violations=violations,
        audit_findings=findings,
    )


__all__ = [
    "GDPRApprovalRequirement",
    "AuditRequirement",
    "FinancialApprovalChainRequirement",
    "SegregationOfDutiesRequirement",
    "MandatoryDocumentationRequirement",
    "RecordRetentionRequirement",
    "RegulatoryCheckpointRequirement",
    "ComplianceRequirement",
    "ComplianceViolation",
    "AuditFinding",
    "ComplianceReport",
    "evaluate_compliance",
]
