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
An optional discrete-event engine (`engine="discrete"`) processes every
case through a single global, time-ordered event queue instead of one
case at a time, for a more general model of contention under heavy or
bursty load (see `docs/discrete_event_engine.md`); richer arrival
patterns -- uniform-random, batched, business-hour, and peak-hour --
are available via `ArrivalModel`. Capacity can also be modeled as an
**`ActorPool`** of several interchangeable `Worker`s with their own
cost, speed, reliability, and shift schedule, routed by least-loaded
scheduling instead of a single fixed actor (see `docs/team_capacity.md`).

On top of a simulation run, a **redesign diff engine** compares a
"before" and "after" `KPIResult` pair into a structured `RedesignDiff`
with an ROI and payback analysis, and a **report generator** renders
that diff as a plain-text report for non-technical stakeholders (see
`docs/redesign_analysis.md`).

Beyond a single workflow, a **`WorkflowPortfolio`** aggregates several
redesign diffs together, ranks them by transformation value, and rolls
up combined ROI, cost savings, and payback so a transformation program
covering multiple processes can be prioritized (see
`docs/portfolio_analysis.md`). A **sensitivity sweep engine** re-runs a
before/after pair while varying one assumption at a time (AI error
rate, AI cost, human hourly cost, arrival interval, implementation
cost) to find the break-even point where a redesign stops paying off
(see `docs/sensitivity_analysis.md`). Workflow definitions can be
persisted as JSON with lightweight structural validation, so they can
be authored, shared, or version-controlled outside of Python code (see
`docs/json_workflows.md`). Every report type -- redesign diffs,
portfolios, Monte Carlo analysis, sensitivity grids, and capacity plans
-- can also be rendered as a clean, self-contained HTML report for
sharing with stakeholders who won't run the CLI.

Beyond a single seeded run, a **Monte Carlo engine** re-simulates a
workflow (or a before/after pair) across many seeds and reports mean,
min, max, median, and P10/P90 for every KPI, ROI, and payback, with an
executive summary explaining how much confidence to place in the
result (see `docs/monte_carlo.md`). A **two-parameter sensitivity
grid** extends the single-parameter sweep to a full ROI matrix across
combinations of two assumptions moving together, classifying every
combination as a safe, negative-ROI, or operationally unstable
operating region (see `docs/advanced_sensitivity.md`). A **capacity
planning engine** turns simulated utilization into concrete staffing
recommendations -- overloaded, underutilized, or balanced against a
target -- and lets you simulate the effect of a specific hire before
committing to it (see `docs/capacity_planning.md`).

Beyond execution, the simulator reasons about governance and business
risk directly. A **`Node`** can require more than one actor at once (e.g.
Manager + Legal, or an AI agent plus a human reviewer), with the resulting
coordination delay tracked on `KPIResult` (see `docs/team_capacity.md`). A
**business policy engine** and a **compliance engine** check a workflow's
structure against attachable governance rules -- approval gates, routing
and escalation constraints, retry safety, business hours, mandatory human
review, separation of duties, GDPR-style consent gates, financial approval
chains, mandatory documentation, and record retention -- reporting
violations, a compliance score, and audit findings (see
`docs/policy_engine.md`, `docs/compliance.md`). An **SLA engine** checks
completion, response, and escalation deadlines against a simulation's
actual event log, tracking attainment, breaches, and estimated financial
penalties (see `docs/sla_modeling.md`). An **organizational risk engine**
scores a workflow across six categories -- operational, compliance, AI
failure, staffing, process complexity, and single point of failure -- with
an explainable list of risk factors behind every score (see
`docs/risk_engine.md`). A **recommendation engine** turns all of the above
into a prioritized, reasoned list of actionable suggestions -- automate
this task, keep human review, adjust staffing, merge or split activities,
redesign an escalation path -- each with affected KPIs, an expected
benefit, and a confidence level (see `docs/recommendation_engine.md`). An
**AI adoption assessment** scores automation readiness, AI maturity, human
dependency, governance, explainability, and rollout complexity into a
pilot/phased-rollout/full-deployment recommendation, and an **executive
assessment report** combines every one of these analyses -- KPI summary,
ROI, SLA performance, compliance, policy violations, organizational risk,
recommendations, and AI adoption -- into a single plain-text or HTML
document (see `docs/ai_adoption.md`).

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

### Customer support ticket resolution

```
Ticket Intake -> Triage -> Response Drafting -> Follow-Up
                    \\              \\-> Low-Confidence Response
                     \\-> Escalation -> Follow-Up
                     \\-> Wrong Classification         \\-> Delayed Escalation
                     \\-> Missing Customer Context
```

- **Before**: a Support Agent triages, drafts responses to, and follows
  up on every ticket; a Specialist handles escalations.
- **After**: AI agents triage tickets and draft responses end to end; a
  new Support Reviewer role approves or corrects AI output on complex
  or low-confidence cases; the Specialist is reserved purely for
  genuine escalations.

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

# Run several bundled examples together and print a per-workflow summary.
b2b-simulator run-portfolio sales-lead-qualification invoice-processing customer-support-ticket-resolution

# Full portfolio report: ranking, aggregate ROI/payback, risks, rollout order.
b2b-simulator compare-portfolio sales-lead-qualification invoice-processing --implementation-cost 5000

# Sweep an assumption and find the break-even point.
b2b-simulator sensitivity-example invoice-processing --parameter ai_cost_per_execution --values 0,5,10,20

# Save/load a workflow definition as JSON.
b2b-simulator save-example invoice-processing --output-dir workflows
b2b-simulator load-example workflows/invoice-processing-after.json

# Write a static, shareable HTML redesign report.
b2b-simulator html-report-example invoice-processing --output report.html

# Run with the discrete-event engine instead of the default sequential one.
b2b-simulator run-example sales-lead-qualification --engine discrete

# Monte Carlo: re-simulate across many seeds and report variability, ROI, and payback.
b2b-simulator monte-carlo-example invoice-processing --seeds 1,2,3,4,5 --implementation-cost 8000
b2b-simulator monte-carlo-portfolio sales-lead-qualification invoice-processing --seeds 1,2,3,4,5

# Two-parameter sensitivity grid: ROI matrix and safe/negative/unstable regions.
b2b-simulator sensitivity-grid-example invoice-processing \
  --x-parameter ai_error_rate --x-values 0,0.1,0.2,0.3 \
  --y-parameter ai_cost_per_execution --y-values 0,5,10,20

# Capacity planning: staffing recommendations and raw utilization figures.
b2b-simulator capacity-analysis invoice-processing --arrival-interval 10
b2b-simulator team-utilization invoice-processing --arrival-interval 10

# Governance: policy and compliance checks against workflow structure.
b2b-simulator policy-analysis invoice-processing --variant after
b2b-simulator compliance-analysis invoice-processing --variant after --html-output compliance.html

# Organizational risk: category scores and explainable risk factors.
b2b-simulator risk-analysis invoice-processing --variant after --cases 300

# AI adoption readiness: pilot / phased rollout / full deployment recommendation.
b2b-simulator readiness-analysis invoice-processing --variant after --cases 300

# Actionable, reasoned redesign recommendations.
b2b-simulator recommend-redesign invoice-processing --variant after --cases 300

# Executive assessment report: KPI, ROI, SLA, compliance, policy, risk,
# recommendations, and AI adoption combined into one report.
b2b-simulator executive-report invoice-processing --cases 300 --implementation-cost 8000 --html-output executive.html
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
    primitives/          Node, Edge, Actor, HumanActor, AIAgentActor, Task, Event,
                         DurationModel, Worker, Shift
    workflow.py           Workflow graph model with validation
    workflow_io.py          JSON persistence + stdlib schema validation for workflows
    capacity.py               ActorScheduler: queueing and daily capacity limits
    arrivals.py                 ArrivalModel: non-uniform case arrival patterns
    pool.py                       ActorPool + PoolScheduler: team-based capacity
    queueing.py                     Queue depth, growth/collapse, throughput analysis
    discrete_event.py                 DiscreteEventEngine: global priority-queue simulation
    kpi.py                     KPIResult aggregation object
    simulation.py                SimulationRunner (dispatches to the discrete-event engine)
    redesign.py                    Redesign diff engine (before/after comparison, ROI, payback)
    portfolio.py                     WorkflowPortfolio: multi-workflow aggregation and ranking
    sensitivity.py                     Sweep engine and break-even detection
    sensitivity_grid.py                  Two-parameter sensitivity grids and region classification
    monte_carlo.py                         Repeated seeded runs and percentile statistics
    capacity_planning.py                     Staffing recommendations and hiring simulation
    multi_resource.py                          Synchronized scheduling for multi-actor tasks
    policy.py                                    Business policy engine and violation tracking
    compliance.py                                  Compliance requirements and audit findings
    sla.py                                           SLA deadline tracking and breach analysis
    risk.py                                            Organizational risk scoring engine
    recommendation.py                                    Actionable, reasoned recommendations
    ai_adoption.py                                         AI adoption readiness assessment
    executive_report.py                                      Combined executive assessment
    report.py                            Plain-text report generators for every analysis type
    html_report.py                         Static HTML report renderer
    export.py                                JSON/CSV export for events, KPIs, and comparisons
    examples/                                   Bundled example workflows + sample JSON
                                                 definitions + governance.py (policy/compliance/SLA)
    cli.py                                        Command-line entry point
tests/                    Unit tests for every module above
docs/                     Architecture, capacity modeling, redesign/portfolio/sensitivity
                          analysis, JSON workflows, discrete-event engine, team capacity,
                          Monte Carlo, advanced sensitivity, capacity planning, policy
                          engine, compliance, SLA modeling, risk engine, recommendation
                          engine, and AI adoption
```

## Status

Phase 1 established the core domain model, a working simulation runner,
and a single business example end to end. Phase 2 added capacity-aware
queueing, realistic duration variance, a structured redesign diff engine
with ROI/payback analysis, plain-text reporting, JSON/CSV export, and a
second business example (invoice processing). Phase 3 added a third
business example (customer support ticket resolution), a workflow
portfolio model for evaluating multiple redesigns together, a
sensitivity/break-even sweep engine, JSON persistence for workflow
definitions, and static HTML reports for both single-workflow and
portfolio results. Phase 4 turns the simulator into an enterprise-grade
process modeling engine: an optional discrete-event execution engine
with a global priority queue; richer arrival patterns (uniform,
batched, business-hour, peak-hour); team-based capacity via
`ActorPool`/`Worker`/`Shift` with least-loaded routing and overtime;
Monte Carlo analysis across many seeds with percentile statistics;
two-parameter sensitivity grids with safe/negative/unstable region
classification; and a capacity planning engine for staffing
recommendations and hiring simulations. Phase 5 transforms the simulator
from a workflow simulator into a decision-support platform: multi-resource
tasks requiring several actors at once; a business policy engine and a
compliance engine for governance rules and regulatory/audit requirements;
an SLA engine tracking deadline attainment, breaches, and penalties; an
organizational risk engine with explainable category scores; a
recommendation engine generating actionable, reasoned suggestions; an AI
adoption assessment scoring rollout readiness; and an executive assessment
report combining every analysis into one document.

## License

MIT
