"""Governance definitions for the bundled example workflows.

Each example ships with a matching set of business policies, compliance
requirements, and service-level agreements that reference the example's
own node and actor ids. Because every example's "before" and "after"
variant shares identical node ids (see `tests/test_examples.py`), the
same governance definitions apply to either variant unmodified -- which
makes it possible to compare how an AI-driven redesign changes
governance posture, not just cost and cycle time.

These are deliberately independent of the workflow builders themselves:
adding a policy here never requires touching `Node` or `Workflow`
definitions, keeping the example workflows stable for existing tests.
"""

from __future__ import annotations

from b2b_workflow_simulator.compliance import (
    AuditRequirement,
    ComplianceRequirement,
    FinancialApprovalChainRequirement,
    MandatoryDocumentationRequirement,
    RecordRetentionRequirement,
    RegulatoryCheckpointRequirement,
    SegregationOfDutiesRequirement,
)
from b2b_workflow_simulator.policy import (
    ApprovalPolicy,
    EscalationPolicy,
    MandatoryHumanReviewPolicy,
    Policy,
    SeparationOfDutiesPolicy,
)
from b2b_workflow_simulator.sla import SLA, CompletionSLA, ResponseSLA


def invoice_processing_policies() -> list[Policy]:
    """Governance policies for the invoice processing example."""
    return [
        ApprovalPolicy(
            name="erp-entry-requires-approval",
            target_node_id="erp_entry",
            required_before_node_ids=("approval",),
            description="Invoices must be approved before being posted to the ERP.",
        ),
        SeparationOfDutiesPolicy(
            name="validation-approval-segregation",
            node_id_a="validation",
            node_id_b="approval",
            description="Whoever validates an invoice must not also approve it.",
        ),
        EscalationPolicy(
            name="approval-escalation-path",
            node_id="approval",
            description="An automated approval step must have a reachable human escalation path.",
        ),
    ]


def invoice_processing_compliance_requirements() -> list[ComplianceRequirement]:
    """Compliance requirements for the invoice processing example."""
    return [
        FinancialApprovalChainRequirement(
            name="payment-approval-chain",
            node_id="payment_scheduling",
            approval_chain_node_ids=("validation", "approval"),
            description="Payments must be gated by validation, then approval, in order.",
        ),
        SegregationOfDutiesRequirement(
            name="posting-approval-segregation",
            node_id_a="approval",
            node_id_b="erp_entry",
            description="Approving and posting an invoice should not rest with one actor.",
        ),
        AuditRequirement(
            name="approval-audit-trail",
            node_id="approval",
            description="Every approval decision must be reconstructable from the event log.",
        ),
        RecordRetentionRequirement(
            name="invoice-record-retention",
            node_id="payment_scheduling",
            retention_days=2555,
            description="Posted invoice and payment records are retained for 7 years.",
        ),
    ]


def invoice_processing_slas() -> list[SLA]:
    """Service-level agreements for the invoice processing example."""
    return [
        CompletionSLA(
            name="invoice-cycle-time",
            deadline_minutes=120.0,
            penalty_per_minute=0.50,
            description="Invoices should clear intake through payment scheduling within 2 hours.",
        ),
        ResponseSLA(
            name="approval-response-time",
            node_id="approval",
            deadline_minutes=60.0,
            description="An invoice should reach the approval stage within an hour of intake.",
        ),
    ]


def customer_support_policies() -> list[Policy]:
    """Governance policies for the customer support ticket resolution example."""
    return [
        MandatoryHumanReviewPolicy(
            name="response-requires-human-in-manual-mode",
            node_id="response_drafting",
            description=(
                "Response drafting must be reviewed by a human unless the "
                "organization has explicitly approved autonomous response agents."
            ),
        ),
        EscalationPolicy(
            name="triage-escalation-path",
            node_id="triage",
            description="An automated triage step must have a reachable human escalation path.",
        ),
        SeparationOfDutiesPolicy(
            name="intake-escalation-segregation",
            node_id_a="ticket_intake",
            node_id_b="escalation",
            description="Whoever logs a ticket must not be the same actor who escalates it.",
        ),
    ]


def customer_support_compliance_requirements() -> list[ComplianceRequirement]:
    """Compliance requirements for the customer support ticket resolution example."""
    return [
        AuditRequirement(
            name="escalation-audit-trail",
            node_id="escalation",
            description="Every escalation must be reconstructable from the event log.",
        ),
        RegulatoryCheckpointRequirement(
            name="escalation-service-review",
            node_id="escalation",
            regulation_reference="Internal SLA Policy 4.2",
            description="Escalations are reviewed under the internal customer SLA policy.",
        ),
        MandatoryDocumentationRequirement(
            name="response-documentation",
            node_id="response_drafting",
            required_metadata_keys=("customer_communication_log",),
            description="Responses sent to customers must be logged for compliance review.",
        ),
        RecordRetentionRequirement(
            name="ticket-record-retention",
            node_id="follow_up",
            retention_days=1095,
            description="Closed ticket records are retained for 3 years.",
        ),
    ]


def customer_support_slas() -> list[SLA]:
    """Service-level agreements for the customer support ticket resolution example."""
    return [
        ResponseSLA(
            name="triage-response-time",
            node_id="triage",
            deadline_minutes=15.0,
            description="Tickets should be triaged within 15 minutes of intake.",
        ),
        CompletionSLA(
            name="ticket-resolution-time",
            deadline_minutes=240.0,
            penalty_per_minute=1.0,
            description="Tickets should reach a resolution within 4 hours.",
        ),
    ]


def sales_lead_qualification_policies() -> list[Policy]:
    """Governance policies for the sales lead qualification example."""
    return [
        ApprovalPolicy(
            name="handoff-requires-discovery",
            target_node_id="qualified_handoff",
            required_before_node_ids=("discovery_call",),
            description="A lead must pass through discovery before being handed off as qualified.",
        ),
        EscalationPolicy(
            name="research-escalation-path",
            node_id="initial_research",
            description=("An automated research step must have a reachable human escalation path."),
        ),
        SeparationOfDutiesPolicy(
            name="intake-handoff-segregation",
            node_id_a="lead_intake",
            node_id_b="qualified_handoff",
            description="Whoever logs a lead must not be the same actor who hands it off.",
        ),
    ]


def sales_lead_qualification_compliance_requirements() -> list[ComplianceRequirement]:
    """Compliance requirements for the sales lead qualification example."""
    return [
        AuditRequirement(
            name="handoff-audit-trail",
            node_id="qualified_handoff",
            description="Every qualified handoff must be reconstructable from the event log.",
        ),
        MandatoryDocumentationRequirement(
            name="discovery-call-documentation",
            node_id="discovery_call",
            required_metadata_keys=("call_notes", "budget_confirmed"),
            description="Discovery calls must be logged with notes and budget confirmation.",
        ),
        RecordRetentionRequirement(
            name="proposal-record-retention",
            node_id="proposal_draft",
            retention_days=1825,
            description="Proposal drafts are retained for 5 years for deal history.",
        ),
    ]


def sales_lead_qualification_slas() -> list[SLA]:
    """Service-level agreements for the sales lead qualification example."""
    return [
        ResponseSLA(
            name="discovery-call-response-time",
            node_id="discovery_call",
            deadline_minutes=180.0,
            description="A qualified lead should reach a discovery call within 3 hours.",
        ),
        CompletionSLA(
            name="qualification-cycle-time",
            deadline_minutes=300.0,
            description="Lead qualification should conclude within 5 hours of intake.",
        ),
    ]


__all__ = [
    "invoice_processing_policies",
    "invoice_processing_compliance_requirements",
    "invoice_processing_slas",
    "customer_support_policies",
    "customer_support_compliance_requirements",
    "customer_support_slas",
    "sales_lead_qualification_policies",
    "sales_lead_qualification_compliance_requirements",
    "sales_lead_qualification_slas",
]
