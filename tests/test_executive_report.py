from b2b_workflow_simulator.compliance import GDPRApprovalRequirement, evaluate_compliance
from b2b_workflow_simulator.executive_report import (
    build_executive_assessment,
    generate_executive_report,
)
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.policy import SeparationOfDutiesPolicy, evaluate_policies
from b2b_workflow_simulator.primitives.event import Event, EventType
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.simulation import SimulationResult
from b2b_workflow_simulator.sla import CompletionSLA, evaluate_sla
from b2b_workflow_simulator.workflow import Workflow


def build_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Ops Flow", entry_node_id="intake")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_node(Node(node_id="intake", name="Intake", actor_id="clerk", is_terminal=True))
    return workflow


def build_kpi(total_cases: int = 10, completed_cases: int = 10) -> KPIResult:
    return KPIResult(
        workflow_name="Ops Flow",
        total_cases=total_cases,
        completed_cases=completed_cases,
        node_visit_counts={"intake": total_cases},
    )


def test_build_executive_assessment_includes_core_sub_reports():
    workflow = build_workflow()
    kpi = build_kpi()

    assessment = build_executive_assessment(workflow, kpi)

    assert assessment.workflow_name == "Ops Flow"
    assert assessment.risk_assessment is not None
    assert assessment.recommendations is not None
    assert assessment.ai_adoption is not None
    assert assessment.redesign_diff is None
    assert assessment.policy_evaluation is None
    assert assessment.compliance_report is None
    assert assessment.sla_report is None


def test_build_executive_assessment_includes_optional_sections_when_supplied():
    workflow = build_workflow()
    kpi = build_kpi()
    policy_evaluation = evaluate_policies(
        workflow, [SeparationOfDutiesPolicy(name="sod", node_id_a="intake", node_id_b="intake")]
    )
    compliance_report = evaluate_compliance(
        workflow,
        [
            GDPRApprovalRequirement(
                name="gdpr", personal_data_node_id="intake", consent_node_ids=("nowhere",)
            )
        ],
    )
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 30.0, "case-1"),
    ]
    sla_report = evaluate_sla(
        SimulationResult(workflow_name="Ops Flow", events=events),
        [CompletionSLA(name="fast", deadline_minutes=10.0)],
    )
    before_kpi = build_kpi(total_cases=10, completed_cases=8)
    diff = compare_workflows(before_kpi, kpi)

    assessment = build_executive_assessment(
        workflow,
        kpi,
        redesign_diff=diff,
        policy_evaluation=policy_evaluation,
        compliance_report=compliance_report,
        sla_report=sla_report,
    )

    assert assessment.redesign_diff is diff
    assert assessment.policy_evaluation is policy_evaluation
    assert assessment.compliance_report is compliance_report
    assert assessment.sla_report is sla_report


def test_generate_executive_report_includes_all_section_headers():
    workflow = build_workflow()
    kpi = build_kpi()

    assessment = build_executive_assessment(workflow, kpi)
    report = generate_executive_report(assessment)

    for header in (
        "EXECUTIVE ASSESSMENT REPORT",
        "KPI SUMMARY",
        "ROI",
        "SLA PERFORMANCE",
        "COMPLIANCE",
        "POLICY VIOLATIONS",
        "ORGANIZATIONAL RISK",
        "RECOMMENDATIONS",
        "AI ADOPTION ASSESSMENT",
    ):
        assert header in report


def test_generate_executive_report_omits_optional_sections_gracefully():
    workflow = build_workflow()
    kpi = build_kpi()

    assessment = build_executive_assessment(workflow, kpi)
    report = generate_executive_report(assessment)

    assert "No redesign comparison supplied" in report
    assert "No SLA rules supplied" in report
    assert "No compliance requirements supplied" in report
    assert "No policies supplied" in report


def test_generate_executive_report_includes_kpi_figures():
    workflow = build_workflow()
    kpi = build_kpi(total_cases=20, completed_cases=18)

    assessment = build_executive_assessment(workflow, kpi)
    report = generate_executive_report(assessment)

    assert "Cases simulated: 20" in report
    assert "Completion rate: 90.0%" in report


def test_generate_executive_report_includes_roi_when_diff_supplied():
    workflow = build_workflow()
    kpi = build_kpi()
    before_kpi = build_kpi(total_cases=10, completed_cases=5)
    diff = compare_workflows(before_kpi, kpi)

    assessment = build_executive_assessment(workflow, kpi, redesign_diff=diff)
    report = generate_executive_report(assessment)

    assert "Ops Flow" in report
    assert "Total cost savings" in report


def test_generate_executive_report_truncates_long_recommendation_lists():
    workflow = Workflow(workflow_id="wf", name="Busy Flow", entry_node_id="a")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_actor(HumanActor(actor_id="controller", name="Controller"))
    for node_id in ["a", "b", "c", "d", "e", "f", "g"]:
        actor_id = "clerk" if node_id != "d" else "controller"
        workflow.add_node(
            Node(node_id=node_id, name=node_id, actor_id=actor_id, is_terminal=(node_id == "g"))
        )
    kpi = KPIResult(
        workflow_name="Busy Flow",
        total_cases=10,
        completed_cases=10,
        node_visit_counts={n: 10 for n in ["a", "b", "c", "d", "e", "f", "g"]},
        actor_utilization={"clerk": 0.95},
    )

    assessment = build_executive_assessment(workflow, kpi)
    report = generate_executive_report(assessment)

    if len(assessment.recommendations) > 5:
        assert "more recommendation(s)" in report
