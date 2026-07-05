# Getting Started

## Installation

```bash
git clone <repository-url>
cd B2B-Agentic-Workflow-Simulator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run a bundled example

```bash
b2b-simulator run-example sales-lead-qualification --cases 300 --seed 7
b2b-simulator run-example invoice-processing --cases 300 --seed 7
b2b-simulator run-example customer-support-ticket-resolution --cases 300 --seed 7
```

Each command runs the "before" and "after" variants of the named example
over 300 simulated cases each, using a fixed random seed for reproducible
output, and prints a side-by-side KPI comparison.

## Get a full ROI report

```bash
b2b-simulator compare-example invoice-processing --cases 300 --implementation-cost 8000
```

This prints a plain-text report with an executive summary, a full KPI
delta table, bottleneck stages, actor utilization, risks, and a
recommendation. Add `--implementation-cost` to include payback analysis,
and `--arrival-interval <minutes>` to enable capacity-aware queueing:

```bash
b2b-simulator compare-example sales-lead-qualification --arrival-interval 15
```

With an arrival interval set, cases compete for actor time, so the report
includes real wait times and per-actor utilization instead of zeros.

## Export results

```bash
b2b-simulator export-example invoice-processing --format json --output-dir exports
b2b-simulator export-example invoice-processing --format csv --output-dir exports
```

`--format json` writes event logs, KPI summaries, and the before/after
comparison as JSON files. `--format csv` writes a single comparison CSV
with one row per headline metric, convenient for spreadsheets.

## Evaluate several workflows as a portfolio

```bash
b2b-simulator run-portfolio sales-lead-qualification invoice-processing customer-support-ticket-resolution --cases 300
b2b-simulator compare-portfolio sales-lead-qualification invoice-processing --implementation-cost 5000 --rank-by roi_percentage
```

`run-portfolio` prints a condensed before/after cost and ROI summary for
each named example. `compare-portfolio` prints a full report: an
executive summary, a workflow ranking (by total cost savings, ROI
percentage, or per-case savings via `--rank-by`), aggregate ROI and
payback, consolidated risks, and a recommended rollout order. Add
`--html-output report.html` to also write a shareable HTML version. See
`docs/portfolio_analysis.md`.

## Find the break-even point for an assumption

```bash
b2b-simulator sensitivity-example invoice-processing --parameter ai_cost_per_execution --values 0,5,10,20,40
```

This re-simulates the named example once per value, holding everything
else fixed, and prints a table of cost savings and ROI at each value
plus the range where the redesign's cost savings cross from positive to
negative. Supported `--parameter` values: `ai_error_rate`,
`ai_cost_per_execution`, `human_hourly_cost`, `arrival_interval`, and
`implementation_cost`. See `docs/sensitivity_analysis.md`.

## Save and load workflow definitions as JSON

```bash
b2b-simulator save-example invoice-processing --output-dir workflows
b2b-simulator load-example workflows/invoice-processing-after.json --cases 200
```

`save-example` writes the before/after `Workflow` definitions for a
bundled example as JSON. `load-example` reads any workflow JSON file
(validating its structure first) and prints a simulated KPI summary.
Every bundled example also ships a ready-made JSON definition under
`src/b2b_workflow_simulator/examples/data/`. See `docs/json_workflows.md`.

## Run with the discrete-event engine

```bash
b2b-simulator run-example sales-lead-qualification --engine discrete
b2b-simulator compare-example sales-lead-qualification --engine discrete --arrival-interval 15
```

`--engine discrete` switches from the default sequential engine to a
global, time-ordered event queue, giving a more general model of
contention when many cases are simultaneously in flight (see
`docs/discrete_event_engine.md`). Results match the default engine
under light load and can diverge slightly under heavy, bursty
contention -- both are deterministic and internally consistent for a
given seed.

## Understand outcome variability with Monte Carlo analysis

```bash
b2b-simulator monte-carlo-example invoice-processing --cases 300 --seeds 1,2,3,4,5 --implementation-cost 8000
b2b-simulator monte-carlo-portfolio sales-lead-qualification invoice-processing --cases 300 --seeds 1,2,3,4,5
```

A single seeded run shows one plausible outcome. `monte-carlo-example`
re-runs the named example across every listed seed and reports mean,
min, max, median, and P10/P90 for every KPI plus ROI and payback, with
an executive summary explaining how much the outcome actually varies.
`monte-carlo-portfolio` runs the same analysis across several examples
and prints a condensed summary row per workflow. Add `--html-output` to
`monte-carlo-example` for a shareable HTML version. See
`docs/monte_carlo.md`.

## Sweep two assumptions at once

```bash
b2b-simulator sensitivity-grid-example invoice-processing \
  --x-parameter ai_error_rate --x-values 0,0.1,0.2,0.3 \
  --y-parameter ai_cost_per_execution --y-values 0,5,10,20 \
  --html-output grid.html
```

Prints an ROI matrix across every combination of the two swept
parameters, plus a breakdown of how many combinations are in the safe,
negative-ROI, or operationally unstable region. See
`docs/advanced_sensitivity.md`.

## Model a team instead of a single actor

Build an `ActorPool` of `Worker`s (each with their own cost, speed,
error rate, and optional `Shift` schedule) and reference it from a
`Node` exactly like any other actor -- see `docs/team_capacity.md` for
the full model. Once a workflow uses a pool, check its staffing level:

```bash
b2b-simulator team-utilization invoice-processing --arrival-interval 10
b2b-simulator capacity-analysis invoice-processing --arrival-interval 10 --html-output capacity.html
```

`team-utilization` prints raw actor/pool/worker utilization figures.
`capacity-analysis` goes further, classifying each resource as
overloaded, underutilized, or balanced against a target utilization and
recommending a headcount change. See `docs/capacity_planning.md`.

## Generate a shareable HTML report

```bash
b2b-simulator html-report-example invoice-processing --implementation-cost 8000 --output report.html
```

Writes a single, self-contained HTML file (inline CSS, no external
assets or frontend framework) with the same KPI table, bottlenecks,
utilization, risks, and recommendation as `compare-example`'s
plain-text report, suitable for emailing to a stakeholder who won't run
the CLI.

## Assess governance, risk, and AI readiness

Beyond simulating what a workflow costs and how long it takes, the
simulator can reason about whether a workflow is *allowed* to run the way
it does, how risky it is, and whether it is ready for more AI:

```bash
# Governance: does the workflow satisfy its attached business policies
# and regulatory/compliance requirements?
b2b-simulator policy-analysis invoice-processing --variant after
b2b-simulator compliance-analysis invoice-processing --variant after

# Organizational risk: operational, compliance, AI failure, staffing,
# process complexity, and single-point-of-failure scores, with
# explainable factors behind each one.
b2b-simulator risk-analysis invoice-processing --variant after --cases 300

# AI adoption readiness: automation readiness, AI maturity, human
# dependency, governance, explainability, and rollout complexity,
# rolled up into a pilot/phased-rollout/full-deployment recommendation.
b2b-simulator readiness-analysis invoice-processing --variant after --cases 300

# Actionable recommendations: automate this task, keep human review,
# adjust staffing, merge/split activities, and more -- each with
# reasoning, affected KPIs, expected benefit, and a confidence level.
b2b-simulator recommend-redesign invoice-processing --variant after --cases 300

# Executive assessment: KPI summary, ROI, SLA performance, compliance,
# policy violations, organizational risk, recommendations, and AI
# adoption, combined into one report (plain text or HTML).
b2b-simulator executive-report invoice-processing --cases 300 --implementation-cost 8000 --html-output executive.html
```

`policy-analysis`, `compliance-analysis`, `risk-analysis`, and
`readiness-analysis` each support `--variant before|after` (default
`after`) so a governance or risk regression introduced by a redesign can
be checked directly against the baseline. `executive-report` always
compares both variants for its ROI section, evaluated against the
bundled example's attached governance definitions (see
`src/b2b_workflow_simulator/examples/governance.py`). See
`docs/policy_engine.md`, `docs/compliance.md`, `docs/risk_engine.md`,
`docs/recommendation_engine.md`, `docs/ai_adoption.md`, and
`docs/sla_modeling.md`.

## Define your own workflow

A workflow is built by registering actors, then nodes (each referencing
an actor), then edges (each referencing two nodes):

```python
from b2b_workflow_simulator.primitives import AIAgentActor, DurationModel, Edge, HumanActor, Node
from b2b_workflow_simulator.simulation import SimulationRunner
from b2b_workflow_simulator.workflow import Workflow

workflow = Workflow(
    workflow_id="support-ticket-triage",
    name="Support Ticket Triage",
    entry_node_id="triage",
)

workflow.add_actor(
    AIAgentActor(
        actor_id="triage_bot",
        name="Triage Agent",
        cost_per_execution=0.10,
        speed_multiplier=0.05,
        error_rate=0.03,
        escalation_rate=0.15,
    )
)
workflow.add_actor(HumanActor(actor_id="agent", name="Support Agent", hourly_cost=40.0))

workflow.add_node(Node("triage", "Triage", actor_id="triage_bot", base_duration_minutes=5))
workflow.add_node(
    Node("resolve", "Resolve Ticket", actor_id="agent", base_duration_minutes=20, is_terminal=True)
)
workflow.add_edge(Edge("triage", "resolve"))

workflow.validate()

result = SimulationRunner(seed=42).run(workflow, num_cases=500)
print(result.kpi)
```

Add `duration_model=DurationModel(kind="triangular", minimum=3, mode=5, maximum=12)`
to a `Node` to make its duration vary realistically instead of always
taking exactly `base_duration_minutes`. See `docs/capacity_modeling.md`
for how to model queueing and daily capacity limits.

## Compare before and after

To evaluate a redesign, build two `Workflow` instances that share the
same node IDs but assign different actors (or add/remove nodes and
edges), then run both with the same seed and case count and compare the
resulting `KPIResult` objects with the redesign diff engine:

```python
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.report import generate_report

before_result = SimulationRunner(seed=42).run(before_workflow, num_cases=500)
after_result = SimulationRunner(seed=42).run(after_workflow, num_cases=500)

diff = compare_workflows(before_result.kpi, after_result.kpi, implementation_cost=10000.0)
print(generate_report(diff))
```

See `src/b2b_workflow_simulator/examples/` for complete before/after
pairs, and `docs/redesign_analysis.md` for what each part of the report
means.

## Running the test suite

```bash
pytest
ruff check .
python -m build
```
