"""Scenario registry: central catalog of all simulation scenarios.

Every workflow example in this project — both the original three bundled
examples and the Phase 8 industry scenario library — is registered here as
a :class:`ScenarioDefinition`.  The registry is the single source of truth
for the CLI, case-study generator, and scenario-matrix command.

Scenarios are grouped into :data:`ScenarioCategory` constants.  Every
definition includes before/after workflow builders, three assumption profiles
(base, conservative, aggressive), a description of limitations, and
recommended CLI commands so users know how to get started.

All scenarios are illustrative, not benchmark-validated industry truths.
Durations, error rates, and costs are derived from publicly documented
best-practice estimates and representative process design patterns.  Users
**must** calibrate these values with their own operational data before
presenting results to stakeholders.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.workflow import Workflow

# ---------------------------------------------------------------------------
# Category constants
# ---------------------------------------------------------------------------

HEALTHCARE = "healthcare"
INSURANCE = "insurance"
HUMAN_RESOURCES = "human_resources"
PROCUREMENT = "procurement"
LEGAL = "legal"
INFORMATION_TECHNOLOGY = "information_technology"
FINANCE = "finance"
CUSTOMER_SUCCESS = "customer_success"
SALES = "sales"

SCENARIO_CATEGORIES = (
    HEALTHCARE,
    INSURANCE,
    HUMAN_RESOURCES,
    PROCUREMENT,
    LEGAL,
    INFORMATION_TECHNOLOGY,
    FINANCE,
    CUSTOMER_SUCCESS,
    SALES,
)

CATEGORY_LABELS: dict[str, str] = {
    HEALTHCARE: "Healthcare",
    INSURANCE: "Insurance",
    HUMAN_RESOURCES: "Human Resources",
    PROCUREMENT: "Procurement",
    LEGAL: "Legal",
    INFORMATION_TECHNOLOGY: "Information Technology",
    FINANCE: "Finance",
    CUSTOMER_SUCCESS: "Customer Success",
    SALES: "Sales",
}


# ---------------------------------------------------------------------------
# ScenarioDefinition
# ---------------------------------------------------------------------------


@dataclass
class ScenarioDefinition:
    """Metadata and builders for one simulation scenario.

    Attributes:
        name: Human-readable display name.
        slug: URL-safe identifier used in CLI commands and file names
            (lowercase, hyphen-separated).
        category: One of the :data:`SCENARIO_CATEGORIES` constants.
        description: One-sentence summary of what this scenario models.
        target_users: Who benefits most from running this scenario.
        before_builder: Callable with no arguments that returns the
            "before" (current-state) :class:`~b2b_workflow_simulator.workflow.Workflow`.
        after_builder: Callable that returns the "after" (AI-redesigned)
            workflow.
        default_assumption_profile: Standard-assumption profile for this
            scenario.
        conservative_assumption_profile: Higher AI error rates and costs;
            lower human cost efficiency.
        aggressive_assumption_profile: Lower AI costs and error rates;
            higher human cost efficiency.
        limitations: Bullet-point list of known limitations and caveats.
        recommended_commands: Example CLI commands to try first.
    """

    name: str
    slug: str
    category: str
    description: str
    target_users: str
    before_builder: Callable[[], Workflow]
    after_builder: Callable[[], Workflow]
    default_assumption_profile: AssumptionProfile
    conservative_assumption_profile: AssumptionProfile
    aggressive_assumption_profile: AssumptionProfile
    limitations: list[str] = field(default_factory=list)
    recommended_commands: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry builder (lazy-import to avoid circular deps at module load time)
# ---------------------------------------------------------------------------


def _build_registry() -> dict[str, ScenarioDefinition]:
    from b2b_workflow_simulator.examples import (
        customer_onboarding_implementation,
        customer_support_ticket_resolution,
        finance_month_end_close,
        healthcare_prior_authorization,
        hr_recruiting_screening,
        insurance_claims_intake,
        invoice_processing,
        it_support_triage,
        legal_contract_review,
        procurement_vendor_onboarding,
        sales_lead_qualification,
    )

    defs: list[ScenarioDefinition] = [
        # ---------------------------------------------------------------
        # Original bundled examples
        # ---------------------------------------------------------------
        ScenarioDefinition(
            name="Sales Lead Qualification",
            slug="sales-lead-qualification",
            category=SALES,
            description="Qualify inbound sales leads from intake through discovery call to handoff.",  # noqa: E501
            target_users="Sales ops leaders, revenue operations, CRO office",
            before_builder=sales_lead_qualification.build_before_workflow,
            after_builder=sales_lead_qualification.build_after_workflow,
            default_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=5000.0,
                description="Sales lead qualification - base assumptions",
            ),
            conservative_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=5000.0,
                ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.5,
                description="Sales lead qualification - conservative (higher AI error)",
            ),
            aggressive_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=5000.0,
                ai_cost_multiplier=0.6, human_hourly_cost_multiplier=0.9,
                description="Sales lead qualification - aggressive (lower AI cost)",
            ),
            limitations=[
                "Discovery call stage retained as human; AI quality cannot be modeled here.",
                "Disqualification rates depend on lead source not captured in the model.",
                "Assumes uniform lead quality; segment-specific models may differ.",
            ],
            recommended_commands=[
                "b2b-simulator executive-snapshot sales-lead-qualification --cases 300",
                "b2b-simulator roi-waterfall sales-lead-qualification --cases 300 --implementation-cost 5000",  # noqa: E501
            ],
        ),
        ScenarioDefinition(
            name="Invoice Processing",
            slug="invoice-processing",
            category=FINANCE,
            description="Accounts payable workflow from invoice intake through ERP entry and payment.",  # noqa: E501
            target_users="Finance controllers, AP managers, CFOs",
            before_builder=invoice_processing.build_before_workflow,
            after_builder=invoice_processing.build_after_workflow,
            default_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=8000.0,
                description="Invoice processing - base assumptions",
            ),
            conservative_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=8000.0,
                ai_error_rate_multiplier=2.0, ai_cost_multiplier=1.5,
                description="Invoice processing - conservative",
            ),
            aggressive_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=8000.0,
                ai_cost_multiplier=0.5, human_hourly_cost_multiplier=0.9,
                description="Invoice processing - aggressive",
            ),
            limitations=[
                "Three-way match complexity not fully modeled; exception rates may vary.",
                "ERP integration cost not included in implementation cost estimate.",
                "Approval delays depend on controller availability not captured here.",
            ],
            recommended_commands=[
                "b2b-simulator executive-snapshot invoice-processing --cases 300 --implementation-cost 8000",  # noqa: E501
                "b2b-simulator bottleneck-heatmap invoice-processing --cases 500 --arrival-interval 10",  # noqa: E501
            ],
        ),
        ScenarioDefinition(
            name="Customer Support Ticket Resolution",
            slug="customer-support-ticket-resolution",
            category=CUSTOMER_SUCCESS,
            description="Multi-tier support workflow from ticket triage through specialist resolution.",  # noqa: E501
            target_users="Customer success managers, support operations, VP of CX",
            before_builder=customer_support_ticket_resolution.build_before_workflow,
            after_builder=customer_support_ticket_resolution.build_after_workflow,
            default_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=6000.0,
                description="Customer support - base assumptions",
            ),
            conservative_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=6000.0,
                ai_error_rate_multiplier=2.5, ai_cost_multiplier=1.3,
                description="Customer support - conservative (AI bot errors high)",
            ),
            aggressive_assumption_profile=AssumptionProfile(
                num_cases=300, seed=42, implementation_cost=6000.0,
                ai_cost_multiplier=0.5, human_hourly_cost_multiplier=0.85,
                description="Customer support - aggressive",
            ),
            limitations=[
                "Customer sentiment and CSAT not modeled; AI deflection quality varies.",
                "Escalation rates depend on ticket complexity distribution.",
                "Language/localization overhead not included.",
            ],
            recommended_commands=[
                "b2b-simulator executive-snapshot customer-support-ticket-resolution --cases 300",
                "b2b-simulator consultant-packet customer-support-ticket-resolution --cases 300",
            ],
        ),
        # ---------------------------------------------------------------
        # Phase 8 industry scenarios
        # ---------------------------------------------------------------
        ScenarioDefinition(
            name="Healthcare Prior Authorization",
            slug="healthcare-prior-authorization",
            category=HEALTHCARE,
            description="Insurance prior-auth workflow from clinical submission through payer decision.",  # noqa: E501
            target_users="Health plan medical directors, utilization management teams, providers",
            before_builder=healthcare_prior_authorization.build_before_workflow,
            after_builder=healthcare_prior_authorization.build_after_workflow,
            default_assumption_profile=healthcare_prior_authorization.default_assumptions(),
            conservative_assumption_profile=healthcare_prior_authorization.conservative_assumptions(),
            aggressive_assumption_profile=healthcare_prior_authorization.aggressive_assumptions(),
            limitations=healthcare_prior_authorization.scenario_notes()["limitations"],
            recommended_commands=healthcare_prior_authorization.scenario_notes()["commands"],
        ),
        ScenarioDefinition(
            name="Insurance Claims Intake",
            slug="insurance-claims-intake",
            category=INSURANCE,
            description="Property/casualty claims workflow from first notice of loss through initial adjudication.",  # noqa: E501
            target_users="Claims operations managers, insurers, InsurTech teams",
            before_builder=insurance_claims_intake.build_before_workflow,
            after_builder=insurance_claims_intake.build_after_workflow,
            default_assumption_profile=insurance_claims_intake.default_assumptions(),
            conservative_assumption_profile=insurance_claims_intake.conservative_assumptions(),
            aggressive_assumption_profile=insurance_claims_intake.aggressive_assumptions(),
            limitations=insurance_claims_intake.scenario_notes()["limitations"],
            recommended_commands=insurance_claims_intake.scenario_notes()["commands"],
        ),
        ScenarioDefinition(
            name="HR Recruiting Screening",
            slug="hr-recruiting-screening",
            category=HUMAN_RESOURCES,
            description="Candidate screening pipeline from application receipt through interview scheduling.",  # noqa: E501
            target_users="HR directors, talent acquisition leads, CHROs",
            before_builder=hr_recruiting_screening.build_before_workflow,
            after_builder=hr_recruiting_screening.build_after_workflow,
            default_assumption_profile=hr_recruiting_screening.default_assumptions(),
            conservative_assumption_profile=hr_recruiting_screening.conservative_assumptions(),
            aggressive_assumption_profile=hr_recruiting_screening.aggressive_assumptions(),
            limitations=hr_recruiting_screening.scenario_notes()["limitations"],
            recommended_commands=hr_recruiting_screening.scenario_notes()["commands"],
        ),
        ScenarioDefinition(
            name="Procurement Vendor Onboarding",
            slug="procurement-vendor-onboarding",
            category=PROCUREMENT,
            description="Vendor onboarding from application through compliance check, risk scoring, and activation.",  # noqa: E501
            target_users="Procurement leaders, supply chain managers, CPOs",
            before_builder=procurement_vendor_onboarding.build_before_workflow,
            after_builder=procurement_vendor_onboarding.build_after_workflow,
            default_assumption_profile=procurement_vendor_onboarding.default_assumptions(),
            conservative_assumption_profile=procurement_vendor_onboarding.conservative_assumptions(),
            aggressive_assumption_profile=procurement_vendor_onboarding.aggressive_assumptions(),
            limitations=procurement_vendor_onboarding.scenario_notes()["limitations"],
            recommended_commands=procurement_vendor_onboarding.scenario_notes()["commands"],
        ),
        ScenarioDefinition(
            name="Legal Contract Review",
            slug="legal-contract-review",
            category=LEGAL,
            description="Contract review workflow from receipt through AI redlining, attorney review, and execution.",  # noqa: E501
            target_users="General counsel, legal ops teams, CLOs",
            before_builder=legal_contract_review.build_before_workflow,
            after_builder=legal_contract_review.build_after_workflow,
            default_assumption_profile=legal_contract_review.default_assumptions(),
            conservative_assumption_profile=legal_contract_review.conservative_assumptions(),
            aggressive_assumption_profile=legal_contract_review.aggressive_assumptions(),
            limitations=legal_contract_review.scenario_notes()["limitations"],
            recommended_commands=legal_contract_review.scenario_notes()["commands"],
        ),
        ScenarioDefinition(
            name="IT Support Triage",
            slug="it-support-triage",
            category=INFORMATION_TECHNOLOGY,
            description="Helpdesk incident workflow from intake triage through L1/L2/L3 resolution.",  # noqa: E501
            target_users="IT service managers, CIOs, ITSM platform teams",
            before_builder=it_support_triage.build_before_workflow,
            after_builder=it_support_triage.build_after_workflow,
            default_assumption_profile=it_support_triage.default_assumptions(),
            conservative_assumption_profile=it_support_triage.conservative_assumptions(),
            aggressive_assumption_profile=it_support_triage.aggressive_assumptions(),
            limitations=it_support_triage.scenario_notes()["limitations"],
            recommended_commands=it_support_triage.scenario_notes()["commands"],
        ),
        ScenarioDefinition(
            name="Finance Month-End Close",
            slug="finance-month-end-close",
            category=FINANCE,
            description="Month-end close workflow from data collection through reconciliation and reporting.",  # noqa: E501
            target_users="Controllers, CFOs, finance transformation leads",
            before_builder=finance_month_end_close.build_before_workflow,
            after_builder=finance_month_end_close.build_after_workflow,
            default_assumption_profile=finance_month_end_close.default_assumptions(),
            conservative_assumption_profile=finance_month_end_close.conservative_assumptions(),
            aggressive_assumption_profile=finance_month_end_close.aggressive_assumptions(),
            limitations=finance_month_end_close.scenario_notes()["limitations"],
            recommended_commands=finance_month_end_close.scenario_notes()["commands"],
        ),
        ScenarioDefinition(
            name="Customer Onboarding Implementation",
            slug="customer-onboarding-implementation",
            category=CUSTOMER_SUCCESS,
            description="B2B SaaS customer onboarding from signed contract through go-live.",
            target_users="Customer success leads, implementation managers, VPs of CS",
            before_builder=customer_onboarding_implementation.build_before_workflow,
            after_builder=customer_onboarding_implementation.build_after_workflow,
            default_assumption_profile=customer_onboarding_implementation.default_assumptions(),
            conservative_assumption_profile=customer_onboarding_implementation.conservative_assumptions(),
            aggressive_assumption_profile=customer_onboarding_implementation.aggressive_assumptions(),
            limitations=customer_onboarding_implementation.scenario_notes()["limitations"],
            recommended_commands=customer_onboarding_implementation.scenario_notes()["commands"],
        ),
    ]
    return {d.slug: d for d in defs}


_REGISTRY: dict[str, ScenarioDefinition] | None = None


def _registry() -> dict[str, ScenarioDefinition]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_scenario(slug: str) -> ScenarioDefinition:
    """Return the :class:`ScenarioDefinition` for ``slug``.

    Raises:
        KeyError: If no scenario with that slug is registered, with a
            helpful message listing known slugs.
    """
    reg = _registry()
    if slug not in reg:
        known = ", ".join(sorted(reg))
        raise KeyError(
            f"No scenario registered for slug {slug!r}. "
            f"Known slugs: {known}"
        )
    return reg[slug]


def list_scenarios() -> list[ScenarioDefinition]:
    """Return all registered scenarios, sorted by category then name."""
    return sorted(
        _registry().values(),
        key=lambda s: (s.category, s.name),
    )


def scenario_exists(slug: str) -> bool:
    """Return ``True`` if a scenario with ``slug`` is registered."""
    return slug in _registry()


def scenario_names() -> list[str]:
    """Return all registered slugs in sorted order."""
    return sorted(_registry())


def scenarios_by_category(category: str) -> list[ScenarioDefinition]:
    """Return all scenarios in ``category``, sorted by name."""
    return sorted(
        (s for s in _registry().values() if s.category == category),
        key=lambda s: s.name,
    )


__all__ = [
    "CATEGORY_LABELS",
    "CUSTOMER_SUCCESS",
    "FINANCE",
    "HEALTHCARE",
    "HUMAN_RESOURCES",
    "INFORMATION_TECHNOLOGY",
    "INSURANCE",
    "LEGAL",
    "PROCUREMENT",
    "SALES",
    "SCENARIO_CATEGORIES",
    "ScenarioDefinition",
    "get_scenario",
    "list_scenarios",
    "scenario_exists",
    "scenario_names",
    "scenarios_by_category",
]
