"""Finance month-end close workflow scenario.

The monthly financial close process covers data collection, reconciliation,
journal entries, management review, and financial reporting.  Median close
time at mid-market companies is 5–10 business days; AI can compress this by
automating data extraction and routine reconciliations.

Before: accountants and controllers perform all steps manually.
After: AI extracts and reconciles data; humans focus on exceptions and judgment.

Limitations: consolidation (multi-entity) not modeled.  Tax provision and
external audit workflows are separate.  ERP data quality issues are modeled
as error rates only.
"""

from __future__ import annotations

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
from b2b_workflow_simulator.workflow import Workflow

_SLUG = "finance-month-end-close"


def build_before_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-before",
        name="Finance Month-End Close — Manual",
        entry_node_id="data_collection",
        description="Manual close: accountants and controllers handle all reconciliation and reporting.",  # noqa: E501
    )
    accountant = HumanActor(
        actor_id="accountant", name="Staff Accountant",
        hourly_cost=55.0, speed_multiplier=1.0, error_rate=0.05,
    )
    controller = HumanActor(
        actor_id="controller", name="Controller",
        hourly_cost=110.0, speed_multiplier=1.0, error_rate=0.03,
        available_hours_per_day=7.0,
    )
    cfo = HumanActor(
        actor_id="cfo", name="CFO",
        hourly_cost=300.0, speed_multiplier=1.0, error_rate=0.01,
        available_hours_per_day=3.0,
    )
    for a in (accountant, controller, cfo):
        wf.add_actor(a)

    nodes = [
        Node("data_collection", "Data Collection from Systems", "accountant",
             base_duration_minutes=120.0),
        Node("reconciliation", "Account Reconciliation", "accountant",
             base_duration_minutes=180.0),
        Node("journal_entries", "Journal Entry Preparation", "accountant",
             base_duration_minutes=90.0),
        Node("controller_review", "Controller Review & Approval", "controller",
             base_duration_minutes=120.0),
        Node("financial_statements", "Financial Statement Preparation", "accountant",
             base_duration_minutes=150.0),
        Node("cfo_approval", "CFO Review & Sign-Off", "cfo",
             base_duration_minutes=60.0),
        Node("close_complete", "Close Complete — Reports Published", "controller",
             base_duration_minutes=30.0, is_terminal=True),
        Node("reopen_for_corrections", "Reopened for Corrections", "accountant",
             base_duration_minutes=180.0, is_terminal=True),
        Node("escalated_audit_item", "Escalated: Audit Item Found", "controller",
             base_duration_minutes=120.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("data_collection", "reconciliation", 1.0),
        Edge("reconciliation", "journal_entries", 0.82),
        Edge("reconciliation", "reopen_for_corrections", 0.18),
        Edge("journal_entries", "controller_review", 1.0),
        Edge("controller_review", "financial_statements", 0.85),
        Edge("controller_review", "reopen_for_corrections", 0.15),
        Edge("financial_statements", "cfo_approval", 1.0),
        Edge("cfo_approval", "close_complete", 0.88),
        Edge("cfo_approval", "escalated_audit_item", 0.12),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def build_after_workflow() -> Workflow:
    wf = Workflow(
        workflow_id=f"{_SLUG}-after",
        name="Finance Month-End Close — AI-Assisted",
        entry_node_id="ai_data_extraction",
        description="AI handles data extraction and reconciliation; humans review exceptions.",
    )
    ai_extractor = AIAgentActor(
        actor_id="ai_extractor", name="AI Data Extractor",
        cost_per_execution=5.00, speed_multiplier=0.12, error_rate=0.06, escalation_rate=0.12,
    )
    ai_reconciler = AIAgentActor(
        actor_id="ai_reconciler", name="AI Reconciliation Engine",
        cost_per_execution=8.00, speed_multiplier=0.18, error_rate=0.05, escalation_rate=0.18,
    )
    ai_je = AIAgentActor(
        actor_id="ai_je", name="AI Journal Entry Generator",
        cost_per_execution=3.00, speed_multiplier=0.10, error_rate=0.04, escalation_rate=0.15,
    )
    accountant = HumanActor(
        actor_id="accountant", name="Staff Accountant",
        hourly_cost=55.0, speed_multiplier=1.0, error_rate=0.03,
    )
    controller = HumanActor(
        actor_id="controller", name="Controller",
        hourly_cost=110.0, speed_multiplier=1.0, error_rate=0.02,
        available_hours_per_day=7.0,
    )
    cfo = HumanActor(
        actor_id="cfo", name="CFO",
        hourly_cost=300.0, speed_multiplier=1.0, error_rate=0.01,
        available_hours_per_day=3.0,
    )
    for a in (ai_extractor, ai_reconciler, ai_je, accountant, controller, cfo):
        wf.add_actor(a)

    nodes = [
        Node("ai_data_extraction", "AI Data Extraction", "ai_extractor",
             base_duration_minutes=120.0),
        Node("ai_reconciliation", "AI Reconciliation", "ai_reconciler",
             base_duration_minutes=180.0),
        Node("exception_review", "Accountant Exception Review", "accountant",
             base_duration_minutes=90.0),
        Node("ai_journal_entries", "AI Journal Entry Generation", "ai_je",
             base_duration_minutes=90.0),
        Node("controller_review", "Controller Review & Approval", "controller",
             base_duration_minutes=80.0),
        Node("financial_statements", "Financial Statement Prep", "accountant",
             base_duration_minutes=90.0),
        Node("cfo_approval", "CFO Review & Sign-Off", "cfo",
             base_duration_minutes=45.0),
        Node("close_complete", "Close Complete — Reports Published", "controller",
             base_duration_minutes=20.0, is_terminal=True),
        Node("reopen_for_corrections", "Reopened for Corrections", "accountant",
             base_duration_minutes=120.0, is_terminal=True),
        Node("escalated_audit_item", "Escalated: Audit Item Found", "controller",
             base_duration_minutes=90.0, is_terminal=True),
    ]
    for n in nodes:
        wf.add_node(n)

    edges = [
        Edge("ai_data_extraction", "ai_reconciliation", 1.0),
        Edge("ai_reconciliation", "ai_journal_entries", 0.68),
        Edge("ai_reconciliation", "exception_review", 0.32),
        Edge("exception_review", "ai_journal_entries", 0.80),
        Edge("exception_review", "reopen_for_corrections", 0.20),
        Edge("ai_journal_entries", "controller_review", 1.0),
        Edge("controller_review", "financial_statements", 0.86),
        Edge("controller_review", "reopen_for_corrections", 0.14),
        Edge("financial_statements", "cfo_approval", 1.0),
        Edge("cfo_approval", "close_complete", 0.88),
        Edge("cfo_approval", "escalated_audit_item", 0.12),
    ]
    for e in edges:
        wf.add_edge(e)
    wf.validate()
    return wf


def default_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=120, seed=42, implementation_cost=35_000.0,
        description=f"{_SLUG}: base assumptions",
    )


def conservative_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=120, seed=42, implementation_cost=35_000.0,
        ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.6,
        description=f"{_SLUG}: conservative (ERP data quality issues)",
    )


def aggressive_assumptions() -> AssumptionProfile:
    return AssumptionProfile(
        num_cases=120, seed=42, implementation_cost=35_000.0,
        ai_cost_multiplier=0.5, human_hourly_cost_multiplier=0.88,
        description=f"{_SLUG}: aggressive (clean data, mature AI)",
    )


def scenario_notes() -> dict:
    return {
        "limitations": [
            "Multi-entity consolidation not modeled; intercompany eliminations are separate.",
            "Tax provision and deferred tax calculations not included.",
            "Audit preparation and PBC list management are separate workflows.",
            "ERP data quality issues modeled as error/escalation rates only.",
        ],
        "commands": [
            f"b2b-simulator executive-snapshot {_SLUG} --cases 120 --implementation-cost 35000",
            f"b2b-simulator visualize-workflow {_SLUG} --format text",
        ],
    }
