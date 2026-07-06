"""HR recruiting screening workflow scenario.

Candidate screening pipeline for a mid-sized company filling
professional/technical roles.  High volume of applications creates a
significant bottleneck at the resume review and initial phone-screen stages.

Before: all screening is human.  After: AI handles resume scoring and
initial qualification; humans conduct technical and cultural interviews.

Limitations: bias risk in AI screening is not modeled; requires careful
human oversight.  This simulation does not validate fairness or compliance
with equal employment opportunity laws.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "hr-recruiting-screening"


def build_before_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="HR Recruiting Screening — Manual",
        entry_node_id="application_receipt",
        description="Human-driven recruiting: recruiters screen all candidates.",
    )
    recruiter = HumanActor(
        actor_id="recruiter", name="HR Recruiter",
        hourly_cost=45.0, speed_multiplier=1.0, error_rate=0.05,
    )
    hiring_manager = HumanActor(
        actor_id="hiring_manager", name="Hiring Manager",
        hourly_cost=90.0, speed_multiplier=1.0, error_rate=0.03,
        available_hours_per_day=3.0,
    )
    hr_coordinator = HumanActor(
        actor_id="hr_coordinator", name="HR Coordinator",
        hourly_cost=38.0, speed_multiplier=1.0, error_rate=0.02,
    )
    for a in (recruiter, hiring_manager, hr_coordinator):
        wf.add_actor(a)

    nodes = [
        Node("application_receipt", "Application Receipt & ATS Entry", "hr_coordinator",
             base_duration_minutes=10.0),
        Node("resume_screen", "Resume Screening", "recruiter",
             base_duration_minutes=15.0),
        Node("phone_screen", "Recruiter Phone Screen", "recruiter",
             base_duration_minutes=30.0),
        Node("skills_assessment", "Skills Assessment Review", "hiring_manager",
             base_duration_minutes=25.0),
        Node("interview_scheduled", "Interview Scheduling", "hr_coordinator",
             base_duration_minutes=20.0, is_terminal=True),
        Node("rejected_resume", "Rejected at Resume Screen", "hr_coordinator",
             base_duration_minutes=5.0, is_terminal=True),
        Node("rejected_phone", "Rejected at Phone Screen", "hr_coordinator",
             base_duration_minutes=5.0, is_terminal=True),
        Node("rejected_assessment", "Rejected at Assessment", "hr_coordinator",
             base_duration_minutes=5.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("application_receipt", "resume_screen", 1.0),
        Edge("resume_screen", "phone_screen", 0.35),
        Edge("resume_screen", "rejected_resume", 0.65),
        Edge("phone_screen", "skills_assessment", 0.55),
        Edge("phone_screen", "rejected_phone", 0.45),
        Edge("skills_assessment", "interview_scheduled", 0.60),
        Edge("skills_assessment", "rejected_assessment", 0.40),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="HR Recruiting Screening — AI-Assisted",
        entry_node_id="application_receipt",
        description="AI screens resumes and qualifies candidates; humans conduct interviews.",
    )
    ai_screener = AIAgentActor(
        actor_id="ai_screener", name="AI Resume Screener",
        cost_per_execution=0.30, speed_multiplier=0.05, error_rate=0.08, escalation_rate=0.10,
    )
    ai_qualifier = AIAgentActor(
        actor_id="ai_qualifier", name="AI Candidate Qualifier",
        cost_per_execution=1.50, speed_multiplier=0.10, error_rate=0.06, escalation_rate=0.15,
    )
    recruiter = HumanActor(
        actor_id="recruiter", name="HR Recruiter",
        hourly_cost=45.0, speed_multiplier=1.0, error_rate=0.03,
    )
    hiring_manager = HumanActor(
        actor_id="hiring_manager", name="Hiring Manager",
        hourly_cost=90.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=3.0,
    )
    hr_coordinator = HumanActor(
        actor_id="hr_coordinator", name="HR Coordinator",
        hourly_cost=38.0, speed_multiplier=1.0, error_rate=0.02,
    )
    for a in (ai_screener, ai_qualifier, recruiter, hiring_manager, hr_coordinator):
        wf.add_actor(a)

    nodes = [
        Node("application_receipt", "Application Receipt", "hr_coordinator",
             base_duration_minutes=10.0),
        Node("ai_resume_screen", "AI Resume Scoring", "ai_screener",
             base_duration_minutes=15.0),
        Node("ai_qualification", "AI Candidate Qualification", "ai_qualifier",
             base_duration_minutes=30.0),
        Node("recruiter_review", "Recruiter Borderline Review", "recruiter",
             base_duration_minutes=20.0),
        Node("hiring_manager_screen", "Hiring Manager Screen", "hiring_manager",
             base_duration_minutes=25.0),
        Node("interview_scheduled", "Interview Scheduling", "hr_coordinator",
             base_duration_minutes=15.0, is_terminal=True),
        Node("rejected_resume", "Rejected at Resume Screen", "hr_coordinator",
             base_duration_minutes=3.0, is_terminal=True),
        Node("rejected_qualification", "Rejected at Qualification", "hr_coordinator",
             base_duration_minutes=3.0, is_terminal=True),
        Node("rejected_review", "Rejected at Manager Screen", "hr_coordinator",
             base_duration_minutes=3.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("application_receipt", "ai_resume_screen", 1.0),
        Edge("ai_resume_screen", "ai_qualification", 0.38),
        Edge("ai_resume_screen", "recruiter_review", 0.12),
        Edge("ai_resume_screen", "rejected_resume", 0.50),
        Edge("recruiter_review", "ai_qualification", 0.55),
        Edge("recruiter_review", "rejected_resume", 0.45),
        Edge("ai_qualification", "hiring_manager_screen", 0.65),
        Edge("ai_qualification", "rejected_qualification", 0.35),
        Edge("hiring_manager_screen", "interview_scheduled", 0.60),
        Edge("hiring_manager_screen", "rejected_review", 0.40),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=500, seed=42, implementation_cost=12_000.0,
        description=f"{_SLUG}: base assumptions",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=500, seed=42, implementation_cost=12_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.4,
        description=f"{_SLUG}: conservative (higher AI screening errors)",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=500, seed=42, implementation_cost=12_000.0,
        ai_cost_multiplier=0.5, human_hourly_cost_multiplier=0.85,
        description=f"{_SLUG}: aggressive (lower AI and human costs)",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "AI screening bias risk not modeled; requires human oversight and EEO compliance.",
            "Quality of hire not captured; a faster screen may not mean better candidates.",
            "Assumes uniform role type; specialized/executive search differs significantly.",
            "Candidate experience and employer brand effects not included.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 500 --implementation-cost 12000",
            f"b2b-simulator roi-waterfall {_SLUG} --cases 500 --implementation-cost 12000",
        ],
    }
