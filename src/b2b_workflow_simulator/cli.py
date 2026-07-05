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
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.report import generate_report
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

    if args.command == "compare-example":
        return compare_example(
            args.name, args.cases, args.seed, args.implementation_cost, args.arrival_interval
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
