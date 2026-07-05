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
