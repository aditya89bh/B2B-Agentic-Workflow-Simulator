# Concepts

## The simulation model

A workflow is a directed graph where each **node** is a stage of work and each **edge** is a probability-weighted transition to the next stage.  Each node is assigned an **actor** (human or AI agent) with a cost, speed, and error rate.

The simulator runs `num_cases` cases through this graph, tracking:

- Whether each case completes, fails, or escalates
- How long each stage takes
- How much each stage costs
- Where cases queue when actors are busy (capacity-aware mode)

## Key concepts

### Workflow
A validated directed graph of nodes, edges, and actors.  Every workflow has:
- An entry node where every case begins
- Terminal nodes where cases end (success or failure)
- Edge probabilities that route cases through the graph

### Actor
Either a `HumanActor` (hourly cost, speed, error rate) or an `AIAgentActor` (per-execution cost, speed, error rate, escalation rate).

### KPIResult
The aggregated output of a simulation run: completion rate, failure rate, average cost/case, average cycle time, wait time, escalation rate, and per-node breakdowns.

### RedesignDiff
A before/after comparison of two `KPIResult` objects, including ROI, payback period, and bottleneck analysis.

### Assumption profile
A JSON-serializable set of simulation parameters: number of cases, random seed, implementation cost, and multipliers for AI error rates, AI costs, and human hourly costs.  Three profiles ship with every scenario: base, conservative, aggressive.

### ScenarioConfig
A JSON file with sparse overrides applied on top of a registered scenario: actor costs, node durations, branch probabilities, workflow names.  The original scenario is never mutated.

## Before vs after

Every scenario has a **before** (current-state, human-only) and **after** (redesigned, AI-assisted) workflow variant.  The simulator runs both and computes the delta.

## Simulation engines

**Simple** (default): sequential case processing; fast; approximates contention.

**Discrete-event**: chronologically-ordered event queue; more accurate under heavy load; slower.

Use `--engine discrete` for more faithful queueing behavior.

## Assumption profile hierarchy

1. Workflow actor defaults (in Python code)
2. Assumption profile multipliers (base/conservative/aggressive)
3. ScenarioConfig actor/node/edge overrides

Overrides are applied in this order when generating configured outputs.

## Limitation reminder

All figures are estimates anchored to user-provided assumptions.  The simulation does not replace operational measurement, process mining, or management consulting judgment.  See [Limitations](limitations.md).
