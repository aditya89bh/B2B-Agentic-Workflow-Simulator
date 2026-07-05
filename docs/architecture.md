# Architecture

## Design goal

Model a business workflow as data, independent of how it gets executed
or reported on. That separation is what makes "before vs. after"
comparison possible: the same `SimulationRunner` and `KPIResult` code
paths work for a fully-human process, a fully-automated one, or anything
in between, because all of that variation lives in the `Workflow`
definition, not in the engine.

## Layers

```
primitives/   Data-only building blocks (Node, Edge, Actor, Task, Event)
workflow.py   Graph structure + structural validation
simulation.py Execution engine (stateless, seeded RNG)
kpi.py        Aggregation of simulation output into business metrics
examples/     Concrete, business-realistic Workflow instances
cli.py        Thin argument-parsing layer over the above
```

Each layer only depends on the ones above it in this list. `primitives`
has no dependencies within the package. `workflow.py` depends only on
`primitives`. `simulation.py` depends on `primitives`, `workflow.py`, and
`kpi.py`. This keeps the domain model usable without pulling in
simulation or CLI concerns, which matters as the project grows (e.g. a
future web UI could import `workflow.py` and `kpi.py` directly).

## Node and Edge: the graph

A `Workflow` is a directed graph. `Node` instances are the vertices;
`Edge` instances are the directed, optionally-weighted arcs between them.
Every node is assigned exactly one `actor_id`, resolved against the
workflow's registered actors at simulation time. This keeps "who does the
work" (actor) separate from "what work happens" (node), so the same node
definition can be re-staffed with a different actor to build an "after"
variant, as the sales lead qualification example does.

Branching is expressed as multiple edges leaving the same source node,
each carrying a `probability`. `Workflow.validate()` enforces that these
probabilities sum to 1.0 and that every non-terminal node has at least
one outgoing edge, so malformed workflows fail fast before simulation
rather than producing silently wrong results.

## Actors: humans and AI agents

`HumanActor` and `AIAgentActor` both extend `Actor` but model cost and
failure differently, reflecting how these two kinds of workers actually
behave in practice:

- Humans incur cost proportional to time (`hourly_cost`), have a `speed_multiplier`
  representing relative efficiency, and an `error_rate` for mistakes/rework.
- AI agents incur a flat `cost_per_execution` regardless of duration
  (reflecting API/tool pricing), typically have a much lower
  `speed_multiplier`, and additionally have an `escalation_rate`
  representing how often the agent defers the task to a human rather than
  attempting it — a distinct failure mode from simply getting it wrong.

## Simulation model

`SimulationRunner.run(workflow, num_cases)` simulates `num_cases`
independent cases. Each case starts at `workflow.entry_node_id` and
repeats the following until it reaches a terminal node or fails:

1. Resolve the node's assigned actor.
2. Compute duration (`node.base_duration_minutes * actor.speed_multiplier`)
   and cost (`actor.cost_for_duration(duration)`).
3. Roll against `actor.error_rate` to decide whether the task fails; a
   failure ends the case immediately as a `CASE_FAILED` event.
4. If the actor is an `AIAgentActor`, roll against `escalation_rate` to
   decide whether the task is marked `ESCALATED` (still counted as
   progressing the case, but flagged distinctly for reporting).
5. If the node is terminal, end the case as `CASE_COMPLETED`.
6. Otherwise, choose the next node from the node's outgoing edges,
   weighted by `probability`, using the run's seeded RNG.

All of this is driven by a single `random.Random` instance seeded at
`SimulationRunner` construction, so a given seed reproduces the exact
same sequence of outcomes — essential for treating "before" and "after"
comparisons as controlled experiments rather than noisy one-off samples.

## KPI aggregation

`KPIResult` accumulates simple counters and totals during the run
(cases, cost, duration, per-node visit/failure/duration counts) and
exposes derived business metrics (`completion_rate`, `failure_rate`,
`avg_cost_per_case`, `avg_cycle_time_minutes`, `bottleneck_nodes()`) as
computed properties rather than stored fields, so there is exactly one
source of truth for each number.

## What Phase 1 deliberately leaves out

- Capacity/staffing constraints (e.g. an actor can only work N hours/day).
- Parallel or concurrent node execution.
- Cost/time distributions (durations are currently deterministic given a
  node and actor, not sampled from a distribution).
- Persistence, a web UI, or workflow authoring tools.

These are natural extensions for later phases once the core model has
proven itself on more examples.
