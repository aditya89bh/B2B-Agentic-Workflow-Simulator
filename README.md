# B2B Agentic Workflow Simulator

An organizational digital twin for AI transformation. This project lets
corporates, consultants, founders, and operations leaders simulate a
business workflow **before** and **after** introducing AI agents, so the
impact on cost, cycle time, quality, and failure modes can be understood
before anything is built or deployed in production.

This is not a toy agent demo. It is a modeling tool for answering a
concrete question: *if we hand parts of this process to AI agents, does
the workflow get better, break, or just change shape?*

## Why this exists

Most AI transformation projects skip straight to building an agent and
hoping it helps. This simulator inverts that: model the workflow as a
graph of stages, actors, and handoffs first, run it under both the
current ("before") and redesigned ("after") staffing models, and compare
the resulting KPIs. That turns a vague pitch ("AI will help sales ops")
into a specific, falsifiable claim ("this redesign cuts average cost per
lead by 55% and cycle time by 60%, at the cost of a 3% higher escalation
rate on research tasks").

## Core concepts

The simulator is built from a small set of primitives:

- **Node** — a stage of work in a process (e.g. "Discovery Call").
- **Edge** — a directed, probability-weighted transition between nodes,
  used to model branching (e.g. qualified vs. disqualified leads).
- **HumanActor** — a person assigned to a node, modeled with an hourly
  cost, a speed multiplier, and an error rate.
- **AIAgentActor** — an AI agent assigned to a node, modeled with a
  per-execution cost, a speed multiplier, an error rate, and an
  escalation rate (how often it defers to a human).
- **Workflow** — a validated graph of nodes, edges, and actors; the
  blueprint that gets simulated.
- **Task** / **Event** — the runtime record of one stage being executed
  for one case, and the immutable audit trail the simulation produces.
- **KPIResult** — aggregated metrics (cost, cycle time, completion rate,
  failure rate, bottleneck stages) computed from a simulation run.

A `SimulationRunner` takes a `Workflow` and a number of cases, runs each
case through the graph with a seeded random number generator, and
returns a `KPIResult`. Because the same seed produces the same outcome,
"before" and "after" variants can be compared fairly.

## Example: sales lead qualification

The bundled example models a B2B sales lead qualification process:

```
Lead Intake -> Initial Research -> Discovery Call -> Proposal Draft -> Qualified Handoff
                               \\-> Disqualified                  \\-> Disqualified
```

- **Before**: every stage is staffed by an SDR or Account Executive.
- **After**: Lead Intake, Initial Research, and Proposal Draft are handled
  by AI agents; the Discovery Call stays human because it depends on
  judgment and rapport that the simulator does not attempt to automate.

Run it from the command line:

```bash
b2b-simulator run-example sales-lead-qualification --cases 300 --seed 7
```

Example output:

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
    primitives/        Node, Edge, Actor, HumanActor, AIAgentActor, Task, Event
    workflow.py         Workflow graph model with validation
    kpi.py              KPIResult aggregation object
    simulation.py        SimulationRunner
    examples/            Bundled example workflows
    cli.py               Command-line entry point
tests/                  Unit tests for every module above
docs/                   Architecture and usage documentation
```

## Status

This repository is in early, active development. Phase 1 establishes the
core domain model, a working simulation runner, and a single business
example end to end. Later phases will add richer redesign tooling,
staffing/capacity modeling, and reporting.

## License

MIT
