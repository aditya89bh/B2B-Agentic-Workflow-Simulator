"""Legal contract review workflow scenario.

Standard commercial contract review from receipt through negotiation to
execution.  Legal teams report contract review as one of the highest-volume,
most repetitive activities that AI is well-positioned to assist with.

Before: paralegals and attorneys handle all review and redlining.
After: AI generates first-pass redlines and risk flags; attorneys focus on
negotiation and non-standard clauses.

Limitations: contract negotiation complexity and counterparty behavior are
not modeled.  Regulatory context (GDPR, export control, etc.) is not
included.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "legal-contract-review"


def build_before_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="Legal Contract Review — Manual",
        entry_node_id="contract_receipt",
        description="Human-only contract review: paralegals and attorneys handle all steps.",
    )
    paralegal = HumanActor(
        actor_id="paralegal", name="Paralegal",
        hourly_cost=65.0, speed_multiplier=1.0, error_rate=0.05,
    )
    attorney = HumanActor(
        actor_id="attorney", name="Attorney",
        hourly_cost=280.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=5.0,
    )
    legal_ops = HumanActor(
        actor_id="legal_ops", name="Legal Ops Specialist",
        hourly_cost=70.0, speed_multiplier=1.0, error_rate=0.03,
    )
    for a in (paralegal, attorney, legal_ops):
        wf.add_actor(a)

    nodes = [
        Node("contract_receipt", "Contract Receipt & Classification", "legal_ops",
             base_duration_minutes=20.0),
        Node("paralegal_review", "Paralegal Initial Review", "paralegal",
             base_duration_minutes=90.0),
        Node("attorney_review", "Attorney Review & Redlining", "attorney",
             base_duration_minutes=120.0),
        Node("negotiation", "Counterparty Negotiation", "attorney",
             base_duration_minutes=180.0),
        Node("final_review", "Final Legal Sign-Off", "attorney",
             base_duration_minutes=45.0),
        Node("executed", "Contract Executed", "legal_ops",
             base_duration_minutes=15.0, is_terminal=True),
        Node("rejected_scope", "Out of Scope — Declined", "legal_ops",
             base_duration_minutes=10.0, is_terminal=True),
        Node("escalated_general_counsel", "Escalated to General Counsel", "attorney",
             base_duration_minutes=60.0, is_terminal=True),
        Node("stalled_negotiation", "Negotiation Stalled", "attorney",
             base_duration_minutes=30.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("contract_receipt", "paralegal_review", 0.88),
        Edge("contract_receipt", "rejected_scope", 0.12),
        Edge("paralegal_review", "attorney_review", 0.80),
        Edge("paralegal_review", "rejected_scope", 0.20),
        Edge("attorney_review", "negotiation", 0.65),
        Edge("attorney_review", "final_review", 0.25),
        Edge("attorney_review", "escalated_general_counsel", 0.10),
        Edge("negotiation", "final_review", 0.55),
        Edge("negotiation", "stalled_negotiation", 0.25),
        Edge("negotiation", "escalated_general_counsel", 0.20),
        Edge("final_review", "executed", 1.0),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="Legal Contract Review — AI-Assisted",
        entry_node_id="contract_receipt",
        description="AI generates first-pass redlines; attorneys focus on negotiation.",
    )
    ai_classifier = AIAgentActor(
        actor_id="ai_classifier", name="AI Contract Classifier",
        cost_per_execution=1.50, speed_multiplier=0.08, error_rate=0.05, escalation_rate=0.08,
    )
    ai_reviewer = AIAgentActor(
        actor_id="ai_reviewer", name="AI Contract Reviewer",
        cost_per_execution=8.00, speed_multiplier=0.15, error_rate=0.06, escalation_rate=0.20,
    )
    paralegal = HumanActor(
        actor_id="paralegal", name="Paralegal",
        hourly_cost=65.0, speed_multiplier=1.0, error_rate=0.04,
    )
    attorney = HumanActor(
        actor_id="attorney", name="Attorney",
        hourly_cost=280.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=5.0,
    )
    legal_ops = HumanActor(
        actor_id="legal_ops", name="Legal Ops Specialist",
        hourly_cost=70.0, speed_multiplier=1.0, error_rate=0.02,
    )
    for a in (ai_classifier, ai_reviewer, paralegal, attorney, legal_ops):
        wf.add_actor(a)

    nodes = [
        Node("contract_receipt", "Contract Receipt & Classification", "ai_classifier",
             base_duration_minutes=20.0),
        Node("ai_first_pass", "AI First-Pass Review & Redlining", "ai_reviewer",
             base_duration_minutes=90.0),
        Node("paralegal_qc", "Paralegal Quality Check", "paralegal",
             base_duration_minutes=45.0),
        Node("attorney_negotiation", "Attorney Negotiation & Sign-Off", "attorney",
             base_duration_minutes=90.0),
        Node("final_review", "Final Legal Approval", "attorney",
             base_duration_minutes=30.0),
        Node("executed", "Contract Executed", "legal_ops",
             base_duration_minutes=12.0, is_terminal=True),
        Node("rejected_scope", "Out of Scope — Declined", "legal_ops",
             base_duration_minutes=8.0, is_terminal=True),
        Node("escalated_general_counsel", "Escalated to General Counsel", "attorney",
             base_duration_minutes=50.0, is_terminal=True),
        Node("stalled_negotiation", "Negotiation Stalled", "attorney",
             base_duration_minutes=25.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("contract_receipt", "ai_first_pass", 0.86),
        Edge("contract_receipt", "rejected_scope", 0.14),
        Edge("ai_first_pass", "paralegal_qc", 0.82),
        Edge("ai_first_pass", "rejected_scope", 0.18),
        Edge("paralegal_qc", "attorney_negotiation", 0.70),
        Edge("paralegal_qc", "escalated_general_counsel", 0.30),
        Edge("attorney_negotiation", "final_review", 0.62),
        Edge("attorney_negotiation", "stalled_negotiation", 0.22),
        Edge("attorney_negotiation", "escalated_general_counsel", 0.16),
        Edge("final_review", "executed", 1.0),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=150, seed=42, implementation_cost=30_000.0,
        description=f"{_SLUG}: base assumptions",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=150, seed=42, implementation_cost=30_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.8,
        description=f"{_SLUG}: conservative (AI misses risk clauses)",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=150, seed=42, implementation_cost=30_000.0,
        ai_cost_multiplier=0.5, human_hourly_cost_multiplier=0.88,
        description=f"{_SLUG}: aggressive (mature AI legal review)",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "Counterparty negotiation behavior not modeled; actual cycle time depends on counterparty.",  # noqa: E501
            "Regulatory overlays (GDPR, export control, data privacy) not included.",
            "Contract value and risk level not differentiated; complex M&A or IP contracts differ.",
            "AI accuracy on novel or non-standard clauses may be lower than modeled.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 150 --implementation-cost 30000",
            f"b2b-simulator roi-waterfall {_SLUG} --cases 150 --implementation-cost 30000",
        ],
    }
