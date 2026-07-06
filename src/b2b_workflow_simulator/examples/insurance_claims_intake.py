"""Insurance claims intake workflow scenario.

First notice of loss (FNOL) through initial adjudication for property and
casualty insurance.  Claims volume can be extremely high after catastrophic
events; the AI opportunity is primarily in triage, data extraction, and
routine adjudication of low-complexity claims.

Before: adjusters manually handle all steps.  After: AI handles intake,
coverage verification, and simple claim decisions; complex claims route
to senior adjusters.

Limitations: fraud detection is modeled as an error/escalation signal, not
a full SIU workflow.  Catastrophe surge (CAT) periods are not modeled.
Regulatory state-specific requirements are not included.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "insurance-claims-intake"


def build_before_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="Insurance Claims Intake — Manual",
        entry_node_id="fnol_receipt",
        description="Manual claims intake: adjusters handle all steps.",
    )
    claims_adjuster = HumanActor(
        actor_id="claims_adjuster", name="Claims Adjuster",
        hourly_cost=55.0, speed_multiplier=1.0, error_rate=0.04,
    )
    senior_adjuster = HumanActor(
        actor_id="senior_adjuster", name="Senior Adjuster",
        hourly_cost=80.0, speed_multiplier=1.0, error_rate=0.02,
    )
    fraud_analyst = HumanActor(
        actor_id="fraud_analyst", name="Fraud Analyst",
        hourly_cost=70.0, speed_multiplier=1.0, error_rate=0.03,
    )
    for a in (claims_adjuster, senior_adjuster, fraud_analyst):
        wf.add_actor(a)

    nodes = [
        Node("fnol_receipt", "FNOL Receipt & Logging", "claims_adjuster",
             base_duration_minutes=25.0),
        Node("coverage_verification", "Coverage Verification", "claims_adjuster",
             base_duration_minutes=30.0),
        Node("fraud_screening", "Fraud Screening", "fraud_analyst",
             base_duration_minutes=20.0),
        Node("adjudication", "Initial Adjudication", "claims_adjuster",
             base_duration_minutes=40.0),
        Node("complex_review", "Complex Claim Review", "senior_adjuster",
             base_duration_minutes=60.0),
        Node("approved_payment", "Approved for Payment", "claims_adjuster",
             base_duration_minutes=15.0, is_terminal=True),
        Node("denied_claim", "Claim Denied", "claims_adjuster",
             base_duration_minutes=20.0, is_terminal=True),
        Node("siu_referral", "SIU Fraud Referral", "fraud_analyst",
             base_duration_minutes=30.0, is_terminal=True),
        Node("no_coverage", "No Coverage — Closed", "claims_adjuster",
             base_duration_minutes=10.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("fnol_receipt", "coverage_verification", 0.90),
        Edge("fnol_receipt", "no_coverage", 0.10),
        Edge("coverage_verification", "fraud_screening", 0.92),
        Edge("coverage_verification", "no_coverage", 0.08),
        Edge("fraud_screening", "adjudication", 0.85),
        Edge("fraud_screening", "siu_referral", 0.15),
        Edge("adjudication", "approved_payment", 0.60),
        Edge("adjudication", "complex_review", 0.30),
        Edge("adjudication", "denied_claim", 0.10),
        Edge("complex_review", "approved_payment", 0.65),
        Edge("complex_review", "denied_claim", 0.35),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="Insurance Claims Intake — AI-Assisted",
        entry_node_id="ai_fnol",
        description="AI handles intake, coverage check, and fraud screening; humans adjudicate complex claims.",  # noqa: E501
    )
    ai_intake = AIAgentActor(
        actor_id="ai_intake", name="AI FNOL Processor",
        cost_per_execution=0.60, speed_multiplier=0.07, error_rate=0.05, escalation_rate=0.08,
    )
    ai_coverage = AIAgentActor(
        actor_id="ai_coverage", name="AI Coverage Verifier",
        cost_per_execution=1.20, speed_multiplier=0.10, error_rate=0.04, escalation_rate=0.12,
    )
    ai_fraud = AIAgentActor(
        actor_id="ai_fraud", name="AI Fraud Detector",
        cost_per_execution=2.00, speed_multiplier=0.12, error_rate=0.06, escalation_rate=0.10,
    )
    senior_adjuster = HumanActor(
        actor_id="senior_adjuster", name="Senior Adjuster",
        hourly_cost=80.0, speed_multiplier=1.0, error_rate=0.02,
    )
    claims_adjuster = HumanActor(
        actor_id="claims_adjuster", name="Claims Adjuster",
        hourly_cost=55.0, speed_multiplier=1.0, error_rate=0.03,
    )
    for a in (ai_intake, ai_coverage, ai_fraud, senior_adjuster, claims_adjuster):
        wf.add_actor(a)

    nodes = [
        Node("ai_fnol", "AI FNOL Processing", "ai_intake",
             base_duration_minutes=25.0),
        Node("ai_coverage_check", "AI Coverage Verification", "ai_coverage",
             base_duration_minutes=30.0),
        Node("ai_fraud_check", "AI Fraud Screening", "ai_fraud",
             base_duration_minutes=20.0),
        Node("auto_adjudication", "Automated Adjudication", "ai_fraud",
             base_duration_minutes=40.0),
        Node("complex_review", "Senior Adjuster Review", "senior_adjuster",
             base_duration_minutes=45.0),
        Node("approved_payment", "Approved for Payment", "claims_adjuster",
             base_duration_minutes=12.0, is_terminal=True),
        Node("denied_claim", "Claim Denied", "claims_adjuster",
             base_duration_minutes=15.0, is_terminal=True),
        Node("siu_referral", "SIU Fraud Referral", "senior_adjuster",
             base_duration_minutes=20.0, is_terminal=True),
        Node("no_coverage", "No Coverage — Closed", "claims_adjuster",
             base_duration_minutes=8.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("ai_fnol", "ai_coverage_check", 0.92),
        Edge("ai_fnol", "no_coverage", 0.08),
        Edge("ai_coverage_check", "ai_fraud_check", 0.90),
        Edge("ai_coverage_check", "no_coverage", 0.10),
        Edge("ai_fraud_check", "auto_adjudication", 0.84),
        Edge("ai_fraud_check", "siu_referral", 0.16),
        Edge("auto_adjudication", "approved_payment", 0.58),
        Edge("auto_adjudication", "complex_review", 0.28),
        Edge("auto_adjudication", "denied_claim", 0.14),
        Edge("complex_review", "approved_payment", 0.62),
        Edge("complex_review", "denied_claim", 0.38),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=400, seed=42, implementation_cost=22_000.0,
        description=f"{_SLUG}: base assumptions",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=400, seed=42, implementation_cost=22_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.5,
        description=f"{_SLUG}: conservative (higher AI error/cost)",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=400, seed=42, implementation_cost=22_000.0,
        ai_cost_multiplier=0.55, human_hourly_cost_multiplier=0.9,
        description=f"{_SLUG}: aggressive (mature AI platform)",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "Fraud detection modeled as error/escalation rates, not a full SIU workflow.",
            "CAT (catastrophe) surge not modeled; volumes can 10× during events.",
            "State-specific regulatory requirements not included.",
            "Liability, workers comp, and specialty lines have different workflows.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 400 --implementation-cost 22000",
            f"b2b-simulator roi-waterfall {_SLUG} --cases 400 --implementation-cost 22000",
        ],
    }
