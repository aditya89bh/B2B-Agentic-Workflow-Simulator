# Changelog

## Phase 3 - Portfolios, Sensitivity Analysis, and Persistence

Added the tooling needed to run this beyond a single workflow: comparing
several redesigns as a program, testing how sensitive an ROI case is to
its underlying assumptions, persisting workflow definitions outside of
Python, and sharing results as static HTML.

- Portfolio model: `WorkflowPortfolio` in `portfolio.py` aggregates
  several before/after workflow comparisons, ranks them by total cost
  savings, ROI percentage, or per-case savings, and rolls up aggregate
  before/after cost, cost savings, wait-time savings, and a combined
  payback period.
- Portfolio report: `generate_portfolio_report()` in `report.py` renders
  a plain-text report with an executive summary, workflow ranking,
  aggregate ROI/payback, consolidated risks across every workflow, and a
  recommended rollout order.
- Sensitivity analysis: `run_sensitivity_sweep()` in `sensitivity.py`
  sweeps AI error rate, AI cost per execution, human hourly cost,
  arrival interval, or implementation cost across a before/after pair,
  fully seeded and reproducible; `SensitivityResult.break_even_range()`
  identifies the parameter range where cost savings cross from positive
  to negative.
- Third bundled example: customer support ticket resolution, with
  realistic failure paths (wrong classification, missing customer
  context, low-confidence response, delayed escalation) and an
  AI-augmented redesign that introduces a Support Reviewer role for
  complex cases while reserving the Specialist for genuine escalations.
- Persistent workflow definitions: `workflow_io.py` adds
  `save_workflow()`/`load_workflow()` plus stdlib-only structural
  validation (`validate_workflow_dict()`, no schema library dependency);
  every bundled example ships a matching JSON definition under
  `examples/data/`.
- HTML report renderer: `html_report.py` renders a `RedesignDiff` or
  `WorkflowPortfolio` as a single, self-contained HTML document with
  inline CSS and fully escaped interpolated text -- no frontend
  framework, no external assets.
- CLI: added `run-portfolio`, `compare-portfolio` (with `--rank-by` and
  optional `--html-output`), `sensitivity-example`, `save-example`,
  `load-example`, and `html-report-example`; registered the customer
  support example alongside the existing two.
- Unit test coverage for the portfolio model and report, sensitivity
  sweeps and break-even detection, the customer support example, JSON
  load/save and validation errors, HTML report escaping, and every new
  CLI command.
- Documentation: updated README, architecture, and getting-started
  docs; added `docs/portfolio_analysis.md`, `docs/sensitivity_analysis.md`,
  and `docs/json_workflows.md`.

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
