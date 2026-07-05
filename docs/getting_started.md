# Getting Started

## Installation

```bash
git clone <repository-url>
cd B2B-Agentic-Workflow-Simulator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run the bundled example

```bash
b2b-simulator run-example sales-lead-qualification --cases 300 --seed 7
```

This runs the "before" (human-only) and "after" (AI-augmented) variants
of the sales lead qualification workflow over 300 simulated leads each,
using a fixed random seed for reproducible output, and prints a
side-by-side KPI comparison.

## Define your own workflow

A workflow is built by registering actors, then nodes (each referencing
an actor), then edges (each referencing two nodes):

```python
from b2b_workflow_simulator.primitives import AIAgentActor, Edge, HumanActor, Node
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

## Compare before and after

To evaluate a redesign, build two `Workflow` instances that share the
same node IDs but assign different actors (or add/remove nodes and
edges), then run both with the same seed and case count and compare the
resulting `KPIResult` objects. See
`src/b2b_workflow_simulator/examples/sales_lead_qualification.py` for a
complete before/after pair, and `src/b2b_workflow_simulator/cli.py` for
how the comparison table is produced.

## Running the test suite

```bash
pytest
ruff check .
python -m build
```
