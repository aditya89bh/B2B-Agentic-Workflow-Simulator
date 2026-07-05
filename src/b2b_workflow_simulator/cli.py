"""Command-line interface for running bundled example simulations."""

from __future__ import annotations

import argparse
import sys

from b2b_workflow_simulator.examples import invoice_processing, sales_lead_qualification
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.simulation import SimulationRunner

EXAMPLES = {
    "sales-lead-qualification": (
        sales_lead_qualification.build_before_workflow,
        sales_lead_qualification.build_after_workflow,
    ),
    "invoice-processing": (
        invoice_processing.build_before_workflow,
        invoice_processing.build_after_workflow,
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


def run_example(example_name: str, num_cases: int, seed: int | None) -> int:
    """Run the before/after variants of a bundled example and print a KPI comparison."""
    if example_name not in EXAMPLES:
        available = ", ".join(sorted(EXAMPLES))
        print(f"Unknown example '{example_name}'. Available examples: {available}", file=sys.stderr)
        return 1

    build_before, build_after = EXAMPLES[example_name]
    before_workflow = build_before()
    after_workflow = build_after()

    before_result = SimulationRunner(seed=seed).run(before_workflow, num_cases)
    after_result = SimulationRunner(seed=seed).run(after_workflow, num_cases)

    print(f"Example: {example_name}")
    print(f"Cases per variant: {num_cases}")
    print()
    print(f"Before: {before_workflow.name}")
    print(f"After:  {after_workflow.name}")
    print()
    _print_kpi_table(before_result.kpi, after_result.kpi)
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-example":
        return run_example(args.name, args.cases, args.seed)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
