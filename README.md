# B2B Agentic Workflow Simulator

An organizational digital twin for AI transformation. This project lets
corporates, consultants, founders, and operations leaders simulate a
business workflow **before** and **after** introducing AI agents, so the
impact on cost, cycle time, capacity, quality, and failure modes can be
understood before anything is built or deployed in production.

This is not a toy agent demo. It is a modeling tool for answering a
concrete question: *if we hand parts of this process to AI agents, does
the workflow get better, break, or just change shape?*

## Why this exists

Most AI transformation projects skip straight to building an agent and
hoping it helps. This simulator inverts that: model the workflow as a
graph of stages, actors, and handoffs first, run it under both the
current ("before") and redesigned ("after") staffing models, and compare
the resulting KPIs. That turns a vague pitch ("AI will help sales ops")
into a specific, falsifiable claim, backed by a structured ROI report:
completion rate, cost per case, cycle time, wait time, actor utilization,
bottlenecks, escalation rate, and payback period.

## Core concepts

The simulator is built from a small set of primitives:

- **Node** — a stage of work in a process (e.g. "Discovery Call"), with
  an optional `DurationModel` describing how its duration varies.
- **Edge** — a directed, probability-weighted transition between nodes,
  used to model branching (e.g. qualified vs. disqualified leads).
- **HumanActor** — a person assigned to a node, modeled with an hourly
  cost, a speed multiplier, an error rate, and daily working capacity.
- **AIAgentActor** — an AI agent assigned to a node, modeled with a
  per-execution cost, a speed multiplier, an error rate, and an
  escalation rate (how often it defers to a human).
- **Workflow** — a validated graph of nodes, edges, and actors; the
  blueprint that gets simulated.
- **Task** / **Event** — the runtime record of one stage being executed
  for one case, and the immutable audit trail the simulation produces.
- **KPIResult** — aggregated metrics (cost, cycle time, wait time,
  completion/failure/escalation rate, actor utilization, bottleneck
  stages) computed from a simulation run.

A `SimulationRunner` takes a `Workflow` and a number of cases, runs each
case through the graph with a seeded random number generator, and
returns a `KPIResult`. Because the same seed produces the same outcome,
"before" and "after" variants can be compared fairly. Passing an arrival
interval switches on capacity-aware simulation: actors become shared,
finite resources that queue work and can be overloaded, exactly like a
real team or a rate-limited AI service (see `docs/capacity_modeling.md`).

On top of a simulation run, a **redesign diff engine** compares a
"before" and "after" `KPIResult` pair into a structured `RedesignDiff`
with an ROI and payback analysis, and a **report generator** renders
that diff as a plain-text report for non-technical stakeholders (see
`docs/redesign_analysis.md`).

## Bundled examples

### Sales lead qualification

```
Lead Intake -> Initial Research -> Discovery Call -> Proposal Draft -> Qualified Handoff
                               \\-> Disqualified                  \\-> Disqualified
```

- **Before**: every stage is staffed by an SDR or Account Executive.
- **After**: Lead Intake, Initial Research, and Proposal Draft are handled
  by AI agents; the Discovery Call stays human because it depends on
  judgment and rapport that the simulator does not attempt to automate.

### Invoice processing (accounts payable)

```
Invoice Intake -> Validation -> Approval -> ERP Entry -> Payment Scheduling
                         \\           \\-> Approval Delay
                          \\-> Missing PO / Mismatched Amount / Vendor Data Issue
```

- **Before**: an AP Clerk and a Controller manually intake, validate,
  approve, and post every invoice.
- **After**: AI agents handle straight-through intake, validation,
  approval, and ERP entry; every exception (missing PO, mismatched
  amount, vendor data issue, or a stalled approval) is routed to a human
  AP Specialist, keeping a human firmly in the loop for anything the
  agents cannot confidently resolve.

## Command-line usage

```bash
# Print a before/after KPI table for a bundled example.
b2b-simulator run-example sales-lead-qualification --cases 300 --seed 7

# Print a full ROI report: executive summary, KPI deltas, bottlenecks,
# actor utilization, risks, and a recommendation.
b2b-simulator compare-example invoice-processing --cases 300 --implementation-cost 8000

# Same as above, but with capacity-aware queueing: cases arrive every
# 15 minutes and compete for actor time.
b2b-simulator compare-example sales-lead-qualification --arrival-interval 15

# Export event logs, KPI summaries, and the comparison to disk.
b2b-simulator export-example invoice-processing --format json --output-dir exports
```

Example `run-example` output:

```
Metric                    Before       After
--------------------------------------------
Cases simulated              300         300
Completed                    222         261
Failed                         78          39
Completion rate            74.0%       87.0%
Total cost            $14,753.75   $6,281.70
Avg cost / case           $49.18      $20.94
Avg cycle time (min)        57.5        23.5
```

## Installation

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests and checks

```bash
pytest
ruff check .
python -m build
```

## Project layout

```
src/b2b_workflow_simulator/
    primitives/          Node, Edge, Actor, HumanActor, AIAgentActor, Task, Event, DurationModel
    workflow.py           Workflow graph model with validation
    capacity.py            ActorScheduler: queueing and daily capacity limits
    kpi.py                 KPIResult aggregation object
    simulation.py           SimulationRunner
    redesign.py              Redesign diff engine (before/after comparison, ROI, payback)
    report.py                 Plain-text ROI report generator
    export.py                  JSON/CSV export for events, KPIs, and comparisons
    examples/                   Bundled example workflows
    cli.py                       Command-line entry point
tests/                    Unit tests for every module above
docs/                     Architecture, capacity modeling, and redesign analysis documentation
```

## Status

Phase 1 established the core domain model, a working simulation runner,
and a single business example end to end. Phase 2 adds capacity-aware
queueing, realistic duration variance, a structured redesign diff engine
with ROI/payback analysis, plain-text reporting, JSON/CSV export, and a
second business example (invoice processing).

## License

MIT
