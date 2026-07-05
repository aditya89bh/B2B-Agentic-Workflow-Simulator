import pytest

from b2b_workflow_simulator.compliance import evaluate_compliance
from b2b_workflow_simulator.examples import (
    customer_support_ticket_resolution,
    governance,
    invoice_processing,
    sales_lead_qualification,
)
from b2b_workflow_simulator.policy import evaluate_policies
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.sla import evaluate_sla

_EXAMPLES = [
    (
        invoice_processing.build_before_workflow,
        invoice_processing.build_after_workflow,
        governance.invoice_processing_policies,
        governance.invoice_processing_compliance_requirements,
        governance.invoice_processing_slas,
    ),
    (
        customer_support_ticket_resolution.build_before_workflow,
        customer_support_ticket_resolution.build_after_workflow,
        governance.customer_support_policies,
        governance.customer_support_compliance_requirements,
        governance.customer_support_slas,
    ),
    (
        sales_lead_qualification.build_before_workflow,
        sales_lead_qualification.build_after_workflow,
        governance.sales_lead_qualification_policies,
        governance.sales_lead_qualification_compliance_requirements,
        governance.sales_lead_qualification_slas,
    ),
]


@pytest.mark.parametrize("before_builder,after_builder,policies_fn,compliance_fn,sla_fn", _EXAMPLES)
def test_policies_reference_only_existing_nodes_and_actors(
    before_builder, after_builder, policies_fn, compliance_fn, sla_fn
):
    before = before_builder()
    after = after_builder()

    evaluation_before = evaluate_policies(before, policies_fn())
    evaluation_after = evaluate_policies(after, policies_fn())

    assert evaluation_before.policies_checked == len(policies_fn())
    assert evaluation_after.policies_checked == len(policies_fn())


@pytest.mark.parametrize("before_builder,after_builder,policies_fn,compliance_fn,sla_fn", _EXAMPLES)
def test_compliance_requirements_reference_only_existing_nodes(
    before_builder, after_builder, policies_fn, compliance_fn, sla_fn
):
    before = before_builder()
    after = after_builder()

    report_before = evaluate_compliance(before, compliance_fn())
    report_after = evaluate_compliance(after, compliance_fn())

    assert report_before.requirements_checked == len(compliance_fn())
    assert report_after.requirements_checked == len(compliance_fn())


@pytest.mark.parametrize("before_builder,after_builder,policies_fn,compliance_fn,sla_fn", _EXAMPLES)
def test_slas_evaluate_cleanly_against_a_simulation_run(
    before_builder, after_builder, policies_fn, compliance_fn, sla_fn
):
    before = before_builder()
    after = after_builder()

    for workflow in (before, after):
        result = SimulationRunner(seed=1).run(workflow, 20)
        report = evaluate_sla(result, sla_fn())
        assert report.rules_checked == len(sla_fn())
        assert 0.0 <= report.attainment_rate <= 1.0


def test_invoice_after_variant_introduces_a_segregation_of_duties_gap():
    after = invoice_processing.build_after_workflow()
    report = evaluate_compliance(after, governance.invoice_processing_compliance_requirements())

    assert any(v.requirement_kind == "segregation_of_duties" for v in report.violations)


def test_invoice_before_variant_has_no_segregation_of_duties_gap():
    before = invoice_processing.build_before_workflow()
    report = evaluate_compliance(before, governance.invoice_processing_compliance_requirements())

    assert not any(v.requirement_kind == "segregation_of_duties" for v in report.violations)


def test_customer_support_after_variant_violates_mandatory_human_review():
    after = customer_support_ticket_resolution.build_after_workflow()
    evaluation = evaluate_policies(after, governance.customer_support_policies())

    assert any(v.policy_kind == "mandatory_human_review" for v in evaluation.violations)


def test_customer_support_before_variant_satisfies_mandatory_human_review():
    before = customer_support_ticket_resolution.build_before_workflow()
    evaluation = evaluate_policies(before, governance.customer_support_policies())

    assert not any(v.policy_kind == "mandatory_human_review" for v in evaluation.violations)


def test_sales_lead_qualification_handoff_approval_policy_is_satisfied():
    for builder in (
        sales_lead_qualification.build_before_workflow,
        sales_lead_qualification.build_after_workflow,
    ):
        workflow = builder()
        evaluation = evaluate_policies(workflow, governance.sales_lead_qualification_policies())
        assert not any(v.policy_kind == "approval" for v in evaluation.violations)
