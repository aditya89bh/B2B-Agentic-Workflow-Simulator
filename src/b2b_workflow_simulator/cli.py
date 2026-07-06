"""Command-line interface for running bundled example simulations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from b2b_workflow_simulator.ai_adoption import assess_ai_adoption, generate_ai_adoption_report
from b2b_workflow_simulator.assumptions import (
    AssumptionProfile,
    apply_profile_to_workflow,
    load_assumption_profile,
)
from b2b_workflow_simulator.capacity_planning import (
    DEFAULT_OVERLOAD_THRESHOLD,
    DEFAULT_TARGET_UTILIZATION,
    DEFAULT_UNDERUTILIZATION_THRESHOLD,
    analyze_capacity,
    generate_capacity_report,
)
from b2b_workflow_simulator.case_studies import generate_all_case_studies, generate_case_study
from b2b_workflow_simulator.compliance import evaluate_compliance, generate_compliance_report
from b2b_workflow_simulator.cross_workflow import CrossWorkflowSimulator, WorkflowRunConfig
from b2b_workflow_simulator.examples import (
    customer_onboarding_implementation,
    customer_support_ticket_resolution,
    finance_month_end_close,
    governance,
    healthcare_prior_authorization,
    hr_recruiting_screening,
    insurance_claims_intake,
    invoice_processing,
    it_support_triage,
    legal_contract_review,
    procurement_vendor_onboarding,
    sales_lead_qualification,
)
from b2b_workflow_simulator.examples.saas_org import (
    build_saas_org,
    build_saas_org_budget,
    build_saas_shared_resources,
)
from b2b_workflow_simulator.executive_report import (
    build_executive_assessment,
    generate_executive_report,
)
from b2b_workflow_simulator.export import diff_to_csv, diff_to_json, events_to_json, kpi_to_json
from b2b_workflow_simulator.growth import GrowthConfig, generate_growth_report, project_growth
from b2b_workflow_simulator.heatmap import build_bottleneck_heatmap, heatmap_to_svg, heatmap_to_text
from b2b_workflow_simulator.html_report import (
    render_ai_adoption_html,
    render_capacity_html,
    render_compliance_html,
    render_diff_html,
    render_executive_html,
    render_monte_carlo_comparison_html,
    render_org_budget_html,
    render_org_executive_html,
    render_org_growth_html,
    render_org_health_html,
    render_policy_html,
    render_portfolio_html,
    render_recommendation_html,
    render_risk_html,
    render_sensitivity_grid_html,
)
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.monte_carlo import (
    generate_monte_carlo_comparison_report,
    run_monte_carlo_comparison,
)
from b2b_workflow_simulator.org_health import compute_org_health, generate_org_health_report
from b2b_workflow_simulator.org_report import OrgDigitalTwinReport, generate_org_digital_twin_report
from b2b_workflow_simulator.packet import generate_packet
from b2b_workflow_simulator.policy import evaluate_policies, generate_policy_report
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.portfolio import RANK_BY_OPTIONS, WorkflowPortfolio
from b2b_workflow_simulator.recommendation import (
    generate_recommendation_report,
    generate_recommendations,
)
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.report import generate_portfolio_report, generate_report
from b2b_workflow_simulator.restructuring import (
    SCENARIO_TYPES,
    RestructuringScenario,
    compare_restructuring_scenarios,
    generate_restructuring_report,
)
from b2b_workflow_simulator.risk import compute_risk, generate_risk_report
from b2b_workflow_simulator.scenario_matrix import (
    build_scenario_matrix,
    matrix_to_json,
    matrix_to_text,
)
from b2b_workflow_simulator.scenarios import (
    CATEGORY_LABELS,
    SCENARIO_CATEGORIES,
    list_scenarios,
    scenario_exists,
    scenarios_by_category,
)
from b2b_workflow_simulator.sensitivity import (
    PARAMETERS,
    format_sensitivity_table,
    run_sensitivity_sweep,
)
from b2b_workflow_simulator.sensitivity_grid import (
    generate_sensitivity_grid_report,
    run_sensitivity_grid,
)
from b2b_workflow_simulator.shared_resources import RESOURCE_TYPE_LABELS
from b2b_workflow_simulator.simulation import ENGINES, SimulationRunner
from b2b_workflow_simulator.sla import evaluate_sla
from b2b_workflow_simulator.snapshot import build_snapshot, snapshot_to_html, snapshot_to_text
from b2b_workflow_simulator.visualization import compare_mermaid, compare_text, to_mermaid, to_text
from b2b_workflow_simulator.waterfall import (
    build_roi_waterfall,
    waterfall_to_svg,
    waterfall_to_text,
)
from b2b_workflow_simulator.workflow_io import load_workflow, save_workflow

EXPORT_FORMATS = ("json", "csv")

EXAMPLES = {
    "sales-lead-qualification": (
        sales_lead_qualification.build_before_workflow,
        sales_lead_qualification.build_after_workflow,
    ),
    "invoice-processing": (
        invoice_processing.build_before_workflow,
        invoice_processing.build_after_workflow,
    ),
    "customer-support-ticket-resolution": (
        customer_support_ticket_resolution.build_before_workflow,
        customer_support_ticket_resolution.build_after_workflow,
    ),
    # Phase 8: Industry scenario library
    "healthcare-prior-authorization": (
        healthcare_prior_authorization.build_before_workflow,
        healthcare_prior_authorization.build_after_workflow,
    ),
    "insurance-claims-intake": (
        insurance_claims_intake.build_before_workflow,
        insurance_claims_intake.build_after_workflow,
    ),
    "hr-recruiting-screening": (
        hr_recruiting_screening.build_before_workflow,
        hr_recruiting_screening.build_after_workflow,
    ),
    "procurement-vendor-onboarding": (
        procurement_vendor_onboarding.build_before_workflow,
        procurement_vendor_onboarding.build_after_workflow,
    ),
    "legal-contract-review": (
        legal_contract_review.build_before_workflow,
        legal_contract_review.build_after_workflow,
    ),
    "it-support-triage": (
        it_support_triage.build_before_workflow,
        it_support_triage.build_after_workflow,
    ),
    "finance-month-end-close": (
        finance_month_end_close.build_before_workflow,
        finance_month_end_close.build_after_workflow,
    ),
    "customer-onboarding-implementation": (
        customer_onboarding_implementation.build_before_workflow,
        customer_onboarding_implementation.build_after_workflow,
    ),
}

GOVERNANCE = {
    "sales-lead-qualification": (
        governance.sales_lead_qualification_policies,
        governance.sales_lead_qualification_compliance_requirements,
        governance.sales_lead_qualification_slas,
    ),
    "invoice-processing": (
        governance.invoice_processing_policies,
        governance.invoice_processing_compliance_requirements,
        governance.invoice_processing_slas,
    ),
    "customer-support-ticket-resolution": (
        governance.customer_support_policies,
        governance.customer_support_compliance_requirements,
        governance.customer_support_slas,
    ),
}


def _print_kpi_table(before: KPIResult, after: KPIResult) -> None:
    rows = [
        ("Cases simulated", f"{before.total_cases}", f"{after.total_cases}"),
        ("Completed", f"{before.completed_cases}", f"{after.completed_cases}"),
        ("Failed", f"{before.failed_cases}", f"{after.failed_cases}"),
        (
            "Completion rate",
            f"{before.completion_rate:.1%}",
            f"{after.completion_rate:.1%}",
        ),
        ("Total cost", f"${before.total_cost:,.2f}", f"${after.total_cost:,.2f}"),
        (
            "Avg cost / case",
            f"${before.avg_cost_per_case:,.2f}",
            f"${after.avg_cost_per_case:,.2f}",
        ),
        (
            "Avg cycle time (min)",
            f"{before.avg_cycle_time_minutes:,.1f}",
            f"{after.avg_cycle_time_minutes:,.1f}",
        ),
    ]

    label_width = max(len(row[0]) for row in rows)
    col_width = max(max(len(row[1]), len(row[2])) for row in rows)
    header = f"{'Metric':<{label_width}}  {'Before':>{col_width}}  {'After':>{col_width}}"
    print(header)
    print("-" * len(header))
    for label, before_value, after_value in rows:
        print(f"{label:<{label_width}}  {before_value:>{col_width}}  {after_value:>{col_width}}")


def _run_before_after(
    example_name: str,
    num_cases: int,
    seed: int | None,
    arrival_interval_minutes: float | None = None,
    engine: str = "simple",
    collect_events: bool = True,
):
    """Build and simulate both variants of a bundled example.

    Returns a `(before_workflow, after_workflow, before_result, after_result)`
    tuple, or `None` (after printing an error) if `example_name` is unknown.
    """
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return None

    build_before, build_after = EXAMPLES[example_name]
    before_workflow = build_before()
    after_workflow = build_after()

    before_result = SimulationRunner(seed=seed).run(
        before_workflow, num_cases,
        arrival_interval_minutes=arrival_interval_minutes,
        engine=engine,
        collect_events=collect_events,
    )
    after_result = SimulationRunner(seed=seed).run(
        after_workflow, num_cases,
        arrival_interval_minutes=arrival_interval_minutes,
        engine=engine,
        collect_events=collect_events,
    )
    return before_workflow, after_workflow, before_result, after_result


def _build_portfolio(
    example_names: list[str],
    num_cases: int,
    seed: int | None,
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
) -> WorkflowPortfolio | None:
    """Build a `WorkflowPortfolio` from a list of bundled example names.

    Returns `None` (after printing an error) if any name is unknown.
    """
    unknown = [name for name in example_names if name not in EXAMPLES]
    if unknown:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example(s): {', '.join(unknown)}. Available: {available}", file=sys.stderr)
        return None

    portfolio = WorkflowPortfolio(name="Portfolio")
    for name in example_names:
        outcome = _run_before_after(name, num_cases, seed, arrival_interval_minutes)
        if outcome is None:
            return None
        _before_workflow, _after_workflow, before_result, after_result = outcome
        portfolio.add_entry(name, before_result.kpi, after_result.kpi, implementation_cost)
    return portfolio


def run_portfolio(
    example_names: list[str],
    num_cases: int,
    seed: int | None,
) -> int:
    """Run several bundled examples and print a condensed per-workflow KPI summary."""
    portfolio = _build_portfolio(example_names, num_cases, seed, None, None)
    if portfolio is None:
        return 1

    print(f"Portfolio: {', '.join(example_names)}")
    print(f"Cases per workflow: {num_cases}")
    print()
    rows = [
        (
            entry.name,
            f"${entry.diff.total_cost.before:,.2f}",
            f"${entry.diff.total_cost.after:,.2f}",
            f"{entry.diff.roi.roi_percentage:+.1f}%"
            if entry.diff.roi.roi_percentage is not None
            else "n/a",
        )
        for entry in portfolio.entries
    ]
    label_width = max(len(row[0]) for row in rows)
    col_width = max(max(len(row[1]), len(row[2]), len(row[3])) for row in rows)
    header = (
        f"{'Workflow':<{label_width}}  {'Before Cost':>{col_width}}  "
        f"{'After Cost':>{col_width}}  {'ROI':>{col_width}}"
    )
    print(header)
    print("-" * len(header))
    for name, before_cost, after_cost, roi in rows:
        print(
            f"{name:<{label_width}}  {before_cost:>{col_width}}  "
            f"{after_cost:>{col_width}}  {roi:>{col_width}}"
        )
    return 0


def run_example(example_name: str, num_cases: int, seed: int | None, engine: str = "simple") -> int:
    """Run the before/after variants of a bundled example and print a KPI comparison."""
    outcome = _run_before_after(example_name, num_cases, seed, engine=engine)
    if outcome is None:
        return 1
    before_workflow, after_workflow, before_result, after_result = outcome

    print(f"Example: {example_name}")
    print(f"Cases per variant: {num_cases}")
    print(f"Engine: {engine}")
    print()
    print(f"Before: {before_workflow.name}")
    print(f"After:  {after_workflow.name}")
    print()
    _print_kpi_table(before_result.kpi, after_result.kpi)
    return 0


def compare_portfolio(
    example_names: list[str],
    num_cases: int,
    seed: int | None,
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
    rank_by: str,
    html_output: str | None,
) -> int:
    """Run several bundled examples and print a full portfolio report."""
    portfolio = _build_portfolio(
        example_names, num_cases, seed, implementation_cost, arrival_interval_minutes
    )
    if portfolio is None:
        return 1

    print(generate_portfolio_report(portfolio, rank_by=rank_by))

    if html_output:
        Path(html_output).write_text(render_portfolio_html(portfolio, rank_by=rank_by))
        print(f"\nHTML report written to {html_output}")
    return 0


def compare_example(
    example_name: str,
    num_cases: int | None,
    seed: int | None,
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
    engine: str | None = None,
    assumptions_path: str | None = None,
) -> int:
    """Run both variants of a bundled example and print a full ROI report."""
    profile = _load_profile(assumptions_path)
    effective_cases = num_cases if num_cases is not None else profile.num_cases
    effective_seed = seed if seed is not None else profile.seed
    effective_impl = (
        implementation_cost if implementation_cost is not None
        else profile.implementation_cost
    )
    effective_interval = (
        arrival_interval_minutes if arrival_interval_minutes is not None
        else profile.arrival_interval_minutes
    )
    effective_engine = engine if engine is not None else profile.engine
    run_profile = AssumptionProfile(
        num_cases=effective_cases,
        seed=effective_seed,
        implementation_cost=effective_impl,
        arrival_interval_minutes=effective_interval,
        engine=effective_engine,
        ai_error_rate_multiplier=profile.ai_error_rate_multiplier,
        ai_cost_multiplier=profile.ai_cost_multiplier,
        human_hourly_cost_multiplier=profile.human_hourly_cost_multiplier,
        collect_events=False,
    )
    outcome = _run_before_after_with_profile(
        example_name, run_profile,
        arrival_interval_minutes=effective_interval,
        engine=effective_engine,
    )
    if outcome is None:
        return 1
    _before_workflow, _after_workflow, before_result, after_result = outcome

    diff = compare_workflows(before_result.kpi, after_result.kpi, effective_impl)
    print(generate_report(diff))
    return 0


def html_report_example(
    example_name: str,
    num_cases: int,
    seed: int | None,
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
    output_path: str,
) -> int:
    """Run both variants of a bundled example and write a static HTML redesign report."""
    outcome = _run_before_after(example_name, num_cases, seed, arrival_interval_minutes)
    if outcome is None:
        return 1
    _before_workflow, _after_workflow, before_result, after_result = outcome

    diff = compare_workflows(before_result.kpi, after_result.kpi, implementation_cost)
    Path(output_path).write_text(render_diff_html(diff))
    print(f"HTML report written to {output_path}")
    return 0


def sensitivity_example(
    example_name: str,
    parameter: str,
    values: list[float],
    num_cases: int,
    seed: int | None,
    implementation_cost: float | None,
) -> int:
    """Run a sensitivity sweep for a bundled example and print the resulting table."""
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return 1

    build_before, build_after = EXAMPLES[example_name]
    result = run_sensitivity_sweep(
        build_before,
        build_after,
        parameter,
        values,
        num_cases,
        seed=seed,
        implementation_cost=implementation_cost,
    )
    print(f"Example: {example_name}")
    print()
    print(format_sensitivity_table(result))
    return 0


def _parse_int_list(raw: str) -> list[int]:
    try:
        return [int(part) for part in raw.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected a comma-separated list of integers, got {raw!r}"
        ) from exc


def monte_carlo_example(
    example_name: str,
    num_cases: int,
    seeds: list[int],
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
    engine: str,
    html_output: str | None,
) -> int:
    """Run a Monte Carlo comparison for a bundled example across many seeds."""
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return 1

    build_before, build_after = EXAMPLES[example_name]
    result = run_monte_carlo_comparison(
        build_before,
        build_after,
        num_cases,
        seeds,
        arrival_interval_minutes=arrival_interval_minutes,
        implementation_cost=implementation_cost,
        engine=engine,
    )
    print(f"Example: {example_name}")
    print(f"Seeds: {len(seeds)}")
    print()
    print(generate_monte_carlo_comparison_report(result))

    if html_output:
        Path(html_output).write_text(render_monte_carlo_comparison_html(result))
        print(f"\nHTML report written to {html_output}")
    return 0


def monte_carlo_portfolio(
    example_names: list[str],
    num_cases: int,
    seeds: list[int],
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
) -> int:
    """Run a Monte Carlo comparison for several bundled examples and summarize each."""
    unknown = [name for name in example_names if name not in EXAMPLES]
    if unknown:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example(s): {', '.join(unknown)}. Available: {available}", file=sys.stderr)
        return 1

    print(f"Portfolio: {', '.join(example_names)}")
    print(f"Cases per run: {num_cases}, Seeds: {len(seeds)}")
    print()
    rows = []
    for name in example_names:
        build_before, build_after = EXAMPLES[name]
        result = run_monte_carlo_comparison(
            build_before,
            build_after,
            num_cases,
            seeds,
            arrival_interval_minutes=arrival_interval_minutes,
            implementation_cost=implementation_cost,
        )
        roi = result.metric_stats["roi_percentage"]
        savings = result.metric_stats["total_cost_savings"]
        roi_str = f"{roi.mean:+.1f}%" if roi.sample_count else "n/a"
        rows.append((name, f"${savings.mean:,.2f}", roi_str))

    label_width = max(len(row[0]) for row in rows)
    col_width = max(max(len(row[1]), len(row[2])) for row in rows)
    header = (
        f"{'Workflow':<{label_width}}  {'Mean Savings':>{col_width}}  {'Mean ROI':>{col_width}}"
    )
    print(header)
    print("-" * len(header))
    for name, savings, roi in rows:
        print(f"{name:<{label_width}}  {savings:>{col_width}}  {roi:>{col_width}}")
    return 0


def sensitivity_grid_example(
    example_name: str,
    x_parameter: str,
    x_values: list[float],
    y_parameter: str,
    y_values: list[float],
    num_cases: int,
    seed: int | None,
    implementation_cost: float | None,
    html_output: str | None,
) -> int:
    """Run a two-parameter sensitivity grid for a bundled example and print the ROI matrix."""
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return 1

    build_before, build_after = EXAMPLES[example_name]
    result = run_sensitivity_grid(
        build_before,
        build_after,
        x_parameter,
        x_values,
        y_parameter,
        y_values,
        num_cases,
        seed=seed,
        implementation_cost=implementation_cost,
    )
    print(f"Example: {example_name}")
    print()
    print(generate_sensitivity_grid_report(result))

    if html_output:
        Path(html_output).write_text(render_sensitivity_grid_html(result))
        print(f"\nHTML report written to {html_output}")
    return 0


def capacity_analysis(
    example_name: str,
    variant: str,
    num_cases: int,
    seed: int | None,
    arrival_interval_minutes: float | None,
    target_utilization: float,
    overload_threshold: float,
    underutilization_threshold: float,
    html_output: str | None,
) -> int:
    """Run one variant of a bundled example and print a capacity/staffing report."""
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return 1

    build_before, build_after = EXAMPLES[example_name]
    workflow = build_before() if variant == "before" else build_after()
    result = SimulationRunner(seed=seed).run(
        workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
    )
    pool_sizes = {
        actor.actor_id: len(actor.workers)
        for actor in workflow.actors.values()
        if isinstance(actor, ActorPool)
    }
    plan = analyze_capacity(
        result.kpi,
        pool_sizes=pool_sizes,
        target_utilization=target_utilization,
        overload_threshold=overload_threshold,
        underutilization_threshold=underutilization_threshold,
    )
    print(f"Example: {example_name} ({variant})")
    print()
    print(generate_capacity_report(plan))

    if html_output:
        Path(html_output).write_text(render_capacity_html(plan))
        print(f"\nHTML report written to {html_output}")
    return 0


def team_utilization(
    example_name: str,
    variant: str,
    num_cases: int,
    seed: int | None,
    arrival_interval_minutes: float | None,
) -> int:
    """Run one variant of a bundled example and print raw actor/pool/worker utilization."""
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return 1

    build_before, build_after = EXAMPLES[example_name]
    workflow = build_before() if variant == "before" else build_after()
    result = SimulationRunner(seed=seed).run(
        workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
    )
    kpi = result.kpi

    print(f"Example: {example_name} ({variant})")
    print()
    if not kpi.actor_utilization and not kpi.pool_utilization:
        print("No capacity data available. Pass --arrival-interval to enable queueing.")
        return 0

    if kpi.actor_utilization:
        print("Actor utilization:")
        for actor_id, utilization in sorted(kpi.actor_utilization.items()):
            print(f"  - {actor_id}: {utilization:.1%}")
    if kpi.pool_utilization:
        print("Pool utilization:")
        for pool_id, utilization in sorted(kpi.pool_utilization.items()):
            print(f"  - {pool_id}: {utilization:.1%}")
            for worker_id, worker_util in sorted(kpi.worker_utilization.get(pool_id, {}).items()):
                print(f"      - {worker_id}: {worker_util:.1%}")
    return 0


def _select_variant(example_name: str, variant: str):
    """Build one variant ("before" or "after") of a bundled example.

    Returns `None` (after printing an error) if `example_name` is unknown.
    """
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return None
    build_before, build_after = EXAMPLES[example_name]
    return build_before() if variant == "before" else build_after()


def policy_analysis(example_name: str, variant: str, html_output: str | None) -> int:
    """Evaluate a bundled example's attached policies and print a governance report."""
    workflow = _select_variant(example_name, variant)
    if workflow is None:
        return 1

    policies_fn, _, _ = GOVERNANCE.get(example_name, (None, None, None))
    policies = policies_fn() if policies_fn else []
    evaluation = evaluate_policies(workflow, policies)

    print(f"Example: {example_name} ({variant})")
    print()
    print(generate_policy_report(evaluation))

    if html_output:
        Path(html_output).write_text(render_policy_html(evaluation))
        print(f"\nHTML report written to {html_output}")
    return 0


def compliance_analysis(example_name: str, variant: str, html_output: str | None) -> int:
    """Evaluate a bundled example's compliance requirements and print a report."""
    workflow = _select_variant(example_name, variant)
    if workflow is None:
        return 1

    _, compliance_fn, _ = GOVERNANCE.get(example_name, (None, None, None))
    requirements = compliance_fn() if compliance_fn else []
    report = evaluate_compliance(workflow, requirements)

    print(f"Example: {example_name} ({variant})")
    print()
    print(generate_compliance_report(report))

    if html_output:
        Path(html_output).write_text(render_compliance_html(report))
        print(f"\nHTML report written to {html_output}")
    return 0


def risk_analysis(
    example_name: str,
    variant: str,
    num_cases: int,
    seed: int | None,
    arrival_interval_minutes: float | None,
    html_output: str | None,
) -> int:
    """Simulate a bundled example variant and print an organizational risk assessment."""
    workflow = _select_variant(example_name, variant)
    if workflow is None:
        return 1

    result = SimulationRunner(seed=seed).run(
        workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
    )
    policies_fn, compliance_fn, _ = GOVERNANCE.get(example_name, (None, None, None))
    policy_evaluation = evaluate_policies(workflow, policies_fn()) if policies_fn else None
    compliance_report = evaluate_compliance(workflow, compliance_fn()) if compliance_fn else None
    assessment = compute_risk(workflow, result.kpi, policy_evaluation, compliance_report)

    print(f"Example: {example_name} ({variant})")
    print()
    print(generate_risk_report(assessment))

    if html_output:
        Path(html_output).write_text(render_risk_html(assessment))
        print(f"\nHTML report written to {html_output}")
    return 0


def readiness_analysis(
    example_name: str,
    variant: str,
    num_cases: int,
    seed: int | None,
    html_output: str | None,
) -> int:
    """Simulate a bundled example variant and print an AI adoption readiness assessment."""
    workflow = _select_variant(example_name, variant)
    if workflow is None:
        return 1

    result = SimulationRunner(seed=seed).run(workflow, num_cases)
    policies_fn, _, _ = GOVERNANCE.get(example_name, (None, None, None))
    policy_evaluation = evaluate_policies(workflow, policies_fn()) if policies_fn else None
    assessment = assess_ai_adoption(workflow, result.kpi, policy_evaluation)

    print(f"Example: {example_name} ({variant})")
    print()
    print(generate_ai_adoption_report(assessment))

    if html_output:
        Path(html_output).write_text(render_ai_adoption_html(assessment))
        print(f"\nHTML report written to {html_output}")
    return 0


def recommend_redesign(
    example_name: str,
    variant: str,
    num_cases: int,
    seed: int | None,
    html_output: str | None,
) -> int:
    """Simulate a bundled example variant and print actionable redesign recommendations."""
    workflow = _select_variant(example_name, variant)
    if workflow is None:
        return 1

    result = SimulationRunner(seed=seed).run(workflow, num_cases)
    policies_fn, compliance_fn, _ = GOVERNANCE.get(example_name, (None, None, None))
    policy_evaluation = evaluate_policies(workflow, policies_fn()) if policies_fn else None
    compliance_report = evaluate_compliance(workflow, compliance_fn()) if compliance_fn else None
    risk_assessment = compute_risk(workflow, result.kpi, policy_evaluation, compliance_report)
    recommendations = generate_recommendations(workflow, result.kpi, risk_assessment)

    print(f"Example: {example_name} ({variant})")
    print()
    print(generate_recommendation_report(recommendations))

    if html_output:
        Path(html_output).write_text(render_recommendation_html(recommendations))
        print(f"\nHTML report written to {html_output}")
    return 0


def executive_report(
    example_name: str,
    num_cases: int,
    seed: int | None,
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
    html_output: str | None,
) -> int:
    """Run both variants of a bundled example and print a full executive assessment report.

    The report evaluates the "after" (redesigned) workflow, using the
    "before" workflow only to compute the ROI section.
    """
    outcome = _run_before_after(example_name, num_cases, seed, arrival_interval_minutes)
    if outcome is None:
        return 1
    _before_workflow, after_workflow, before_result, after_result = outcome

    diff = compare_workflows(before_result.kpi, after_result.kpi, implementation_cost)
    policies_fn, compliance_fn, sla_fn = GOVERNANCE.get(example_name, (None, None, None))
    policy_evaluation = evaluate_policies(after_workflow, policies_fn()) if policies_fn else None
    compliance_report = (
        evaluate_compliance(after_workflow, compliance_fn()) if compliance_fn else None
    )
    sla_report = evaluate_sla(after_result, sla_fn()) if sla_fn else None

    assessment = build_executive_assessment(
        after_workflow,
        after_result.kpi,
        redesign_diff=diff,
        policy_evaluation=policy_evaluation,
        compliance_report=compliance_report,
        sla_report=sla_report,
    )

    print(generate_executive_report(assessment))

    if html_output:
        Path(html_output).write_text(render_executive_html(assessment))
        print(f"\nHTML report written to {html_output}")
    return 0


def export_example(
    example_name: str,
    num_cases: int,
    seed: int | None,
    export_format: str,
    output_dir: str,
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
) -> int:
    """Run both variants of a bundled example and export results to disk."""
    outcome = _run_before_after(example_name, num_cases, seed, arrival_interval_minutes)
    if outcome is None:
        return 1
    _before_workflow, _after_workflow, before_result, after_result = outcome

    diff = compare_workflows(before_result.kpi, after_result.kpi, implementation_cost)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    if export_format == "json":
        files = {
            f"{example_name}-before-events.json": events_to_json(before_result.events),
            f"{example_name}-after-events.json": events_to_json(after_result.events),
            f"{example_name}-before-kpi.json": kpi_to_json(before_result.kpi),
            f"{example_name}-after-kpi.json": kpi_to_json(after_result.kpi),
            f"{example_name}-comparison.json": diff_to_json(diff),
        }
    else:
        files = {f"{example_name}-comparison.csv": diff_to_csv(diff)}

    print(f"Exported {len(files)} file(s) to {destination}/:")
    for filename, content in files.items():
        file_path = destination / filename
        file_path.write_text(content)
        print(f"  - {file_path}")
    return 0


def _parse_float_list(raw: str) -> list[float]:
    try:
        return [float(part) for part in raw.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected a comma-separated list of numbers, got {raw!r}"
        ) from exc


def save_example(example_name: str, output_dir: str) -> int:
    """Save the before/after workflow definitions of a bundled example as JSON files."""
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available: {available}", file=sys.stderr)
        return 1

    build_before, build_after = EXAMPLES[example_name]
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    files = {
        f"{example_name}-before.json": build_before(),
        f"{example_name}-after.json": build_after(),
    }
    for filename, workflow in files.items():
        file_path = destination / filename
        save_workflow(workflow, file_path)
        print(f"  - {file_path}")
    print(f"Saved {len(files)} workflow definition(s) to {destination}/:")
    return 0


def load_example(path: str, num_cases: int, seed: int | None) -> int:
    """Load a workflow definition from JSON and print its simulated KPI summary."""
    try:
        workflow = load_workflow(path)
    except (OSError, ValueError) as exc:
        print(f"Failed to load workflow from '{path}': {exc}", file=sys.stderr)
        return 1

    result = SimulationRunner(seed=seed).run(workflow, num_cases)
    kpi = result.kpi

    print(f"Loaded workflow: {workflow.name}")
    print(f"Cases simulated: {num_cases}")
    print()
    print(f"Completed:          {kpi.completed_cases}")
    print(f"Failed:             {kpi.failed_cases}")
    print(f"Completion rate:    {kpi.completion_rate:.1%}")
    print(f"Total cost:         ${kpi.total_cost:,.2f}")
    print(f"Avg cost / case:    ${kpi.avg_cost_per_case:,.2f}")
    print(f"Avg cycle time:     {kpi.avg_cycle_time_minutes:,.1f} minutes")
    return 0


def _build_saas_cross_workflow_result(
    num_cases: int,
    seed: int | None,
    arrival_interval: float | None,
) -> tuple:
    """Build and run the bundled SaaS org cross-workflow simulation.

    Returns a ``(Organization, CrossWorkflowResult, SharedResourcePool)``
    tuple.  The shared resource pool has contention usage already recorded
    from the simulation run.
    """
    org = build_saas_org()
    pool = build_saas_shared_resources()
    sim = CrossWorkflowSimulator(org, seed=seed, shared_resource_pool=pool)
    sim.add_workflow(
        WorkflowRunConfig(
            workflow=sales_lead_qualification.build_after_workflow(),
            num_cases=num_cases,
            arrival_interval_minutes=arrival_interval,
            dept_id="sales",
        )
    )
    sim.add_workflow(
        WorkflowRunConfig(
            workflow=invoice_processing.build_after_workflow(),
            num_cases=num_cases,
            arrival_interval_minutes=arrival_interval,
            dept_id="finance",
        )
    )
    sim.add_workflow(
        WorkflowRunConfig(
            workflow=customer_support_ticket_resolution.build_after_workflow(),
            num_cases=num_cases,
            arrival_interval_minutes=arrival_interval,
            dept_id="customer-success",
        )
    )
    result = sim.run()
    return org, result, pool


def run_org(num_cases: int, seed: int | None, arrival_interval: float | None) -> int:
    """Run the bundled B2B SaaS organizational simulation and print a KPI summary."""
    org, result, pool = _build_saas_cross_workflow_result(num_cases, seed, arrival_interval)
    print(f"Organization: {org.name}")
    print(f"Cases per workflow: {num_cases}")
    print(f"Total workflows: {len(result.workflow_ids)}")
    print(f"Total cases simulated: {result.total_cases}")
    print(f"Total cost: ${result.total_cost:,.2f}")
    print(f"Avg completion rate: {result.avg_completion_rate:.1%}")
    print()
    label_w = max(len(wf_id) for wf_id in result.workflow_ids)
    print(f"{'Workflow':<{label_w}}  {'Completion':>12}  {'Cost/Case':>12}  {'Cycle (min)':>12}")
    print("-" * (label_w + 42))
    for wf_id in result.workflow_ids:
        kpi = result.kpi_for(wf_id)
        print(
            f"{wf_id:<{label_w}}  {kpi.completion_rate:>12.1%}  "
            f"${kpi.avg_cost_per_case:>11,.2f}  {kpi.avg_cycle_time_minutes:>12,.1f}"
        )
    return 0


def org_health(num_cases: int, seed: int | None, html_output: str | None) -> int:
    """Compute and display the organizational health score for the bundled SaaS org."""
    org, result, pool = _build_saas_cross_workflow_result(num_cases, seed, None)
    org_budget = build_saas_org_budget()
    kpi_results = {wf_id: result.kpi_for(wf_id) for wf_id in result.workflow_ids}
    health_score = compute_org_health(org, org_budget, pool, kpi_results)
    print(generate_org_health_report(health_score))
    if html_output:
        Path(html_output).write_text(render_org_health_html(health_score))
        print(f"\nHTML report written to {html_output}")
    return 0


def org_budget_analysis(html_output: str | None) -> int:
    """Print the budget analysis for the bundled B2B SaaS organization."""
    org = build_saas_org()
    org_budget = build_saas_org_budget()
    print(f"Organization: {org.name}")
    print(f"Total annual budget: ${org_budget.total_budget:,.0f}")
    print(f"Overall utilization: {org_budget.overall_utilization:.1%}")
    print()
    print(f"{'Department':<30}  {'Budget':>12}  {'Spent':>12}  {'Util':>8}  {'Status':>8}")
    print("-" * 76)
    for dept_id, budget in org_budget.dept_budgets.items():
        try:
            dept_name = org.get_department(dept_id).name
        except KeyError:
            dept_name = dept_id
        status = "OVERRUN" if budget.has_overrun else "OK"
        print(
            f"{dept_name:<30}  ${budget.annual_budget:>11,.0f}  "
            f"${budget.total_spent:>11,.0f}  {budget.utilization:>7.1%}  {status:>8}"
        )
    if html_output:
        Path(html_output).write_text(render_org_budget_html(org, org_budget))
        print(f"\nHTML report written to {html_output}")
    return 0


def org_resource_contention(
    days: int, num_cases: int, seed: int | None, html_output: str | None
) -> int:
    """Print shared resource contention analysis for the bundled SaaS org."""
    org, result, pool = _build_saas_cross_workflow_result(num_cases, seed, None)
    contentions = pool.all_contentions(days=days)
    print(f"Organization: {org.name}")
    print(f"Cases simulated per workflow: {num_cases}")
    print(f"Reference period: {days} day(s)")
    print()
    if not contentions:
        print("No shared resources registered.")
        return 0
    print(f"{'Resource':<32}  {'Type':<18}  {'Ratio':>8}  {'Risk':>10}")
    print("-" * 74)
    for c in contentions:
        res = pool.resource(c.resource_id)
        type_label = RESOURCE_TYPE_LABELS.get(res.resource_type, res.resource_type)
        print(
            f"{c.resource_name:<32}  {type_label:<18}  "
            f"{c.contention_ratio:>8.2f}  {c.overload_risk.upper():>10}"
        )
    bottlenecks = pool.bottleneck_resources(days=days)
    if bottlenecks:
        print(f"\n{len(bottlenecks)} bottleneck resource(s) detected (demand > capacity).")
    if html_output:
        from b2b_workflow_simulator.html_report import render_org_executive_html
        from b2b_workflow_simulator.org_report import OrgDigitalTwinReport
        report = OrgDigitalTwinReport(org=org, shared_resources=pool)
        Path(html_output).write_text(render_org_executive_html(report))
        print(f"\nHTML report written to {html_output}")
    return 0


def org_growth_projection(
    monthly_growth_rate: float,
    base_cases: int,
    base_headcount: int,
    headcount_growth: float,
    ai_adoption_rate: float,
    html_output: str | None,
) -> int:
    """Project 12-month growth for the bundled B2B SaaS organization."""
    org = build_saas_org()
    org_budget = build_saas_org_budget()
    config = GrowthConfig(
        monthly_growth_rate=monthly_growth_rate,
        base_cases_per_month=base_cases,
        base_headcount=base_headcount,
        headcount_growth_rate=headcount_growth,
        ai_adoption_increase_rate=ai_adoption_rate,
    )
    projection = project_growth(org, org_budget, config)
    print(generate_growth_report(projection))
    if html_output:
        Path(html_output).write_text(render_org_growth_html(projection))
        print(f"\nHTML report written to {html_output}")
    return 0


def org_restructure_scenario(scenario_type: str, num_cases: int, seed: int | None) -> int:
    """Evaluate a restructuring scenario for the bundled B2B SaaS organization."""
    if scenario_type not in SCENARIO_TYPES:
        available = ", ".join(sorted(SCENARIO_TYPES))
        print(f"Unknown scenario type '{scenario_type}'. Available: {available}", file=sys.stderr)
        return 1
    org, result, pool = _build_saas_cross_workflow_result(num_cases, seed, None)
    kpi_results = {wf_id: result.kpi_for(wf_id) for wf_id in result.workflow_ids}
    org_budget = build_saas_org_budget()
    scenario = RestructuringScenario(
        scenario_id="cli-scenario",
        scenario_type=scenario_type,
        description=f"Evaluate '{scenario_type}' for {org.name}",
    )
    impacts = compare_restructuring_scenarios(org, kpi_results, [scenario], org_budget)
    print(generate_restructuring_report(impacts))
    return 0


def org_executive_report(
    num_cases: int, seed: int | None, html_output: str | None
) -> int:
    """Generate a full organizational executive report for the bundled SaaS org."""
    org, result, pool = _build_saas_cross_workflow_result(num_cases, seed, None)
    kpi_results = {wf_id: result.kpi_for(wf_id) for wf_id in result.workflow_ids}
    org_budget = build_saas_org_budget()
    health_score = compute_org_health(org, org_budget, pool, kpi_results)

    config = GrowthConfig(base_cases_per_month=num_cases, base_headcount=org.total_headcount())
    growth_projection = project_growth(org, org_budget, config)

    from b2b_workflow_simulator.restructuring import (
        CREATE_AI_OPS_TEAM,
        HIRE_ADDITIONAL_STAFF,
        REDUCE_APPROVAL_LAYERS,
    )
    scenarios = [
        RestructuringScenario(
            scenario_id="s1",
            scenario_type=CREATE_AI_OPS_TEAM,
            description="Create a dedicated AI Operations team",
        ),
        RestructuringScenario(
            scenario_id="s2",
            scenario_type=HIRE_ADDITIONAL_STAFF,
            description="Hire additional CS agents",
            parameters={"headcount_delta": 2},
        ),
        RestructuringScenario(
            scenario_id="s3",
            scenario_type=REDUCE_APPROVAL_LAYERS,
            description="Reduce approval layers in invoice processing",
            parameters={"approval_layers_removed": 1},
        ),
    ]
    restructuring_impacts = compare_restructuring_scenarios(org, kpi_results, scenarios, org_budget)

    report = OrgDigitalTwinReport(
        org=org,
        kpi_results=kpi_results,
        org_budget=org_budget,
        shared_resources=pool,
        health_score=health_score,
        growth_projection=growth_projection,
        restructuring_impacts=restructuring_impacts,
        cross_workflow_result=result,
    )
    print(generate_org_digital_twin_report(report))

    if html_output:
        Path(html_output).write_text(render_org_executive_html(report))
        print(f"\nHTML report written to {html_output}")
    return 0


def _load_profile(path: str | None) -> AssumptionProfile:
    """Load profile from path, or return the default base profile."""
    if path is None:
        return AssumptionProfile()
    try:
        return load_assumption_profile(path)
    except (OSError, ValueError) as exc:
        print(f"Failed to load assumption profile '{path}': {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _run_before_after_with_profile(
    example_name: str,
    profile: AssumptionProfile,
    arrival_interval_minutes: float | None = None,
    engine: str = "simple",
    collect_events: bool = False,
):
    """Build and simulate both variants with profile multipliers applied.

    Actor costs and error rates are scaled by the profile's multipliers
    before the simulation runs.  The original workflow objects are not
    mutated.  Returns the same 4-tuple as ``_run_before_after``, or
    ``None`` on error.
    """
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(
            f"Unknown example '{example_name}'. Available: {available}",
            file=sys.stderr,
        )
        return None

    build_before, build_after = EXAMPLES[example_name]
    before_workflow = apply_profile_to_workflow(build_before(), profile)
    after_workflow = apply_profile_to_workflow(build_after(), profile)

    before_result = SimulationRunner(seed=profile.seed).run(
        before_workflow,
        profile.num_cases,
        arrival_interval_minutes=arrival_interval_minutes,
        engine=engine,
        collect_events=collect_events,
    )
    after_result = SimulationRunner(seed=profile.seed).run(
        after_workflow,
        profile.num_cases,
        arrival_interval_minutes=arrival_interval_minutes,
        engine=engine,
        collect_events=collect_events,
    )
    return before_workflow, after_workflow, before_result, after_result


def visualize_workflow(
    example_name: str, variant: str, fmt: str, output: str | None
) -> int:
    """Render a bundled workflow as Mermaid or plain text."""
    workflow = _select_variant(example_name, variant)
    if workflow is None:
        return 1
    if fmt == "mermaid":
        content = to_mermaid(workflow)
    elif fmt == "compare":
        build_before, build_after = EXAMPLES[example_name]
        content = (
            compare_mermaid(build_before(), build_after())
            if fmt == "compare"
            else compare_text(build_before(), build_after())
        )
    else:
        content = to_text(workflow)
    if output:
        Path(output).write_text(content)
        print(f"Written to {output}")
    else:
        print(content)
    return 0


def roi_waterfall(
    example_name: str,
    num_cases: int,
    seed: int,
    implementation_cost: float | None,
    fmt: str,
    output: str | None,
    assumptions_path: str | None,
) -> int:
    """Run a bundled example and render an ROI waterfall."""
    profile = _load_profile(assumptions_path)
    effective_cases = num_cases if num_cases is not None else profile.num_cases
    effective_seed = seed if seed is not None else profile.seed
    effective_impl = (
        implementation_cost if implementation_cost is not None
        else profile.implementation_cost
    )
    profile = AssumptionProfile(
        num_cases=effective_cases, seed=effective_seed,
        implementation_cost=effective_impl,
        currency_label=profile.currency_label,
        ai_error_rate_multiplier=profile.ai_error_rate_multiplier,
        ai_cost_multiplier=profile.ai_cost_multiplier,
        human_hourly_cost_multiplier=profile.human_hourly_cost_multiplier,
        collect_events=False,
    )
    outcome = _run_before_after_with_profile(example_name, profile)
    if outcome is None:
        return 1
    _before_wf, _after_wf, before_result, after_result = outcome
    waterfall = build_roi_waterfall(
        before_result.kpi, after_result.kpi,
        implementation_cost=effective_impl,
        currency=profile.currency_label,
    )
    if fmt == "svg":
        content = waterfall_to_svg(waterfall)
    else:
        content = waterfall_to_text(waterfall)

    if output:
        Path(output).write_text(content)
        print(f"Written to {output}")
    else:
        print(content)
    return 0


def bottleneck_heatmap(
    example_name: str,
    variant: str,
    num_cases: int,
    seed: int,
    arrival_interval: float | None,
    fmt: str,
    output: str | None,
    assumptions_path: str | None,
) -> int:
    """Run a bundled example variant and render a bottleneck heatmap."""
    profile = _load_profile(assumptions_path)
    effective_cases = num_cases if num_cases is not None else profile.num_cases
    effective_seed = seed if seed is not None else profile.seed
    effective_interval = (
        arrival_interval if arrival_interval is not None
        else profile.arrival_interval_minutes
    )

    raw_workflow = _select_variant(example_name, variant)
    if raw_workflow is None:
        return 1
    workflow = apply_profile_to_workflow(raw_workflow, profile)
    result = SimulationRunner(seed=effective_seed).run(
        workflow, effective_cases,
        arrival_interval_minutes=effective_interval,
        collect_events=False,
    )
    heatmap = build_bottleneck_heatmap(workflow, result.kpi)
    if fmt == "svg":
        content = heatmap_to_svg(heatmap)
    else:
        content = heatmap_to_text(heatmap)

    if output:
        Path(output).write_text(content)
        print(f"Written to {output}")
    else:
        print(content)
    return 0


def executive_snapshot(
    example_name: str,
    num_cases: int,
    seed: int,
    implementation_cost: float | None,
    arrival_interval: float | None,
    html_output: str | None,
    assumptions_path: str | None,
) -> int:
    """Run both variants of a bundled example and print a concise snapshot."""
    profile = _load_profile(assumptions_path)
    effective_cases = num_cases if num_cases is not None else profile.num_cases
    effective_seed = seed if seed is not None else profile.seed
    effective_impl = (
        implementation_cost if implementation_cost is not None
        else profile.implementation_cost
    )
    effective_interval = (
        arrival_interval if arrival_interval is not None
        else profile.arrival_interval_minutes
    )

    profile = AssumptionProfile(
        num_cases=effective_cases, seed=effective_seed,
        implementation_cost=effective_impl,
        arrival_interval_minutes=effective_interval,
        ai_error_rate_multiplier=profile.ai_error_rate_multiplier,
        ai_cost_multiplier=profile.ai_cost_multiplier,
        human_hourly_cost_multiplier=profile.human_hourly_cost_multiplier,
        collect_events=False,
    )
    outcome = _run_before_after_with_profile(
        example_name, profile,
        arrival_interval_minutes=effective_interval,
    )
    if outcome is None:
        return 1
    _before_wf, _after_wf, before_result, after_result = outcome
    snapshot = build_snapshot(
        before_result.kpi, after_result.kpi,
        implementation_cost=effective_impl,
    )
    print(snapshot_to_text(snapshot))
    if html_output:
        Path(html_output).write_text(snapshot_to_html(snapshot))
        print(f"\nHTML report written to {html_output}")
    return 0


def consultant_packet(
    example_name: str,
    num_cases: int,
    seed: int,
    implementation_cost: float | None,
    output_dir: str,
    assumptions_path: str | None,
) -> int:
    """Generate a full stakeholder packet directory for a bundled example."""
    profile = _load_profile(assumptions_path)
    effective_cases = num_cases if num_cases is not None else profile.num_cases
    effective_seed = seed if seed is not None else profile.seed
    effective_impl = (
        implementation_cost if implementation_cost is not None
        else profile.implementation_cost
    )
    profile = AssumptionProfile(
        num_cases=effective_cases,
        seed=effective_seed,
        implementation_cost=effective_impl,
        currency_label=profile.currency_label,
        description=profile.description,
        ai_error_rate_multiplier=profile.ai_error_rate_multiplier,
        ai_cost_multiplier=profile.ai_cost_multiplier,
        human_hourly_cost_multiplier=profile.human_hourly_cost_multiplier,
        collect_events=False,
    )

    outcome = _run_before_after_with_profile(example_name, profile)
    if outcome is None:
        return 1
    before_wf, after_wf, before_result, after_result = outcome

    dest = Path(output_dir)
    files = generate_packet(
        example_name, before_wf, after_wf, before_result, after_result,
        profile, dest,
    )
    print(f"Consultant packet written to {dest}/")
    for filename in sorted(files):
        print(f"  {filename}")
    return 0


def generate_example_gallery(output_dir: str) -> int:
    """Generate deterministic example outputs for the gallery."""
    from b2b_workflow_simulator.assumptions import AssumptionProfile

    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)

    examples_cfg = [
        ("sales-lead-qualification",      "sales_lead_snapshot.txt"),
        ("invoice-processing",            "invoice_processing_snapshot.txt"),
        ("customer-support-ticket-resolution", "customer_support_snapshot.txt"),
    ]
    profile = AssumptionProfile(num_cases=300, seed=42, implementation_cost=8000.0)

    for example_name, snapshot_file in examples_cfg:
        outcome = _run_before_after(example_name, profile.num_cases, profile.seed,
                                    collect_events=False)
        if outcome is None:
            continue
        _before_wf, _after_wf, before_result, after_result = outcome
        snap = build_snapshot(
            before_result.kpi, after_result.kpi,
            implementation_cost=profile.implementation_cost,
        )
        (dest / snapshot_file).write_text(snapshot_to_text(snap))

    inv_outcome = _run_before_after("invoice-processing", profile.num_cases, profile.seed,
                                    collect_events=False)
    if inv_outcome is not None:
        _bwf, _awf, _br, inv_after = inv_outcome
        waterfall = build_roi_waterfall(
            _br.kpi, inv_after.kpi,
            implementation_cost=profile.implementation_cost,
        )
        (dest / "invoice_processing_roi_waterfall.svg").write_text(waterfall_to_svg(waterfall))
        heatmap = build_bottleneck_heatmap(_awf, inv_after.kpi)
        (dest / "invoice_processing_bottleneck_heatmap.svg").write_text(heatmap_to_svg(heatmap))

    print(f"Example gallery outputs written to {dest}/")
    for f in sorted(dest.iterdir()):
        print(f"  {f.name}")
    return 0


def list_scenarios_cmd(category: str | None, fmt: str) -> int:
    """List all registered scenarios."""
    scenarios = (
        scenarios_by_category(category) if category else list_scenarios()
    )
    if fmt == "json":
        import json as _json
        data = [
            {
                "slug": s.slug,
                "name": s.name,
                "category": CATEGORY_LABELS.get(s.category, s.category),
                "description": s.description,
                "target_users": s.target_users,
                "recommended_commands": s.recommended_commands,
            }
            for s in scenarios
        ]
        print(_json.dumps(data, indent=2))
        return 0

    if not scenarios:
        print("No scenarios found.")
        return 0

    current_cat = None
    for s in scenarios:
        cat_label = CATEGORY_LABELS.get(s.category, s.category)
        if cat_label != current_cat:
            if current_cat is not None:
                print()
            print(f"  {cat_label}")
            print(f"  {'─' * len(cat_label)}")
            current_cat = cat_label
        print(f"    {s.slug:<42} {s.description[:55]}")
    print()
    print(f"Total: {len(scenarios)} scenario(s).  Use `b2b-simulator run-example <slug>` to run.")
    return 0


def generate_case_studies_cmd(
    output_dir: str,
    scenario_slug: str | None,
    profiles: str,
) -> int:
    """Generate case study directories for all or one scenario."""
    profile_list = [p.strip() for p in profiles.split(",")]
    valid = {"base", "conservative", "aggressive"}
    invalid = set(profile_list) - valid
    if invalid:
        print(
            f"Invalid profile names: {invalid}. Use: base, conservative, aggressive",
            file=sys.stderr,
        )
        return 1

    if scenario_slug:
        if not scenario_exists(scenario_slug):
            from b2b_workflow_simulator.scenarios import scenario_names
            print(
                f"Unknown scenario '{scenario_slug}'. "
                f"Available: {', '.join(scenario_names())}",
                file=sys.stderr,
            )
            return 1
        from b2b_workflow_simulator.scenarios import get_scenario
        scenario = get_scenario(scenario_slug)
        files = generate_case_study(scenario, Path(output_dir) / scenario_slug, profile_list)
        print(f"Case study written to {Path(output_dir) / scenario_slug}/")
        for fn in sorted(files):
            print(f"  {fn}")
    else:
        results = generate_all_case_studies(Path(output_dir), profiles=profile_list)
        print(f"Case studies written to {output_dir}/")
        for slug in sorted(results):
            print(f"  {slug}/ ({len(results[slug])} files)")
    return 0


def scenario_matrix_cmd(
    profile_name: str,
    fmt: str,
    output: str | None,
    scenario_slug: str | None,
) -> int:
    """Run scenario matrix comparison."""
    slugs = [scenario_slug] if scenario_slug else None
    rows = build_scenario_matrix(profile_name=profile_name, scenario_slugs=slugs)
    if fmt == "json":
        content = matrix_to_json(rows)
    else:
        content = matrix_to_text(rows)

    if output:
        Path(output).write_text(content)
        print(f"Written to {output}")
    else:
        print(content)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="b2b-simulator",
        description="Simulate and compare before/after B2B workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run-example", help="Run a bundled example workflow and compare before/after KPIs."
    )
    run_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    run_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per variant (default: 200).",
    )
    run_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    run_parser.add_argument(
        "--engine",
        choices=ENGINES,
        default="simple",
        help="Simulation engine: 'simple' (default) or 'discrete'.",
    )

    portfolio_parser = subparsers.add_parser(
        "run-portfolio",
        help="Run several bundled examples together and print a per-workflow KPI summary.",
    )
    portfolio_parser.add_argument(
        "names",
        nargs="+",
        choices=sorted(EXAMPLES),
        help="Names of the bundled examples to include in the portfolio.",
    )
    portfolio_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per variant (default: 200).",
    )
    portfolio_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )

    compare_parser = subparsers.add_parser(
        "compare-example",
        help="Run a bundled example and print a full before/after ROI report.",
    )
    compare_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    compare_parser.add_argument(
        "--cases",
        type=int,
        default=None,
        help="Number of cases to simulate per variant (default: 200, or profile.num_cases).",
    )
    compare_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible results (default: 42, or profile.seed).",
    )
    compare_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="One-time cost of implementing the redesign, for payback analysis.",
    )
    compare_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )
    compare_parser.add_argument(
        "--engine",
        choices=ENGINES,
        default=None,
        help="Simulation engine: 'simple' (default) or 'discrete', or profile.engine.",
    )
    compare_parser.add_argument(
        "--assumptions",
        default=None,
        help=(
            'Path to an assumption profile JSON file. '
            'Scales AI error rates, AI costs, and human costs; '
            'also overrides --cases, --seed, --arrival-interval, '
            'and --implementation-cost.'
        ),
    )

    compare_portfolio_parser = subparsers.add_parser(
        "compare-portfolio",
        help="Run several bundled examples together and print a full portfolio report.",
    )
    compare_portfolio_parser.add_argument(
        "names",
        nargs="+",
        choices=sorted(EXAMPLES),
        help="Names of the bundled examples to include in the portfolio.",
    )
    compare_portfolio_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per variant (default: 200).",
    )
    compare_portfolio_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    compare_portfolio_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="One-time implementation cost applied to every workflow in the portfolio.",
    )
    compare_portfolio_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )
    compare_portfolio_parser.add_argument(
        "--rank-by",
        choices=RANK_BY_OPTIONS,
        default="total_cost_savings",
        help="Metric used to rank workflows (default: total_cost_savings).",
    )
    compare_portfolio_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML portfolio report to this path.",
    )

    sensitivity_parser = subparsers.add_parser(
        "sensitivity-example",
        help="Sweep one assumption for a bundled example and print a sensitivity table.",
    )
    sensitivity_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    sensitivity_parser.add_argument(
        "--parameter",
        choices=PARAMETERS,
        required=True,
        help="Which assumption to sweep.",
    )
    sensitivity_parser.add_argument(
        "--values",
        type=_parse_float_list,
        required=True,
        help="Comma-separated list of values to test, e.g. '0.0,0.1,0.2'.",
    )
    sensitivity_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per value (default: 200).",
    )
    sensitivity_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    sensitivity_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="Baseline implementation cost used for every value (default: None).",
    )

    export_parser = subparsers.add_parser(
        "export-example",
        help="Run a bundled example and export events, KPIs, and the comparison to disk.",
    )
    export_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    export_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per variant (default: 200).",
    )
    export_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    export_parser.add_argument(
        "--format",
        choices=EXPORT_FORMATS,
        default="json",
        help="Export format (default: json). csv exports the comparison only.",
    )
    export_parser.add_argument(
        "--output-dir",
        default="exports",
        help="Directory to write exported files into (default: ./exports).",
    )
    export_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="One-time cost of implementing the redesign, for payback analysis.",
    )
    export_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )

    html_report_parser = subparsers.add_parser(
        "html-report-example",
        help="Run a bundled example and write a static HTML redesign report.",
    )
    html_report_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    html_report_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per variant (default: 200).",
    )
    html_report_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    html_report_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="One-time cost of implementing the redesign, for payback analysis.",
    )
    html_report_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )
    html_report_parser.add_argument(
        "--output",
        default="report.html",
        help="Path to write the HTML report to (default: ./report.html).",
    )

    save_parser = subparsers.add_parser(
        "save-example",
        help="Save a bundled example's before/after workflow definitions as JSON.",
    )
    save_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to save.",
    )
    save_parser.add_argument(
        "--output-dir",
        default="workflows",
        help="Directory to write workflow JSON files into (default: ./workflows).",
    )

    load_parser = subparsers.add_parser(
        "load-example",
        help="Load a workflow definition from JSON and print its simulated KPI summary.",
    )
    load_parser.add_argument("path", help="Path to a workflow definition JSON file.")
    load_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate (default: 200).",
    )
    load_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )

    monte_carlo_parser = subparsers.add_parser(
        "monte-carlo-example",
        help="Run a Monte Carlo comparison for a bundled example across many seeds.",
    )
    monte_carlo_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    monte_carlo_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per run (default: 200).",
    )
    monte_carlo_parser.add_argument(
        "--seeds",
        type=_parse_int_list,
        default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        help="Comma-separated list of seeds to run, e.g. '1,2,3' (default: 1..10).",
    )
    monte_carlo_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="One-time cost of implementing the redesign, for payback analysis.",
    )
    monte_carlo_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )
    monte_carlo_parser.add_argument(
        "--engine",
        choices=ENGINES,
        default="simple",
        help="Simulation engine: 'simple' (default) or 'discrete'.",
    )
    monte_carlo_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML Monte Carlo report to this path.",
    )

    monte_carlo_portfolio_parser = subparsers.add_parser(
        "monte-carlo-portfolio",
        help="Run a Monte Carlo comparison for several bundled examples and summarize each.",
    )
    monte_carlo_portfolio_parser.add_argument(
        "names",
        nargs="+",
        choices=sorted(EXAMPLES),
        help="Names of the bundled examples to include.",
    )
    monte_carlo_portfolio_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per run (default: 200).",
    )
    monte_carlo_portfolio_parser.add_argument(
        "--seeds",
        type=_parse_int_list,
        default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        help="Comma-separated list of seeds to run, e.g. '1,2,3' (default: 1..10).",
    )
    monte_carlo_portfolio_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="One-time implementation cost applied to every workflow.",
    )
    monte_carlo_portfolio_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )

    sensitivity_grid_parser = subparsers.add_parser(
        "sensitivity-grid-example",
        help="Sweep two assumptions for a bundled example and print an ROI matrix.",
    )
    sensitivity_grid_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    sensitivity_grid_parser.add_argument(
        "--x-parameter",
        choices=PARAMETERS,
        required=True,
        help="Parameter to sweep along the x-axis (columns).",
    )
    sensitivity_grid_parser.add_argument(
        "--x-values",
        type=_parse_float_list,
        required=True,
        help="Comma-separated list of x-axis values, e.g. '0.0,0.1,0.2'.",
    )
    sensitivity_grid_parser.add_argument(
        "--y-parameter",
        choices=PARAMETERS,
        required=True,
        help="Parameter to sweep along the y-axis (rows).",
    )
    sensitivity_grid_parser.add_argument(
        "--y-values",
        type=_parse_float_list,
        required=True,
        help="Comma-separated list of y-axis values, e.g. '0.0,0.1,0.2'.",
    )
    sensitivity_grid_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per grid cell (default: 200).",
    )
    sensitivity_grid_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    sensitivity_grid_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="Baseline implementation cost used for every grid cell (default: None).",
    )
    sensitivity_grid_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML sensitivity grid report to this path.",
    )

    capacity_parser = subparsers.add_parser(
        "capacity-analysis",
        help="Run one variant of a bundled example and print a capacity/staffing report.",
    )
    capacity_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    capacity_parser.add_argument(
        "--variant",
        choices=("before", "after"),
        default="after",
        help="Which workflow variant to analyze (default: after).",
    )
    capacity_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate (default: 200).",
    )
    capacity_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    capacity_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )
    capacity_parser.add_argument(
        "--target-utilization",
        type=float,
        default=DEFAULT_TARGET_UTILIZATION,
        help=f"Desired steady-state utilization (default: {DEFAULT_TARGET_UTILIZATION}).",
    )
    capacity_parser.add_argument(
        "--overload-threshold",
        type=float,
        default=DEFAULT_OVERLOAD_THRESHOLD,
        help=f"Utilization at/above which a resource is overloaded "
        f"(default: {DEFAULT_OVERLOAD_THRESHOLD}).",
    )
    capacity_parser.add_argument(
        "--underutilization-threshold",
        type=float,
        default=DEFAULT_UNDERUTILIZATION_THRESHOLD,
        help=f"Utilization at/below which a resource is underutilized "
        f"(default: {DEFAULT_UNDERUTILIZATION_THRESHOLD}).",
    )
    capacity_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML capacity report to this path.",
    )

    team_utilization_parser = subparsers.add_parser(
        "team-utilization",
        help="Run one variant of a bundled example and print raw utilization figures.",
    )
    team_utilization_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to run.",
    )
    team_utilization_parser.add_argument(
        "--variant",
        choices=("before", "after"),
        default="after",
        help="Which workflow variant to analyze (default: after).",
    )
    team_utilization_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate (default: 200).",
    )
    team_utilization_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    team_utilization_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )

    policy_parser = subparsers.add_parser(
        "policy-analysis",
        help="Evaluate a bundled example's attached policies and print a governance report.",
    )
    policy_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to analyze.",
    )
    policy_parser.add_argument(
        "--variant",
        choices=("before", "after"),
        default="after",
        help="Which workflow variant to analyze (default: after).",
    )
    policy_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML policy report to this path.",
    )

    compliance_parser = subparsers.add_parser(
        "compliance-analysis",
        help="Evaluate a bundled example's compliance requirements and print a report.",
    )
    compliance_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to analyze.",
    )
    compliance_parser.add_argument(
        "--variant",
        choices=("before", "after"),
        default="after",
        help="Which workflow variant to analyze (default: after).",
    )
    compliance_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML compliance report to this path.",
    )

    risk_parser = subparsers.add_parser(
        "risk-analysis",
        help="Simulate a bundled example variant and print an organizational risk assessment.",
    )
    risk_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to analyze.",
    )
    risk_parser.add_argument(
        "--variant",
        choices=("before", "after"),
        default="after",
        help="Which workflow variant to analyze (default: after).",
    )
    risk_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate (default: 200).",
    )
    risk_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    risk_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )
    risk_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML risk report to this path.",
    )

    readiness_parser = subparsers.add_parser(
        "readiness-analysis",
        help="Simulate a bundled example variant and print an AI adoption readiness assessment.",
    )
    readiness_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to analyze.",
    )
    readiness_parser.add_argument(
        "--variant",
        choices=("before", "after"),
        default="after",
        help="Which workflow variant to analyze (default: after).",
    )
    readiness_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate (default: 200).",
    )
    readiness_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    readiness_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML AI adoption report to this path.",
    )

    recommend_parser = subparsers.add_parser(
        "recommend-redesign",
        help="Simulate a bundled example variant and print actionable redesign recommendations.",
    )
    recommend_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to analyze.",
    )
    recommend_parser.add_argument(
        "--variant",
        choices=("before", "after"),
        default="after",
        help="Which workflow variant to analyze (default: after).",
    )
    recommend_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate (default: 200).",
    )
    recommend_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    recommend_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML recommendation report to this path.",
    )

    executive_parser = subparsers.add_parser(
        "executive-report",
        help="Run a bundled example and print a full executive assessment report.",
    )
    executive_parser.add_argument(
        "name",
        choices=sorted(EXAMPLES),
        help="Name of the bundled example to analyze.",
    )
    executive_parser.add_argument(
        "--cases",
        type=int,
        default=200,
        help="Number of cases to simulate per variant (default: 200).",
    )
    executive_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    executive_parser.add_argument(
        "--implementation-cost",
        type=float,
        default=None,
        help="One-time cost of implementing the redesign, for payback analysis.",
    )
    executive_parser.add_argument(
        "--arrival-interval",
        type=float,
        default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )
    executive_parser.add_argument(
        "--html-output",
        default=None,
        help="If set, also write a static HTML executive report to this path.",
    )

    run_org_parser = subparsers.add_parser(
        "run-org",
        help="Run the bundled B2B SaaS org simulation and print a KPI summary.",
    )
    run_org_parser.add_argument(
        "--cases", type=int, default=200,
        help="Number of cases to simulate per workflow (default: 200).",
    )
    run_org_parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    run_org_parser.add_argument(
        "--arrival-interval", type=float, default=None,
        help="Minutes between case arrivals; enables capacity-aware queueing.",
    )

    org_health_parser = subparsers.add_parser(
        "org-health",
        help="Compute and display the organizational health score for the bundled SaaS org.",
    )
    org_health_parser.add_argument(
        "--cases", type=int, default=200,
        help="Number of cases to simulate per workflow (default: 200).",
    )
    org_health_parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    org_health_parser.add_argument(
        "--html-output", default=None,
        help="If set, also write a static HTML health report to this path.",
    )

    org_budget_parser = subparsers.add_parser(
        "org-budget-analysis",
        help="Print the budget analysis for the bundled B2B SaaS organization.",
    )
    org_budget_parser.add_argument(
        "--html-output", default=None,
        help="If set, also write a static HTML budget report to this path.",
    )

    org_resource_parser = subparsers.add_parser(
        "org-resource-contention",
        help="Simulate the SaaS org and print shared resource contention analysis.",
    )
    org_resource_parser.add_argument(
        "--cases", type=int, default=200,
        help="Number of cases to simulate per workflow (default: 200).",
    )
    org_resource_parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    org_resource_parser.add_argument(
        "--days", type=int, default=1,
        help="Reference period in working days for contention analysis (default: 1).",
    )
    org_resource_parser.add_argument(
        "--html-output", default=None,
        help="If set, write a static HTML org report including contention to this path.",
    )

    org_growth_parser = subparsers.add_parser(
        "org-growth-projection",
        help="Project 12-month growth for the bundled B2B SaaS organization.",
    )
    org_growth_parser.add_argument(
        "--monthly-growth-rate", type=float, default=0.05,
        help="Monthly case volume growth rate as a decimal (default: 0.05 = 5%%).",
    )
    org_growth_parser.add_argument(
        "--base-cases", type=int, default=200,
        help="Base case volume per month (default: 200).",
    )
    org_growth_parser.add_argument(
        "--base-headcount", type=int, default=18,
        help="Starting headcount (default: 18).",
    )
    org_growth_parser.add_argument(
        "--headcount-growth", type=float, default=0.0,
        help="Monthly headcount growth rate (default: 0.0).",
    )
    org_growth_parser.add_argument(
        "--ai-adoption-rate", type=float, default=0.02,
        help="Monthly AI adoption increase (default: 0.02 = +2 pp/month).",
    )
    org_growth_parser.add_argument(
        "--html-output", default=None,
        help="If set, also write a static HTML growth report to this path.",
    )

    org_restructure_parser = subparsers.add_parser(
        "org-restructure-scenario",
        help="Evaluate a restructuring scenario for the bundled B2B SaaS organization.",
    )
    org_restructure_parser.add_argument(
        "scenario_type",
        choices=sorted(SCENARIO_TYPES),
        help="Type of restructuring scenario to evaluate.",
    )
    org_restructure_parser.add_argument(
        "--cases", type=int, default=200,
        help="Number of cases to simulate per workflow for baseline (default: 200).",
    )
    org_restructure_parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible results (default: 42).",
    )

    org_executive_parser = subparsers.add_parser(
        "org-executive-report",
        help="Generate a full organizational executive report for the bundled SaaS org.",
    )
    org_executive_parser.add_argument(
        "--cases", type=int, default=200,
        help="Number of cases to simulate per workflow (default: 200).",
    )
    org_executive_parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible results (default: 42).",
    )
    org_executive_parser.add_argument(
        "--html-output", default=None,
        help="If set, also write a static HTML executive report to this path.",
    )

    # ------------------------------------------------------------------
    # Phase 7: visualization, waterfall, heatmap, snapshot, packet
    # ------------------------------------------------------------------

    vis_parser = subparsers.add_parser(
        "visualize-workflow",
        help="Render a bundled workflow as a Mermaid flowchart or plain-text graph.",
    )
    vis_parser.add_argument("name", choices=sorted(EXAMPLES),
                            help="Name of the bundled example.")
    vis_parser.add_argument("--variant", choices=("before", "after", "compare"),
                            default="after",
                            help="Variant to render: before, after, or compare (default: after).")
    vis_parser.add_argument("--format", choices=("mermaid", "text"),
                            default="mermaid",
                            help="Output format: mermaid (default) or text.")
    vis_parser.add_argument("--output", default=None,
                            help="If set, write output to this file instead of stdout.")

    waterfall_parser = subparsers.add_parser(
        "roi-waterfall",
        help="Run a bundled example and show a decomposed ROI waterfall.",
    )
    waterfall_parser.add_argument("name", choices=sorted(EXAMPLES),
                                  help="Name of the bundled example.")
    waterfall_parser.add_argument("--cases", type=int, default=None,
                                  help="Cases to simulate (default: 200, or profile.num_cases).")
    waterfall_parser.add_argument("--seed", type=int, default=None,
                                  help="Random seed (default: 42, or profile.seed).")
    waterfall_parser.add_argument("--implementation-cost", type=float, default=None,
                                  help="One-time implementation cost.")
    waterfall_parser.add_argument("--format", choices=("text", "svg"), default="text",
                                  help="Output format: text (default) or svg.")
    waterfall_parser.add_argument("--output", default=None,
                                  help="If set, write output to this file.")
    waterfall_parser.add_argument("--assumptions", default=None,
                                  help=(
                                      'Path to an assumption profile JSON file. '
                                      'Scales AI error rates, AI costs, and human costs; '
                                      'also overrides --cases, --seed, --arrival-interval, '
                                      'and --implementation-cost.'
                                  ))

    heatmap_parser = subparsers.add_parser(
        "bottleneck-heatmap",
        help="Run a bundled example and show a bottleneck pressure heatmap.",
    )
    heatmap_parser.add_argument("name", choices=sorted(EXAMPLES),
                                help="Name of the bundled example.")
    heatmap_parser.add_argument("--variant", choices=("before", "after"), default="after",
                                help="Variant to analyze (default: after).")
    heatmap_parser.add_argument("--cases", type=int, default=None,
                                help="Cases to simulate (default: 200, or profile.num_cases).")
    heatmap_parser.add_argument("--seed", type=int, default=None,
                                help="Random seed (default: 42, or profile.seed).")
    heatmap_parser.add_argument("--arrival-interval", type=float, default=None,
                                help="Minutes between case arrivals.")
    heatmap_parser.add_argument("--format", choices=("text", "svg"), default="text",
                                help="Output format: text (default) or svg.")
    heatmap_parser.add_argument("--output", default=None,
                                help="If set, write output to this file.")
    heatmap_parser.add_argument("--assumptions", default=None,
                                help=(
                                    'Path to an assumption profile JSON file. '
                                    'Scales AI error rates, AI costs, and human costs; '
                                    'also overrides --cases, --seed, --arrival-interval, '
                                    'and --implementation-cost.'
                                ))

    snapshot_parser = subparsers.add_parser(
        "executive-snapshot",
        help="Run a bundled example and print a concise one-page stakeholder snapshot.",
    )
    snapshot_parser.add_argument("name", choices=sorted(EXAMPLES),
                                 help="Name of the bundled example.")
    snapshot_parser.add_argument("--cases", type=int, default=None,
                                 help="Cases to simulate (default: 200, or profile.num_cases).")
    snapshot_parser.add_argument("--seed", type=int, default=None,
                                 help="Random seed (default: 42, or profile.seed).")
    snapshot_parser.add_argument("--implementation-cost", type=float, default=None,
                                 help="One-time implementation cost.")
    snapshot_parser.add_argument("--arrival-interval", type=float, default=None,
                                 help="Minutes between case arrivals.")
    snapshot_parser.add_argument("--html-output", default=None,
                                 help="If set, also write an HTML snapshot to this path.")
    snapshot_parser.add_argument("--assumptions", default=None,
                                 help=(
                                     'Path to an assumption profile JSON file. '
                                     'Scales AI error rates, AI costs, and human costs; '
                                     'also overrides --cases, --seed, --arrival-interval, '
                                     'and --implementation-cost.'
                                 ))

    packet_parser = subparsers.add_parser(
        "consultant-packet",
        help="Generate a full stakeholder packet directory for a bundled example.",
    )
    packet_parser.add_argument("name", choices=sorted(EXAMPLES),
                               help="Name of the bundled example.")
    packet_parser.add_argument("--cases", type=int, default=None,
                               help="Cases to simulate (default: 200, or profile.num_cases).")
    packet_parser.add_argument("--seed", type=int, default=None,
                               help="Random seed (default: 42, or profile.seed).")
    packet_parser.add_argument("--implementation-cost", type=float, default=None,
                               help="One-time implementation cost.")
    packet_parser.add_argument("--output-dir", default="packet",
                               help="Directory to write the packet into (default: ./packet).")
    packet_parser.add_argument("--assumptions", default=None,
                               help=(
                                   'Path to an assumption profile JSON file. '
                                   'Scales AI error rates, AI costs, and human costs; '
                                   'also overrides --cases, --seed, --arrival-interval, '
                                   'and --implementation-cost.'
                               ))

    gallery_parser = subparsers.add_parser(
        "generate-example-gallery",
        help="Generate deterministic example output files for the docs gallery.",
    )
    gallery_parser.add_argument("--output-dir", default="examples/outputs",
                                help="Directory for gallery files (default: examples/outputs).")

    # ------------------------------------------------------------------
    # Phase 8: scenario library commands
    # ------------------------------------------------------------------

    list_parser = subparsers.add_parser(
        "list-scenarios",
        help="List all registered simulation scenarios with category and description.",
    )
    list_parser.add_argument(
        "--category", default=None, choices=sorted(SCENARIO_CATEGORIES),
        help="Filter by category.",
    )
    list_parser.add_argument(
        "--format", dest="fmt", choices=("text", "json"), default="text",
        help="Output format: text (default) or json.",
    )

    case_studies_parser = subparsers.add_parser(
        "generate-case-studies",
        help="Generate full case study directories for all or one scenario.",
    )
    case_studies_parser.add_argument(
        "--output-dir", default="case_studies",
        help="Root directory to write case studies into (default: ./case_studies).",
    )
    case_studies_parser.add_argument(
        "--scenario", default=None, dest="scenario_slug",
        help="Generate only this scenario slug.  Omit for all scenarios.",
    )
    case_studies_parser.add_argument(
        "--profiles", default="base,conservative,aggressive",
        help="Comma-separated profile names: base, conservative, aggressive "
             "(default: all three).",
    )

    matrix_parser = subparsers.add_parser(
        "scenario-matrix",
        help="Compare all scenarios at a high level for consulting prioritization.",
    )
    matrix_parser.add_argument(
        "--profile", default="base",
        choices=("base", "conservative", "aggressive"),
        help="Assumption profile to use for all scenarios (default: base).",
    )
    matrix_parser.add_argument(
        "--format", dest="fmt", choices=("text", "json"), default="text",
        help="Output format: text (default) or json.",
    )
    matrix_parser.add_argument(
        "--output", default=None,
        help="If set, write output to this file instead of stdout.",
    )
    matrix_parser.add_argument(
        "--scenario", default=None, dest="scenario_slug",
        help="Show only this scenario slug.  Omit for all scenarios.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-example":
        return run_example(args.name, args.cases, args.seed, args.engine)

    if args.command == "run-portfolio":
        return run_portfolio(args.names, args.cases, args.seed)

    if args.command == "compare-portfolio":
        return compare_portfolio(
            args.names,
            args.cases,
            args.seed,
            args.implementation_cost,
            args.arrival_interval,
            args.rank_by,
            args.html_output,
        )

    if args.command == "compare-example":
        return compare_example(
            args.name,
            args.cases,
            args.seed,
            args.implementation_cost,
            args.arrival_interval,
            args.engine,
            getattr(args, "assumptions", None),
        )

    if args.command == "sensitivity-example":
        return sensitivity_example(
            args.name, args.parameter, args.values, args.cases, args.seed, args.implementation_cost
        )

    if args.command == "export-example":
        return export_example(
            args.name,
            args.cases,
            args.seed,
            args.format,
            args.output_dir,
            args.implementation_cost,
            args.arrival_interval,
        )

    if args.command == "html-report-example":
        return html_report_example(
            args.name,
            args.cases,
            args.seed,
            args.implementation_cost,
            args.arrival_interval,
            args.output,
        )

    if args.command == "save-example":
        return save_example(args.name, args.output_dir)

    if args.command == "load-example":
        return load_example(args.path, args.cases, args.seed)

    if args.command == "monte-carlo-example":
        return monte_carlo_example(
            args.name,
            args.cases,
            args.seeds,
            args.implementation_cost,
            args.arrival_interval,
            args.engine,
            args.html_output,
        )

    if args.command == "monte-carlo-portfolio":
        return monte_carlo_portfolio(
            args.names, args.cases, args.seeds, args.implementation_cost, args.arrival_interval
        )

    if args.command == "sensitivity-grid-example":
        return sensitivity_grid_example(
            args.name,
            args.x_parameter,
            args.x_values,
            args.y_parameter,
            args.y_values,
            args.cases,
            args.seed,
            args.implementation_cost,
            args.html_output,
        )

    if args.command == "capacity-analysis":
        return capacity_analysis(
            args.name,
            args.variant,
            args.cases,
            args.seed,
            args.arrival_interval,
            args.target_utilization,
            args.overload_threshold,
            args.underutilization_threshold,
            args.html_output,
        )

    if args.command == "team-utilization":
        return team_utilization(
            args.name, args.variant, args.cases, args.seed, args.arrival_interval
        )

    if args.command == "policy-analysis":
        return policy_analysis(args.name, args.variant, args.html_output)

    if args.command == "compliance-analysis":
        return compliance_analysis(args.name, args.variant, args.html_output)

    if args.command == "risk-analysis":
        return risk_analysis(
            args.name,
            args.variant,
            args.cases,
            args.seed,
            args.arrival_interval,
            args.html_output,
        )

    if args.command == "readiness-analysis":
        return readiness_analysis(args.name, args.variant, args.cases, args.seed, args.html_output)

    if args.command == "recommend-redesign":
        return recommend_redesign(args.name, args.variant, args.cases, args.seed, args.html_output)

    if args.command == "executive-report":
        return executive_report(
            args.name,
            args.cases,
            args.seed,
            args.implementation_cost,
            args.arrival_interval,
            args.html_output,
        )

    if args.command == "run-org":
        return run_org(args.cases, args.seed, args.arrival_interval)

    if args.command == "org-health":
        return org_health(args.cases, args.seed, args.html_output)

    if args.command == "org-budget-analysis":
        return org_budget_analysis(args.html_output)

    if args.command == "org-resource-contention":
        return org_resource_contention(args.days, args.cases, args.seed, args.html_output)

    if args.command == "org-growth-projection":
        return org_growth_projection(
            args.monthly_growth_rate,
            args.base_cases,
            args.base_headcount,
            args.headcount_growth,
            args.ai_adoption_rate,
            args.html_output,
        )

    if args.command == "org-restructure-scenario":
        return org_restructure_scenario(args.scenario_type, args.cases, args.seed)

    if args.command == "org-executive-report":
        return org_executive_report(args.cases, args.seed, args.html_output)

    if args.command == "visualize-workflow":
        return visualize_workflow(args.name, args.variant, args.format, args.output)

    if args.command == "roi-waterfall":
        return roi_waterfall(
            args.name, args.cases, args.seed,
            args.implementation_cost, args.format, args.output,
            getattr(args, "assumptions", None),
        )

    if args.command == "bottleneck-heatmap":
        return bottleneck_heatmap(
            args.name, args.variant, args.cases, args.seed,
            args.arrival_interval, args.format, args.output,
            getattr(args, "assumptions", None),
        )

    if args.command == "executive-snapshot":
        return executive_snapshot(
            args.name, args.cases, args.seed,
            args.implementation_cost, args.arrival_interval,
            args.html_output,
            getattr(args, "assumptions", None),
        )

    if args.command == "consultant-packet":
        return consultant_packet(
            args.name, args.cases, args.seed,
            args.implementation_cost, args.output_dir,
            getattr(args, "assumptions", None),
        )

    if args.command == "generate-example-gallery":
        return generate_example_gallery(args.output_dir)

    if args.command == "list-scenarios":
        return list_scenarios_cmd(args.category, args.fmt)

    if args.command == "generate-case-studies":
        return generate_case_studies_cmd(args.output_dir, args.scenario_slug, args.profiles)

    if args.command == "scenario-matrix":
        return scenario_matrix_cmd(args.profile, args.fmt, args.output, args.scenario_slug)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
