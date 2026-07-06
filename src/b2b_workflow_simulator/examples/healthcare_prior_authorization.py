"""Healthcare prior authorization workflow scenario.

Prior authorization (PA) is a utilization management process where a health
insurer requires advance approval before a provider can deliver a specific
treatment, medication, or service.  The PA process is notorious for
administrative burden: providers cite it as a leading cause of physician
burnout and care delays.

This scenario models a typical PA workflow at a regional health plan.

**Before:** Clinical reviewers manually evaluate every submission, medical
directors handle peer-to-peer reviews, and administrative staff manage all
correspondence.  Average turnaround: 3–5 business days.

**After:** AI agents handle intake extraction, initial criteria matching, and
draft decision letters.  Medical directors focus only on escalated cases.
Average turnaround target: same-day for routine requests.

Limitations
-----------
- Clinical criteria logic is modeled as error/escalation rates, not detailed
  decision trees; actual clinical logic is far more complex.
- Appeals and external review processes are not modeled.
- HIPAA compliance overhead and audit requirements are not captured in cost.
- Turnaround times assume single-shift staffing; 24/7 operations would change
  the capacity model significantly.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import (
    AIAgentActor,
    Edge,
    HumanActor,
    Node,
)
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "healthcare-prior-authorization"


def build_before_workflow() -> Workflow:
    """Before: fully manual prior authorization review."""
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="Prior Authorization — Manual Review",
        entry_node_id="pa_intake",
        description="Human-only PA review: clinical staff evaluate all submissions.",
    )
    clinical_reviewer = HumanActor(
        actor_id="clinical_reviewer", name="Clinical Reviewer",
        hourly_cost=75.0, speed_multiplier=1.0, error_rate=0.04,
        available_hours_per_day=8.0,
    )
    medical_director = HumanActor(
        actor_id="medical_director", name="Medical Director",
        hourly_cost=220.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=6.0,
    )
    admin_staff = HumanActor(
        actor_id="admin_staff", name="Admin Staff",
        hourly_cost=32.0, speed_multiplier=1.0, error_rate=0.03,
        available_hours_per_day=8.0,
    )
    for actor in (clinical_reviewer, medical_director, admin_staff):
        wf.add_actor(actor)

    nodes = [
        Node("pa_intake", "PA Intake & Logging", "admin_staff",
             base_duration_minutes=20.0),
        Node("clinical_review", "Clinical Criteria Review", "clinical_reviewer",
             base_duration_minutes=35.0),
        Node("medical_director_review", "Medical Director Peer Review", "medical_director",
             base_duration_minutes=25.0),
        Node("decision_draft", "Decision Letter Draft", "admin_staff",
             base_duration_minutes=15.0),
        Node("approved", "Authorization Approved", "admin_staff",
             base_duration_minutes=10.0, is_terminal=True),
        Node("denied_standard", "Authorization Denied", "admin_staff",
             base_duration_minutes=15.0, is_terminal=True),
        Node("denied_expedited", "Urgent Request Denied", "medical_director",
             base_duration_minutes=20.0, is_terminal=True),
        Node("incomplete_return", "Returned: Incomplete Submission", "admin_staff",
             base_duration_minutes=10.0, is_terminal=True),
    ]
    for node in nodes:
        wf.add_node(node)

    edges = [
        Edge("pa_intake", "clinical_review", 0.85),
        Edge("pa_intake", "incomplete_return", 0.15),
        Edge("clinical_review", "decision_draft", 0.55),
        Edge("clinical_review", "medical_director_review", 0.38),
        Edge("clinical_review", "denied_standard", 0.07),
        Edge("medical_director_review", "decision_draft", 0.70),
        Edge("medical_director_review", "denied_expedited", 0.30),
        Edge("decision_draft", "approved", 0.72),
        Edge("decision_draft", "denied_standard", 0.28),
    ]
    for edge in edges:
        wf.add_edge(edge)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    """After: AI-assisted PA review with human escalation for complex cases."""
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="Prior Authorization — AI-Assisted Review",
        entry_node_id="ai_intake",
        description="AI extracts submission data and pre-screens criteria; humans handle escalations.",  # noqa: E501
    )
    ai_intake = AIAgentActor(
        actor_id="ai_intake", name="AI Intake Extractor",
        cost_per_execution=0.80, speed_multiplier=0.08, error_rate=0.06,
        escalation_rate=0.10,
    )
    ai_criteria = AIAgentActor(
        actor_id="ai_criteria", name="AI Criteria Matcher",
        cost_per_execution=2.50, speed_multiplier=0.15, error_rate=0.05,
        escalation_rate=0.20,
    )
    medical_director = HumanActor(
        actor_id="medical_director", name="Medical Director",
        hourly_cost=220.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=6.0,
    )
    admin_staff = HumanActor(
        actor_id="admin_staff", name="Admin Staff",
        hourly_cost=32.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=8.0,
    )
    for actor in (ai_intake, ai_criteria, medical_director, admin_staff):
        wf.add_actor(actor)

    nodes = [
        Node("ai_intake", "AI Intake & Extraction", "ai_intake",
             base_duration_minutes=20.0),
        Node("ai_criteria_match", "AI Criteria Matching", "ai_criteria",
             base_duration_minutes=35.0),
        Node("md_escalation", "Medical Director Escalation Review", "medical_director",
             base_duration_minutes=20.0),
        Node("ai_decision_letter", "AI Decision Letter Generation", "ai_criteria",
             base_duration_minutes=35.0, is_terminal=False),
        Node("approved", "Authorization Approved", "admin_staff",
             base_duration_minutes=10.0, is_terminal=True),
        Node("denied_auto", "Automated Denial", "admin_staff",
             base_duration_minutes=10.0, is_terminal=True),
        Node("denied_escalated", "Escalated Denial", "medical_director",
             base_duration_minutes=20.0, is_terminal=True),
        Node("incomplete_return", "Returned: Incomplete", "admin_staff",
             base_duration_minutes=8.0, is_terminal=True),
    ]
    for node in nodes:
        wf.add_node(node)

    edges = [
        Edge("ai_intake", "ai_criteria_match", 0.88),
        Edge("ai_intake", "incomplete_return", 0.12),
        Edge("ai_criteria_match", "ai_decision_letter", 0.60),
        Edge("ai_criteria_match", "md_escalation", 0.28),
        Edge("ai_criteria_match", "denied_auto", 0.12),
        Edge("md_escalation", "ai_decision_letter", 0.65),
        Edge("md_escalation", "denied_escalated", 0.35),
        Edge("ai_decision_letter", "approved", 0.74),
        Edge("ai_decision_letter", "denied_auto", 0.26),
    ]
    for edge in edges:
        wf.add_edge(edge)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=300, seed=42, implementation_cost=18_000.0,
        description=f"{_SLUG}: base assumptions (typical AI performance)",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=300, seed=42, implementation_cost=18_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.5,
        description=f"{_SLUG}: conservative (higher AI error, clinical complexity)",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=300, seed=42, implementation_cost=18_000.0,
        ai_cost_multiplier=0.6, human_hourly_cost_multiplier=0.9,
        description=f"{_SLUG}: aggressive (mature AI, lower costs)",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "Clinical criteria logic simplified to error/escalation rates; real PA is far more complex.",  # noqa: E501
            "Appeals and external independent review not modeled.",
            "HIPAA compliance and audit overhead not included in cost estimates.",
            "Assumes single-shift staffing; 24/7 payers require different capacity modeling.",
            "Drug and device PA may differ substantially from procedure PA.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 300 --implementation-cost 18000",
            f"b2b-simulator visualize-workflow {_SLUG} --format mermaid",
            f"b2b-simulator bottleneck-heatmap {_SLUG} --cases 500",
        ],
    }
