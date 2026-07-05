"""Command-line interface for running bundled example simulations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from b2b_workflow_simulator.examples import (
    customer_support_ticket_resolution,
    invoice_processing,
    sales_lead_qualification,
)
from b2b_workflow_simulator.export import diff_to_csv, diff_to_json, events_to_json, kpi_to_json
from b2b_workflow_simulator.html_report import render_portfolio_html
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.portfolio import RANK_BY_OPTIONS, WorkflowPortfolio
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.report import generate_portfolio_report, generate_report
from b2b_workflow_simulator.sensitivity import (
    PARAMETERS,
    format_sensitivity_table,
    run_sensitivity_sweep,
)
from b2b_workflow_simulator.simulation import SimulationRunner

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
        before_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
    )
    after_result = SimulationRunner(seed=seed).run(
        after_workflow, num_cases, arrival_interval_minutes=arrival_interval_minutes
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


def run_example(example_name: str, num_cases: int, seed: int | None) -> int:
    """Run the before/after variants of a bundled example and print a KPI comparison."""
    outcome = _run_before_after(example_name, num_cases, seed)
    if outcome is None:
        return 1
    before_workflow, after_workflow, before_result, after_result = outcome

    print(f"Example: {example_name}")
    print(f"Cases per variant: {num_cases}")
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
) -> int:
    """Run both variants of a bundled example and print a full ROI report."""
    outcome = _run_before_after(example_name, num_cases, seed, arrival_interval_minutes)
    if outcome is None:
        return 1
    _before_workflow, _after_workflow, before_result, after_result = outcome

    diff = compare_workflows(before_result.kpi, after_result.kpi, implementation_cost)
    print(generate_report(diff))
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-example":
        return run_example(args.name, args.cases, args.seed)

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
            args.name, args.cases, args.seed, args.implementation_cost, args.arrival_interval
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
