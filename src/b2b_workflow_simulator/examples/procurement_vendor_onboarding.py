"""Procurement vendor onboarding workflow scenario.

New vendor onboarding from initial application through compliance check,
risk scoring, legal review, and system activation.  High manual overhead
in compliance and risk scoring stages creates cycle-time delays of 2–6
weeks at large enterprises.

Before: specialists handle each step manually.
After: AI automates compliance screening and risk scoring; legal and
final activation remain human-controlled.

Limitations: complexity of sanctions screening and third-party risk
management tools is not fully captured.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "procurement-vendor-onboarding"


def build_before_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="Procurement Vendor Onboarding — Manual",
        entry_node_id="vendor_application",
        description="Manual vendor onboarding: procurement specialists handle all steps.",
    )
    procurement_specialist = HumanActor(
        actor_id="procurement_specialist", name="Procurement Specialist",
        hourly_cost=60.0, speed_multiplier=1.0, error_rate=0.04,
    )
    compliance_officer = HumanActor(
        actor_id="compliance_officer", name="Compliance Officer",
        hourly_cost=85.0, speed_multiplier=1.0, error_rate=0.03,
        available_hours_per_day=6.0,
    )
    legal_counsel = HumanActor(
        actor_id="legal_counsel", name="Legal Counsel",
        hourly_cost=200.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=4.0,
    )
    for a in (procurement_specialist, compliance_officer, legal_counsel):
        wf.add_actor(a)

    nodes = [
        Node("vendor_application", "Vendor Application Review", "procurement_specialist",
             base_duration_minutes=30.0),
        Node("compliance_check", "Compliance & Sanctions Check", "compliance_officer",
             base_duration_minutes=45.0),
        Node("risk_scoring", "Vendor Risk Scoring", "compliance_officer",
             base_duration_minutes=40.0),
        Node("legal_review", "Legal Contract Review", "legal_counsel",
             base_duration_minutes=90.0),
        Node("system_setup", "ERP / System Setup", "procurement_specialist",
             base_duration_minutes=60.0),
        Node("onboarded", "Vendor Activated", "procurement_specialist",
             base_duration_minutes=15.0, is_terminal=True),
        Node("rejected_compliance", "Rejected: Compliance Failure", "compliance_officer",
             base_duration_minutes=20.0, is_terminal=True),
        Node("rejected_risk", "Rejected: High Risk", "compliance_officer",
             base_duration_minutes=20.0, is_terminal=True),
        Node("rejected_legal", "Rejected: Legal Review Failed", "legal_counsel",
             base_duration_minutes=30.0, is_terminal=True),
        Node("incomplete_application", "Returned: Incomplete", "procurement_specialist",
             base_duration_minutes=10.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("vendor_application", "compliance_check", 0.82),
        Edge("vendor_application", "incomplete_application", 0.18),
        Edge("compliance_check", "risk_scoring", 0.78),
        Edge("compliance_check", "rejected_compliance", 0.22),
        Edge("risk_scoring", "legal_review", 0.70),
        Edge("risk_scoring", "rejected_risk", 0.30),
        Edge("legal_review", "system_setup", 0.85),
        Edge("legal_review", "rejected_legal", 0.15),
        Edge("system_setup", "onboarded", 1.0),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="Procurement Vendor Onboarding — AI-Assisted",
        entry_node_id="vendor_application",
        description="AI handles compliance and risk screening; humans manage legal and activation.",
    )
    ai_compliance = AIAgentActor(
        actor_id="ai_compliance", name="AI Compliance Screener",
        cost_per_execution=3.00, speed_multiplier=0.12, error_rate=0.05, escalation_rate=0.15,
    )
    ai_risk = AIAgentActor(
        actor_id="ai_risk", name="AI Risk Scorer",
        cost_per_execution=2.50, speed_multiplier=0.10, error_rate=0.04, escalation_rate=0.12,
    )
    procurement_specialist = HumanActor(
        actor_id="procurement_specialist", name="Procurement Specialist",
        hourly_cost=60.0, speed_multiplier=1.0, error_rate=0.03,
    )
    compliance_officer = HumanActor(
        actor_id="compliance_officer", name="Compliance Officer",
        hourly_cost=85.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=6.0,
    )
    legal_counsel = HumanActor(
        actor_id="legal_counsel", name="Legal Counsel",
        hourly_cost=200.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=4.0,
    )
    for a in (ai_compliance, ai_risk, procurement_specialist, compliance_officer, legal_counsel):
        wf.add_actor(a)

    nodes = [
        Node("vendor_application", "Vendor Application Review", "procurement_specialist",
             base_duration_minutes=25.0),
        Node("ai_compliance_check", "AI Compliance Screening", "ai_compliance",
             base_duration_minutes=45.0),
        Node("ai_risk_score", "AI Risk Scoring", "ai_risk",
             base_duration_minutes=40.0),
        Node("compliance_escalation", "Human Compliance Review", "compliance_officer",
             base_duration_minutes=40.0),
        Node("legal_review", "Legal Contract Review", "legal_counsel",
             base_duration_minutes=70.0),
        Node("system_setup", "ERP / System Setup", "procurement_specialist",
             base_duration_minutes=45.0),
        Node("onboarded", "Vendor Activated", "procurement_specialist",
             base_duration_minutes=12.0, is_terminal=True),
        Node("rejected_compliance", "Rejected: Compliance Failure", "compliance_officer",
             base_duration_minutes=15.0, is_terminal=True),
        Node("rejected_risk", "Rejected: High Risk", "ai_risk",
             base_duration_minutes=10.0, is_terminal=True),
        Node("rejected_legal", "Rejected: Legal Review Failed", "legal_counsel",
             base_duration_minutes=20.0, is_terminal=True),
        Node("incomplete_application", "Returned: Incomplete", "procurement_specialist",
             base_duration_minutes=8.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("vendor_application", "ai_compliance_check", 0.84),
        Edge("vendor_application", "incomplete_application", 0.16),
        Edge("ai_compliance_check", "ai_risk_score", 0.72),
        Edge("ai_compliance_check", "compliance_escalation", 0.14),
        Edge("ai_compliance_check", "rejected_compliance", 0.14),
        Edge("compliance_escalation", "ai_risk_score", 0.65),
        Edge("compliance_escalation", "rejected_compliance", 0.35),
        Edge("ai_risk_score", "legal_review", 0.72),
        Edge("ai_risk_score", "rejected_risk", 0.28),
        Edge("legal_review", "system_setup", 0.86),
        Edge("legal_review", "rejected_legal", 0.14),
        Edge("system_setup", "onboarded", 1.0),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=200, seed=42, implementation_cost=25_000.0,
        description=f"{_SLUG}: base assumptions",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=200, seed=42, implementation_cost=25_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.5,
        description=f"{_SLUG}: conservative",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=200, seed=42, implementation_cost=25_000.0,
        ai_cost_multiplier=0.55, human_hourly_cost_multiplier=0.88,
        description=f"{_SLUG}: aggressive",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "Sanctions screening (OFAC, PEP) complexity not fully modeled.",
            "Cyber and ESG risk dimensions not included.",
            "Multi-tier supplier risk not captured.",
            "ERP integration complexity and data quality issues not modeled.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 200 --implementation-cost 25000",
            f"b2b-simulator visualize-workflow {_SLUG} --format text",
        ],
    }
