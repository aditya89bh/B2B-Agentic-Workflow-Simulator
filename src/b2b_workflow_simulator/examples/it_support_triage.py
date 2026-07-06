"""IT support incident triage workflow scenario.

Helpdesk incident management from first-contact triage through L1, L2, and
L3 resolution.  AI is particularly effective at L1 (password resets, access
requests, known-issue lookups) and incident routing.

Before: all triage and L1 resolution handled by human agents.
After: AI handles auto-resolution for common requests; humans focus on
complex and escalated incidents.

Limitations: CMDB data quality and knowledge base coverage significantly
affect AI resolution rates; modeled as error/escalation rates.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "it-support-triage"


def build_before_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="IT Support Triage — Manual",
        entry_node_id="incident_receipt",
        description="Human-only IT support: L1 agents triage and resolve all incidents.",
    )
    l1_agent = HumanActor(
        actor_id="l1_agent", name="L1 Support Agent",
        hourly_cost=35.0, speed_multiplier=1.0, error_rate=0.06,
    )
    l2_engineer = HumanActor(
        actor_id="l2_engineer", name="L2 Engineer",
        hourly_cost=65.0, speed_multiplier=1.0, error_rate=0.04,
    )
    l3_specialist = HumanActor(
        actor_id="l3_specialist", name="L3 Specialist",
        hourly_cost=95.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=6.0,
    )
    for a in (l1_agent, l2_engineer, l3_specialist):
        wf.add_actor(a)

    nodes = [
        Node("incident_receipt", "Incident Receipt & Classification", "l1_agent",
             base_duration_minutes=10.0),
        Node("l1_resolution", "L1 Resolution Attempt", "l1_agent",
             base_duration_minutes=25.0),
        Node("l2_diagnosis", "L2 Technical Diagnosis", "l2_engineer",
             base_duration_minutes=45.0),
        Node("l3_resolution", "L3 Specialist Resolution", "l3_specialist",
             base_duration_minutes=90.0),
        Node("resolved_l1", "Resolved at L1", "l1_agent",
             base_duration_minutes=5.0, is_terminal=True),
        Node("resolved_l2", "Resolved at L2", "l2_engineer",
             base_duration_minutes=10.0, is_terminal=True),
        Node("resolved_l3", "Resolved at L3", "l3_specialist",
             base_duration_minutes=15.0, is_terminal=True),
        Node("vendor_escalation", "Escalated to Vendor", "l3_specialist",
             base_duration_minutes=20.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("incident_receipt", "l1_resolution", 1.0),
        Edge("l1_resolution", "resolved_l1", 0.55),
        Edge("l1_resolution", "l2_diagnosis", 0.45),
        Edge("l2_diagnosis", "resolved_l2", 0.60),
        Edge("l2_diagnosis", "l3_resolution", 0.30),
        Edge("l2_diagnosis", "vendor_escalation", 0.10),
        Edge("l3_resolution", "resolved_l3", 0.80),
        Edge("l3_resolution", "vendor_escalation", 0.20),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="IT Support Triage — AI-Assisted",
        entry_node_id="incident_receipt",
        description="AI resolves common incidents; humans handle complex and escalated cases.",
    )
    ai_triage = AIAgentActor(
        actor_id="ai_triage", name="AI Incident Classifier",
        cost_per_execution=0.20, speed_multiplier=0.04, error_rate=0.07, escalation_rate=0.15,
    )
    ai_l1 = AIAgentActor(
        actor_id="ai_l1", name="AI L1 Resolver",
        cost_per_execution=0.80, speed_multiplier=0.08, error_rate=0.08, escalation_rate=0.30,
    )
    l2_engineer = HumanActor(
        actor_id="l2_engineer", name="L2 Engineer",
        hourly_cost=65.0, speed_multiplier=1.0, error_rate=0.03,
    )
    l3_specialist = HumanActor(
        actor_id="l3_specialist", name="L3 Specialist",
        hourly_cost=95.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=6.0,
    )
    l1_agent = HumanActor(
        actor_id="l1_agent", name="L1 Support Agent",
        hourly_cost=35.0, speed_multiplier=1.0, error_rate=0.04,
    )
    for a in (ai_triage, ai_l1, l2_engineer, l3_specialist, l1_agent):
        wf.add_actor(a)

    nodes = [
        Node("incident_receipt", "AI Incident Classification", "ai_triage",
             base_duration_minutes=10.0),
        Node("ai_l1_resolution", "AI L1 Auto-Resolution", "ai_l1",
             base_duration_minutes=25.0),
        Node("human_l1_review", "Human L1 Oversight", "l1_agent",
             base_duration_minutes=15.0),
        Node("l2_diagnosis", "L2 Technical Diagnosis", "l2_engineer",
             base_duration_minutes=35.0),
        Node("l3_resolution", "L3 Specialist Resolution", "l3_specialist",
             base_duration_minutes=70.0),
        Node("resolved_ai", "Resolved by AI", "l1_agent",
             base_duration_minutes=3.0, is_terminal=True),
        Node("resolved_l1", "Resolved at L1", "l1_agent",
             base_duration_minutes=5.0, is_terminal=True),
        Node("resolved_l2", "Resolved at L2", "l2_engineer",
             base_duration_minutes=8.0, is_terminal=True),
        Node("resolved_l3", "Resolved at L3", "l3_specialist",
             base_duration_minutes=12.0, is_terminal=True),
        Node("vendor_escalation", "Escalated to Vendor", "l3_specialist",
             base_duration_minutes=15.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("incident_receipt", "ai_l1_resolution", 1.0),
        Edge("ai_l1_resolution", "resolved_ai", 0.50),
        Edge("ai_l1_resolution", "human_l1_review", 0.20),
        Edge("ai_l1_resolution", "l2_diagnosis", 0.30),
        Edge("human_l1_review", "resolved_l1", 0.65),
        Edge("human_l1_review", "l2_diagnosis", 0.35),
        Edge("l2_diagnosis", "resolved_l2", 0.62),
        Edge("l2_diagnosis", "l3_resolution", 0.28),
        Edge("l2_diagnosis", "vendor_escalation", 0.10),
        Edge("l3_resolution", "resolved_l3", 0.80),
        Edge("l3_resolution", "vendor_escalation", 0.20),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=500, seed=42, implementation_cost=15_000.0,
        description=f"{_SLUG}: base assumptions",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=500, seed=42, implementation_cost=15_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.4,
        description=f"{_SLUG}: conservative (low KB coverage)",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=500, seed=42, implementation_cost=15_000.0,
        ai_cost_multiplier=0.45, human_hourly_cost_multiplier=0.85,
        description=f"{_SLUG}: aggressive (high KB coverage, mature AI)",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "CMDB data quality and knowledge base coverage significantly affect AI resolution rates.",  # noqa: E501
            "Major incident (P1/P2) management not modeled; this covers routine service requests.",
            "Change management and problem management processes are separate workflows.",
            "On-call escalation and SLA breach penalties not included.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 500 --implementation-cost 15000",
            f"b2b-simulator bottleneck-heatmap {_SLUG} --cases 500",
        ],
    }
