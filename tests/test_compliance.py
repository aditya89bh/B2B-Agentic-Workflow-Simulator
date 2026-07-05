from b2b_workflow_simulator.compliance import (
    AuditRequirement,
    FinancialApprovalChainRequirement,
    GDPRApprovalRequirement,
    MandatoryDocumentationRequirement,
    RecordRetentionRequirement,
    RegulatoryCheckpointRequirement,
    SegregationOfDutiesRequirement,
    evaluate_compliance,
)
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow


def build_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Onboarding", entry_node_id="consent")
    workflow.add_actor(HumanActor(actor_id="rep", name="Rep"))
    workflow.add_actor(HumanActor(actor_id="manager", name="Manager"))
    workflow.add_actor(HumanActor(actor_id="finance", name="Finance"))
    workflow.add_node(Node(node_id="consent", name="Consent", actor_id="rep"))
    workflow.add_node(
        Node(
            node_id="process_data",
            name="Process Personal Data",
            actor_id="rep",
            metadata={"data_subject_id": "abc"},
        )
    )
    workflow.add_node(Node(node_id="manager_approval", name="Manager Approval", actor_id="manager"))
    workflow.add_node(Node(node_id="finance_approval", name="Finance Approval", actor_id="finance"))
    workflow.add_node(
        Node(node_id="disburse", name="Disburse Funds", actor_id="finance", is_terminal=True)
    )
    workflow.add_edge(Edge("consent", "process_data", probability=1.0))
    workflow.add_edge(Edge("process_data", "manager_approval", probability=1.0))
    workflow.add_edge(Edge("manager_approval", "finance_approval", probability=1.0))
    workflow.add_edge(Edge("finance_approval", "disburse", probability=1.0))
    return workflow


def test_gdpr_requirement_passes_when_consent_precedes_processing():
    workflow = build_workflow()
    requirement = GDPRApprovalRequirement(
        name="gdpr-consent", personal_data_node_id="process_data", consent_node_ids=("consent",)
    )

    report = evaluate_compliance(workflow, [requirement])

    assert report.is_compliant
    assert report.compliance_score == 100.0


def test_gdpr_requirement_flags_missing_consent_gate():
    workflow = build_workflow()
    requirement = GDPRApprovalRequirement(
        name="gdpr-consent",
        personal_data_node_id="process_data",
        consent_node_ids=("finance_approval",),
    )

    report = evaluate_compliance(workflow, [requirement])

    assert not report.is_compliant
    assert report.violations[0].requirement_kind == "gdpr_approval"


def test_audit_requirement_flags_missing_metadata():
    workflow = build_workflow()
    requirement = AuditRequirement(
        name="audit-trail",
        node_id="process_data",
        required_metadata_keys=("data_subject_id", "consent_timestamp"),
    )

    report = evaluate_compliance(workflow, [requirement])

    assert not report.is_compliant
    assert "consent_timestamp" in report.violations[0].description


def test_audit_requirement_always_produces_a_finding():
    workflow = build_workflow()
    requirement = AuditRequirement(name="audit-trail", node_id="process_data")

    report = evaluate_compliance(workflow, [requirement])

    assert report.is_compliant
    assert len(report.audit_findings) == 1
    assert report.audit_findings[0].requirement_kind == "audit"


def test_financial_approval_chain_passes_when_chain_precedes_action():
    workflow = build_workflow()
    requirement = FinancialApprovalChainRequirement(
        name="disbursement-chain",
        node_id="disburse",
        approval_chain_node_ids=("manager_approval", "finance_approval"),
    )

    report = evaluate_compliance(workflow, [requirement])

    assert report.is_compliant
    assert len(report.audit_findings) == 1


def test_financial_approval_chain_flags_broken_link():
    workflow = build_workflow()
    requirement = FinancialApprovalChainRequirement(
        name="disbursement-chain",
        node_id="disburse",
        approval_chain_node_ids=("finance_approval", "manager_approval"),
    )

    report = evaluate_compliance(workflow, [requirement])

    assert not report.is_compliant
    assert report.violations[0].requirement_kind == "financial_approval_chain"


def test_segregation_of_duties_flags_same_actor():
    workflow = build_workflow()
    requirement = SegregationOfDutiesRequirement(
        name="sod", node_id_a="finance_approval", node_id_b="disburse"
    )

    report = evaluate_compliance(workflow, [requirement])

    assert not report.is_compliant


def test_segregation_of_duties_passes_for_different_actors():
    workflow = build_workflow()
    requirement = SegregationOfDutiesRequirement(
        name="sod", node_id_a="manager_approval", node_id_b="finance_approval"
    )

    report = evaluate_compliance(workflow, [requirement])

    assert report.is_compliant


def test_mandatory_documentation_flags_missing_fields():
    workflow = build_workflow()
    requirement = MandatoryDocumentationRequirement(
        name="doc-requirement",
        node_id="manager_approval",
        required_metadata_keys=("justification",),
    )

    report = evaluate_compliance(workflow, [requirement])

    assert not report.is_compliant
    assert "justification" in report.violations[0].description


def test_record_retention_always_produces_a_finding_with_no_violation():
    workflow = build_workflow()
    requirement = RecordRetentionRequirement(
        name="retention", node_id="disburse", retention_days=2555
    )

    report = evaluate_compliance(workflow, [requirement])

    assert report.is_compliant
    assert "2555" in report.audit_findings[0].finding


def test_regulatory_checkpoint_always_produces_a_finding_with_no_violation():
    workflow = build_workflow()
    requirement = RegulatoryCheckpointRequirement(
        name="checkpoint", node_id="finance_approval", regulation_reference="SOX 404"
    )

    report = evaluate_compliance(workflow, [requirement])

    assert report.is_compliant
    assert "SOX 404" in report.audit_findings[0].finding


def test_compliance_score_reflects_partial_failures():
    workflow = build_workflow()
    requirements = [
        GDPRApprovalRequirement(
            name="gdpr-consent",
            personal_data_node_id="process_data",
            consent_node_ids=("finance_approval",),  # fails
        ),
        SegregationOfDutiesRequirement(
            name="sod", node_id_a="manager_approval", node_id_b="finance_approval"
        ),  # passes
    ]

    report = evaluate_compliance(workflow, requirements)

    assert report.compliance_score == 50.0


def test_evaluate_compliance_with_no_requirements_is_fully_compliant():
    workflow = build_workflow()

    report = evaluate_compliance(workflow, [])

    assert report.is_compliant
    assert report.compliance_score == 100.0
    assert report.requirements_checked == 0
