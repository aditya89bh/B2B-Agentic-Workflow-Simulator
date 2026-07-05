# Changelog

## Phase 2 - Redesign Analysis and Capacity Modeling

Added the tooling needed to turn a simulation run into a business case:
capacity-aware queueing, realistic duration variance, a structured
redesign comparison with ROI/payback, plain-text reporting, export
support, and a second business example.

- Capacity modeling: `ActorScheduler` models actors as single-server
  queues with daily capacity limits (`available_hours_per_day` on every
  actor); `SimulationRunner.run()` accepts an optional
  `arrival_interval_minutes` to enable queueing, wait time tracking, and
  per-actor utilization.
- Duration variance: `DurationModel` primitive supports fixed, uniform,
  and triangular sampling, fully seeded and reproducible; integrated
  into `Node` and the simulation runner.
- Redesign diff engine: `compare_workflows()` in `redesign.py` produces a
  structured `RedesignDiff` (completion rate, failure rate, cost,
  cost per case, cycle time, wait time, escalation rate, bottlenecks,
  utilization) plus an `ROIAnalysis` with payback logic.
- ROI report: `generate_report()` in `report.py` renders a `RedesignDiff`
  as a plain-text report with an executive summary, KPI table,
  bottlenecks, utilization, risks, and a recommendation.
- Export support: `export.py` serializes event logs, `KPIResult`
  summaries, and `RedesignDiff` comparisons to JSON, and comparisons to
  CSV.
- Second bundled example: invoice processing (accounts payable), with
  realistic exception paths (missing PO, mismatched amount, vendor data
  issue, approval delay) and an AI-augmented redesign that keeps a human
  AP Specialist in the loop for every exception.
- CLI: `run-example` and `compare-example` now support both bundled
  examples; added `compare-example` (full ROI report, with
  `--implementation-cost` and `--arrival-interval`) and `export-example`
  (`--format json|csv`).
- Unit test coverage for capacity constraints, queueing, wait time,
  utilization, duration distributions, the redesign diff engine, the ROI
  report, JSON/CSV export, the invoice processing example, and the new
  CLI commands.
- Documentation: updated README, architecture, and getting-started docs;
  added `docs/redesign_analysis.md` and `docs/capacity_modeling.md`.

## Phase 1 - Foundation

Established the core domain model and a working end-to-end simulation.

- Core primitives: `Node`, `Edge`, `Actor`, `HumanActor`, `AIAgentActor`,
  `Task`, `Event`.
- `Workflow` graph model with structural validation.
- `KPIResult` aggregation object with derived business metrics.
- `SimulationRunner`: seeded, reproducible execution engine.
- Bundled example: sales lead qualification, before (human-only) and
  after (AI-augmented) variants.
- `b2b-simulator` CLI with a `run-example` command that prints a
  before/after KPI comparison.
- Unit test coverage for every primitive, the workflow model, the
  simulation runner, the example workflow, and the CLI.
- Project scaffolding: `pyproject.toml`, README, architecture and
  getting-started docs, MIT license.
