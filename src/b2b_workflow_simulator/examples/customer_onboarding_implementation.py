"""Customer onboarding / implementation workflow scenario.

B2B SaaS customer implementation from signed contract through go-live.
Implementation cycle time directly affects time-to-value for customers and
capacity utilization for the CS/implementation team.

Before: implementation managers and trainers handle all stages manually.
After: AI assists with discovery prep, configuration scripting, and QA;
humans focus on training and relationship management.

Limitations: customer readiness and internal champion availability are major
variables not captured by this simulation.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "customer-onboarding-implementation"


def build_before_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="Customer Onboarding — Manual Implementation",
        entry_node_id="kickoff_prep",
        description="Human-driven implementation: managers and trainers handle all stages.",
    )
    implementation_manager = HumanActor(
        actor_id="implementation_manager", name="Implementation Manager",
        hourly_cost=85.0, speed_multiplier=1.0, error_rate=0.04,
    )
    trainer = HumanActor(
        actor_id="trainer", name="Training Specialist",
        hourly_cost=70.0, speed_multiplier=1.0, error_rate=0.03,
    )
    technical_consultant = HumanActor(
        actor_id="technical_consultant", name="Technical Consultant",
        hourly_cost=120.0, speed_multiplier=1.0, error_rate=0.04,
        available_hours_per_day=6.0,
    )
    for a in (implementation_manager, trainer, technical_consultant):
        wf.add_actor(a)

    nodes = [
        Node("kickoff_prep", "Kickoff Preparation", "implementation_manager",
             base_duration_minutes=120.0),
        Node("discovery", "Business Requirements Discovery", "implementation_manager",
             base_duration_minutes=240.0),
        Node("configuration", "System Configuration", "technical_consultant",
             base_duration_minutes=360.0),
        Node("training", "End-User Training", "trainer",
             base_duration_minutes=300.0),
        Node("uat", "User Acceptance Testing", "implementation_manager",
             base_duration_minutes=180.0),
        Node("go_live", "Go-Live & Hypercare", "implementation_manager",
             base_duration_minutes=120.0),
        Node("onboarded_successfully", "Onboarding Complete", "implementation_manager",
             base_duration_minutes=30.0, is_terminal=True),
        Node("delayed_configuration", "Configuration Rework Required", "technical_consultant",
             base_duration_minutes=240.0, is_terminal=True),
        Node("delayed_uat", "UAT Failed — Rework Required", "implementation_manager",
             base_duration_minutes=180.0, is_terminal=True),
        Node("churned_during_onboarding", "Customer Churned During Onboarding",
             "implementation_manager",
             base_duration_minutes=60.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("kickoff_prep", "discovery", 1.0),
        Edge("discovery", "configuration", 1.0),
        Edge("configuration", "training", 0.80),
        Edge("configuration", "delayed_configuration", 0.20),
        Edge("training", "uat", 1.0),
        Edge("uat", "go_live", 0.72),
        Edge("uat", "delayed_uat", 0.20),
        Edge("uat", "churned_during_onboarding", 0.08),
        Edge("go_live", "onboarded_successfully", 0.90),
        Edge("go_live", "churned_during_onboarding", 0.10),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="Customer Onboarding — AI-Assisted Implementation",
        entry_node_id="ai_kickoff_prep",
        description="AI handles discovery templates, config scripting, and QA; humans drive training.",  # noqa: E501
    )
    ai_prep = AIAgentActor(
        actor_id="ai_prep", name="AI Kickoff Prep Assistant",
        cost_per_execution=5.00, speed_multiplier=0.20, error_rate=0.05, escalation_rate=0.10,
    )
    ai_config = AIAgentActor(
        actor_id="ai_config", name="AI Configuration Engine",
        cost_per_execution=12.00, speed_multiplier=0.25, error_rate=0.06, escalation_rate=0.18,
    )
    ai_qa = AIAgentActor(
        actor_id="ai_qa", name="AI QA Testing Bot",
        cost_per_execution=3.00, speed_multiplier=0.15, error_rate=0.05, escalation_rate=0.15,
    )
    implementation_manager = HumanActor(
        actor_id="implementation_manager", name="Implementation Manager",
        hourly_cost=85.0, speed_multiplier=1.0, error_rate=0.03,
    )
    trainer = HumanActor(
        actor_id="trainer", name="Training Specialist",
        hourly_cost=70.0, speed_multiplier=1.0, error_rate=0.02,
    )
    technical_consultant = HumanActor(
        actor_id="technical_consultant", name="Technical Consultant",
        hourly_cost=120.0, speed_multiplier=1.0, error_rate=0.03,
        available_hours_per_day=6.0,
    )
    for a in (ai_prep, ai_config, ai_qa, implementation_manager, trainer, technical_consultant):
        wf.add_actor(a)

    nodes = [
        Node("ai_kickoff_prep", "AI Kickoff Preparation", "ai_prep",
             base_duration_minutes=120.0),
        Node("discovery", "Business Requirements Discovery", "implementation_manager",
             base_duration_minutes=180.0),
        Node("ai_configuration", "AI System Configuration", "ai_config",
             base_duration_minutes=360.0),
        Node("config_review", "Technical Consultant Config Review", "technical_consultant",
             base_duration_minutes=120.0),
        Node("training", "End-User Training", "trainer",
             base_duration_minutes=240.0),
        Node("ai_uat", "AI Automated UAT Testing", "ai_qa",
             base_duration_minutes=180.0),
        Node("go_live", "Go-Live & Hypercare", "implementation_manager",
             base_duration_minutes=90.0),
        Node("onboarded_successfully", "Onboarding Complete", "implementation_manager",
             base_duration_minutes=20.0, is_terminal=True),
        Node("delayed_configuration", "Configuration Rework Required", "technical_consultant",
             base_duration_minutes=180.0, is_terminal=True),
        Node("delayed_uat", "UAT Failed — Rework Required", "implementation_manager",
             base_duration_minutes=120.0, is_terminal=True),
        Node("churned_during_onboarding", "Customer Churned", "implementation_manager",
             base_duration_minutes=45.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("ai_kickoff_prep", "discovery", 1.0),
        Edge("discovery", "ai_configuration", 1.0),
        Edge("ai_configuration", "config_review", 0.82),
        Edge("ai_configuration", "delayed_configuration", 0.18),
        Edge("config_review", "training", 1.0),
        Edge("training", "ai_uat", 1.0),
        Edge("ai_uat", "go_live", 0.74),
        Edge("ai_uat", "delayed_uat", 0.18),
        Edge("ai_uat", "churned_during_onboarding", 0.08),
        Edge("go_live", "onboarded_successfully", 0.91),
        Edge("go_live", "churned_during_onboarding", 0.09),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=200, seed=42, implementation_cost=20_000.0,
        description=f"{_SLUG}: base assumptions",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=200, seed=42, implementation_cost=20_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.5,
        description=f"{_SLUG}: conservative (complex integrations)",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=200, seed=42, implementation_cost=20_000.0,
        ai_cost_multiplier=0.55, human_hourly_cost_multiplier=0.88,
        description=f"{_SLUG}: aggressive (standardized product, mature AI)",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "Customer readiness and internal champion availability not modeled.",
            "Custom integrations and data migration complexity not captured.",
            "Contract value and implementation tier (SMB vs Enterprise) not differentiated.",
            "Renewal and expansion workflow are separate from initial onboarding.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 200 --implementation-cost 20000",
            f"b2b-simulator consultant-packet {_SLUG} --cases 200 --implementation-cost 20000",
        ],
    }
