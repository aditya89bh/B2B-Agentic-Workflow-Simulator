"""Bundled example: B2B SaaS company organizational digital twin.

This module provides a ready-to-use ``Organization``, ``OrgBudget``, and
``SharedResourcePool`` for a mid-sized B2B SaaS company with six
departments.  It also wires the three existing workflow examples
(sales lead qualification, invoice processing, and customer support
ticket resolution) into the appropriate departments and teams.

Structure::

    Acme B2B SaaS
    ├─ Sales
    │   └─ Sales Development Team
    ├─ Customer Success
    │   └─ CS Operations Team
    ├─ Finance
    │   └─ Finance Operations Team
    ├─ Legal
    │   └─ Legal & Compliance Team
    ├─ Operations
    │   └─ Process Excellence Team
    └─ AI Transformation Office
        └─ AI Ops Team

The three workflows map to departments as follows:

- Sales Lead Qualification → Sales
- Invoice Processing → Finance
- Customer Support Ticket Resolution → Customer Success
"""

from __future__ import annotations

from b2b_workflow_simulator.budget import (
    AI_TOOLING,
    HIRING,
    IMPLEMENTATION,
    OPERATING,
    TRAINING,
    DepartmentBudget,
    OrgBudget,
)
from b2b_workflow_simulator.org_model import (
    Department,
    Organization,
    ReportingLine,
    Role,
    Team,
)
from b2b_workflow_simulator.shared_resources import (
    AI_AGENT,
    EXTERNAL_VENDOR,
    FINANCE_APPROVER,
    LEGAL_REVIEWER,
    MANAGER,
    SOFTWARE_TOOL,
    SPECIALIST,
    SharedResource,
    SharedResourcePool,
)

_ORG_ID = "acme-saas"
_ORG_NAME = "Acme B2B SaaS"

_WORKFLOW_SALES = "sales-lead-qualification"
_WORKFLOW_INVOICE = "invoice-processing"
_WORKFLOW_SUPPORT = "customer-support-ticket-resolution"


def build_saas_org() -> Organization:
    """Build and return the Acme B2B SaaS organization model.

    Returns:
        A fully populated :class:`~b2b_workflow_simulator.org_model.Organization`
        with 6 departments, 6 teams, 18 roles, and 3 workflow associations.
    """
    org = Organization(org_id=_ORG_ID, name=_ORG_NAME)

    # ------------------------------------------------------------------
    # Departments
    # ------------------------------------------------------------------
    sales_dept = Department(dept_id="sales", name="Sales")
    cs_dept = Department(dept_id="customer-success", name="Customer Success")
    finance_dept = Department(dept_id="finance", name="Finance")
    legal_dept = Department(dept_id="legal", name="Legal")
    ops_dept = Department(dept_id="operations", name="Operations")
    ai_dept = Department(dept_id="ai-transformation", name="AI Transformation Office")

    for dept in (sales_dept, cs_dept, finance_dept, legal_dept, ops_dept, ai_dept):
        org.add_department(dept)

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------
    sales_team = Team(team_id="sales-dev", name="Sales Development Team", department_id="sales")
    cs_team = Team(team_id="cs-ops", name="CS Operations Team", department_id="customer-success")
    finance_team = Team(
        team_id="finance-ops", name="Finance Operations Team", department_id="finance"
    )
    legal_team = Team(
        team_id="legal-compliance",
        name="Legal & Compliance Team",
        department_id="legal",
    )
    ops_team = Team(
        team_id="process-excellence",
        name="Process Excellence Team",
        department_id="operations",
    )
    ai_team = Team(team_id="ai-ops", name="AI Ops Team", department_id="ai-transformation")

    for team in (sales_team, cs_team, finance_team, legal_team, ops_team, ai_team):
        org.add_team(team)

    sales_dept.add_team("sales-dev")
    cs_dept.add_team("cs-ops")
    finance_dept.add_team("finance-ops")
    legal_dept.add_team("legal-compliance")
    ops_dept.add_team("process-excellence")
    ai_dept.add_team("ai-ops")

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    roles = [
        Role(
            role_id="vp-sales",
            name="VP of Sales",
            actor_id="sales-rep",
            department_id="sales",
            team_id="sales-dev",
            is_manager=True,
        ),
        Role(
            role_id="sales-ae",
            name="Account Executive",
            actor_id="sales-rep",
            department_id="sales",
            team_id="sales-dev",
        ),
        Role(
            role_id="sales-sdr",
            name="Sales Development Rep",
            actor_id="sdr",
            department_id="sales",
            team_id="sales-dev",
        ),
        Role(
            role_id="sales-ai-qualifier",
            name="AI Lead Qualifier",
            actor_id="ai-qualifier",
            department_id="sales",
            team_id="sales-dev",
            is_ai_agent=True,
        ),
        Role(
            role_id="cs-manager",
            name="CS Manager",
            actor_id="cs-agent",
            department_id="customer-success",
            team_id="cs-ops",
            is_manager=True,
        ),
        Role(
            role_id="cs-agent-role",
            name="Customer Success Agent",
            actor_id="cs-agent",
            department_id="customer-success",
            team_id="cs-ops",
        ),
        Role(
            role_id="cs-ai-support",
            name="AI Support Bot",
            actor_id="ai-support-bot",
            department_id="customer-success",
            team_id="cs-ops",
            is_ai_agent=True,
        ),
        Role(
            role_id="finance-manager",
            name="Finance Manager",
            actor_id="accountant",
            department_id="finance",
            team_id="finance-ops",
            is_manager=True,
        ),
        Role(
            role_id="finance-ap",
            name="Accounts Payable Specialist",
            actor_id="accountant",
            department_id="finance",
            team_id="finance-ops",
        ),
        Role(
            role_id="finance-ai-extractor",
            name="AI Data Extractor",
            actor_id="ai-extractor",
            department_id="finance",
            team_id="finance-ops",
            is_ai_agent=True,
        ),
        Role(
            role_id="legal-counsel",
            name="Legal Counsel",
            actor_id="legal-reviewer",
            department_id="legal",
            team_id="legal-compliance",
            is_manager=True,
        ),
        Role(
            role_id="legal-paralegal",
            name="Paralegal",
            actor_id="legal-reviewer",
            department_id="legal",
            team_id="legal-compliance",
        ),
        Role(
            role_id="ops-director",
            name="Operations Director",
            actor_id="ops-specialist",
            department_id="operations",
            team_id="process-excellence",
            is_manager=True,
        ),
        Role(
            role_id="ops-analyst",
            name="Process Analyst",
            actor_id="ops-specialist",
            department_id="operations",
            team_id="process-excellence",
        ),
        Role(
            role_id="ai-cto",
            name="Chief AI Officer",
            actor_id="ai-ops-lead",
            department_id="ai-transformation",
            team_id="ai-ops",
            is_manager=True,
        ),
        Role(
            role_id="ai-engineer",
            name="AI Engineer",
            actor_id="ai-engineer",
            department_id="ai-transformation",
            team_id="ai-ops",
        ),
        Role(
            role_id="ai-analyst",
            name="AI Deployment Analyst",
            actor_id="ai-analyst",
            department_id="ai-transformation",
            team_id="ai-ops",
        ),
        Role(
            role_id="cfo",
            name="CFO",
            actor_id="finance-approver",
            department_id="finance",
            team_id="finance-ops",
            is_manager=True,
        ),
    ]
    for role in roles:
        org.add_role(role)
        team_id = role.team_id
        if team_id and team_id in org.teams:
            org.get_team(team_id).add_role(role.role_id)

    # ------------------------------------------------------------------
    # Reporting lines
    # ------------------------------------------------------------------
    reporting_lines = [
        ReportingLine(manager_role_id="vp-sales", direct_report_role_id="sales-ae"),
        ReportingLine(manager_role_id="vp-sales", direct_report_role_id="sales-sdr"),
        ReportingLine(manager_role_id="vp-sales", direct_report_role_id="sales-ai-qualifier"),
        ReportingLine(manager_role_id="cs-manager", direct_report_role_id="cs-agent-role"),
        ReportingLine(manager_role_id="cs-manager", direct_report_role_id="cs-ai-support"),
        ReportingLine(manager_role_id="finance-manager", direct_report_role_id="finance-ap"),
        ReportingLine(
            manager_role_id="finance-manager", direct_report_role_id="finance-ai-extractor"
        ),
        ReportingLine(manager_role_id="legal-counsel", direct_report_role_id="legal-paralegal"),
        ReportingLine(manager_role_id="ops-director", direct_report_role_id="ops-analyst"),
        ReportingLine(manager_role_id="ai-cto", direct_report_role_id="ai-engineer"),
        ReportingLine(manager_role_id="ai-cto", direct_report_role_id="ai-analyst"),
        ReportingLine(manager_role_id="cfo", direct_report_role_id="finance-manager"),
    ]
    for line in reporting_lines:
        org.add_reporting_line(line)

    # ------------------------------------------------------------------
    # Workflow associations
    # ------------------------------------------------------------------
    org.add_workflow_id(_WORKFLOW_SALES)
    org.add_workflow_id(_WORKFLOW_INVOICE)
    org.add_workflow_id(_WORKFLOW_SUPPORT)

    sales_dept.add_workflow(_WORKFLOW_SALES)
    sales_team.add_workflow(_WORKFLOW_SALES)

    finance_dept.add_workflow(_WORKFLOW_INVOICE)
    finance_team.add_workflow(_WORKFLOW_INVOICE)

    cs_dept.add_workflow(_WORKFLOW_SUPPORT)
    cs_team.add_workflow(_WORKFLOW_SUPPORT)

    return org


def build_saas_org_budget() -> OrgBudget:
    """Build and return the Acme B2B SaaS annual budget model.

    Returns:
        An :class:`~b2b_workflow_simulator.budget.OrgBudget` with
        department-level allocations across five budget categories.
    """
    org_budget = OrgBudget(org_id=_ORG_ID)

    dept_configs = [
        ("sales", 800_000, {
            OPERATING: 500_000, HIRING: 150_000, AI_TOOLING: 100_000, TRAINING: 50_000,
        }),
        ("customer-success", 600_000, {
            OPERATING: 400_000, HIRING: 100_000, AI_TOOLING: 80_000, TRAINING: 20_000,
        }),
        ("finance", 400_000, {
            OPERATING: 280_000, HIRING: 60_000, IMPLEMENTATION: 40_000, TRAINING: 20_000,
        }),
        ("legal", 350_000, {OPERATING: 300_000, HIRING: 30_000, TRAINING: 20_000}),
        ("operations", 300_000, {
            OPERATING: 200_000, IMPLEMENTATION: 60_000, AI_TOOLING: 25_000, TRAINING: 15_000,
        }),
        ("ai-transformation", 500_000, {
            AI_TOOLING: 250_000, HIRING: 150_000, IMPLEMENTATION: 75_000, TRAINING: 25_000,
        }),
    ]
    for dept_id, annual, allocations in dept_configs:
        dept_budget = DepartmentBudget(dept_id=dept_id, annual_budget=annual)
        for cat, amount in allocations.items():
            dept_budget.allocate(cat, amount)
        org_budget.add_dept_budget(dept_budget)

    return org_budget


def build_saas_shared_resources() -> SharedResourcePool:
    """Build and return the Acme B2B SaaS shared resource pool.

    Returns:
        A :class:`~b2b_workflow_simulator.shared_resources.SharedResourcePool`
        with eight shared resources serving multiple departments, each
        wired to the workflow actor IDs from the bundled examples via
        ``actor_ids``.
    """
    pool = SharedResourcePool(org_id=_ORG_ID)

    # actor_ids reference the workflow actor IDs from the bundled examples
    # (sales-lead-qualification-after, invoice-processing-after,
    #  customer-support-ticket-resolution-after).
    resources = [
        SharedResource(
            resource_id="legal-counsel",
            name="Legal Counsel",
            resource_type=LEGAL_REVIEWER,
            capacity_minutes_per_day=240.0,
            cost_per_use=150.0,
            department_ids=["legal", "sales", "finance"],
            actor_ids=["support_reviewer", "approval_agent"],
        ),
        SharedResource(
            resource_id="finance-approver",
            name="Finance Approver (CFO)",
            resource_type=FINANCE_APPROVER,
            capacity_minutes_per_day=120.0,
            cost_per_use=200.0,
            department_ids=["finance", "operations"],
            actor_ids=["ap_specialist"],
        ),
        SharedResource(
            resource_id="ops-specialist",
            name="Operations Specialist",
            resource_type=SPECIALIST,
            capacity_minutes_per_day=480.0,
            cost_per_use=80.0,
            department_ids=["operations", "sales", "customer-success"],
            actor_ids=["ae", "specialist"],
        ),
        SharedResource(
            resource_id="ai-platform",
            name="AI Automation Platform",
            resource_type=AI_AGENT,
            capacity_minutes_per_day=1440.0,
            cost_per_use=2.0,
            department_ids=["sales", "customer-success", "finance", "ai-transformation"],
            actor_ids=[
                "intake_agent", "research_agent", "proposal_agent",
                "validation_agent", "triage_agent", "response_agent",
            ],
        ),
        SharedResource(
            resource_id="crm-system",
            name="CRM System",
            resource_type=SOFTWARE_TOOL,
            capacity_minutes_per_day=2880.0,
            cost_per_use=0.5,
            department_ids=["sales", "customer-success"],
            actor_ids=["ae", "specialist"],
        ),
        SharedResource(
            resource_id="erp-system",
            name="ERP / Finance System",
            resource_type=SOFTWARE_TOOL,
            capacity_minutes_per_day=1440.0,
            cost_per_use=1.0,
            department_ids=["finance", "operations"],
            actor_ids=["ap_specialist"],
        ),
        SharedResource(
            resource_id="external-auditor",
            name="External Auditor",
            resource_type=EXTERNAL_VENDOR,
            capacity_minutes_per_day=60.0,
            cost_per_use=500.0,
            department_ids=["finance", "legal"],
            actor_ids=["support_reviewer", "ap_specialist"],
        ),
        SharedResource(
            resource_id="it-manager",
            name="IT Manager",
            resource_type=MANAGER,
            capacity_minutes_per_day=240.0,
            cost_per_use=100.0,
            department_ids=["operations", "ai-transformation"],
            actor_ids=[],
        ),
    ]
    for resource in resources:
        pool.add_resource(resource)

    return pool


__all__ = [
    "build_saas_org",
    "build_saas_org_budget",
    "build_saas_shared_resources",
]
