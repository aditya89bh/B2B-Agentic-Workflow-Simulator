"""Command-line interface for running bundled example simulations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from b2b_workflow_simulator.ai_adoption import assess_ai_adoption, generate_ai_adoption_report
from b2b_workflow_simulator.capacity_planning import (
    DEFAULT_OVERLOAD_THRESHOLD,
    DEFAULT_TARGET_UTILIZATION,
    DEFAULT_UNDERUTILIZATION_THRESHOLD,
    analyze_capacity,
    generate_capacity_report,
)
from b2b_workflow_simulator.compliance import evaluate_compliance, generate_compliance_report
from b2b_workflow_simulator.examples import (
    customer_support_ticket_resolution,
    governance,
    invoice_processing,
    sales_lead_qualification,
)
from b2b_workflow_simulator.executive_report import (
    build_executive_assessment,
    generate_executive_report,
)
from b2b_workflow_simulator.export import diff_to_csv, diff_to_json, events_to_json, kpi_to_json
from b2b_workflow_simulator.html_report import (
    render_ai_adoption_html,
    render_capacity_html,
    render_compliance_html,
    render_diff_html,
    render_executive_html,
    render_monte_carlo_comparison_html,
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
from b2b_workflow_simulator.policy import evaluate_policies, generate_policy_report
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.portfolio import RANK_BY_OPTIONS, WorkflowPortfolio
from b2b_workflow_simulator.recommendation import (
    generate_recommendation_report,
    generate_recommendations,
)
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.report import generate_portfolio_report, generate_report
from b2b_workflow_simulator.risk import compute_risk, generate_risk_report
from b2b_workflow_simulator.sensitivity import (
    PARAMETERS,
    format_sensitivity_table,
    run_sensitivity_sweep,
)
from b2b_workflow_simulator.sensitivity_grid import (
    generate_sensitivity_grid_report,
    run_sensitivity_grid,
)
from b2b_workflow_simulator.simulation import ENGINES, SimulationRunner
from b2b_workflow_simulator.sla import evaluate_sla
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
        before_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes, engine=engine
    )
    after_result = SimulationRunner(seed=seed).run(
        after_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes, engine=engine
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
    num_cases: int,
    seed: int | None,
    implementation_cost: float | None,
    arrival_interval_minutes: float | None,
    engine: str = "simple",
) -> int:
    """Run both variants of a bundled example and print a full ROI report."""
    outcome = _run_before_after(example_name, num_cases, seed, arrival_interval_minutes, engine)
    if outcome is None:
        return 1
    _before_workflow, _after_workflow, before_result, after_result = outcome

    diff = compare_workflows(before_result.kpi, after_result.kpi, implementation_cost)
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
        default=200,
        help="Number of cases to simulate per variant (default: 200).",
    )
    compare_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42).",
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
        default="simple",
        help="Simulation engine: 'simple' (default) or 'discrete'.",
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
