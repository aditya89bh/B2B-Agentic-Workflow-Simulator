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
primitives/   Data-only building blocks (Node, Edge, Actor, Task, Event, DurationModel)
workflow.py   Graph structure + structural validation
capacity.py   ActorScheduler: per-actor queueing and daily capacity limits
kpi.py        Aggregation of simulation output into business metrics
simulation.py Execution engine (stateless aside from its seeded RNG)
redesign.py   Before/after comparison of two KPIResult objects, plus ROI
report.py     Plain-text rendering of a RedesignDiff
export.py     JSON/CSV serialization of events, KPIs, and diffs
examples/     Concrete, business-realistic Workflow instances
cli.py        Thin argument-parsing layer over the above
```

Each layer only depends on the ones listed above it. `primitives` has no
dependencies within the package. `workflow.py` and `capacity.py` depend
only on `primitives`. `kpi.py` is standalone data. `simulation.py`
depends on `primitives`, `workflow.py`, `capacity.py`, and `kpi.py`.
`redesign.py` depends only on `kpi.py`, so a `RedesignDiff` can be built
from any two `KPIResult` objects without touching the simulation engine
at all -- useful for testing and for future integrations that produce
KPIs some other way. `report.py` and `export.py` both depend only on
`redesign.py` (and `kpi.py`/`primitives` for export), keeping "how we
compute results" fully separate from "how we present them."

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

`SimulationRunner.run(workflow, num_cases, arrival_interval_minutes=None)`
simulates `num_cases` cases. Each case starts at `workflow.entry_node_id`
and repeats the following until it reaches a terminal node or fails:

1. Resolve the node's assigned actor.
2. Sample a duration from the node's `DurationModel` (fixed by default)
   and scale it by `actor.speed_multiplier`; compute cost via
   `actor.cost_for_duration(duration)`.
3. If `arrival_interval_minutes` was given, ask the run's `ActorScheduler`
   when this actor can actually start the task -- this is where queueing
   and daily capacity limits are enforced (see `docs/capacity_modeling.md`).
   Otherwise the actor is always immediately available, matching Phase 1
   behavior exactly.
4. Roll against `actor.error_rate` to decide whether the task fails; a
   failure ends the case immediately as a `CASE_FAILED` event.
5. If the actor is an `AIAgentActor`, roll against `escalation_rate` to
   decide whether the task is marked `ESCALATED` (still counted as
   progressing the case, but flagged distinctly for reporting).
6. If the node is terminal, end the case as `CASE_COMPLETED`.
7. Otherwise, choose the next node from the node's outgoing edges,
   weighted by `probability`, using the run's seeded RNG.

All of this is driven by a single `random.Random` instance seeded at
`SimulationRunner` construction, so a given seed reproduces the exact
same sequence of outcomes — essential for treating "before" and "after"
comparisons as controlled experiments rather than noisy one-off samples.

## KPI aggregation

`KPIResult` accumulates simple counters and totals during the run
(cases, cost, duration, wait time, escalations, per-node and per-actor
breakdowns) and exposes derived business metrics (`completion_rate`,
`failure_rate`, `avg_cost_per_case`, `avg_cycle_time_minutes`,
`avg_wait_time_minutes`, `escalation_rate`, `bottleneck_nodes()`) as
computed properties rather than stored fields, so there is exactly one
source of truth for each number.

## Redesign diff and reporting

`compare_workflows(before, after, implementation_cost=None)` in
`redesign.py` takes two `KPIResult` objects and produces a `RedesignDiff`:
a `MetricDelta` for each headline metric (before, after, absolute delta,
percent change), the top bottleneck nodes on each side, per-actor
utilization on each side, and an `ROIAnalysis` (total and per-case cost
savings, ROI percentage, and payback in cases if an implementation cost
was supplied). `report.py`'s `generate_report()` renders a `RedesignDiff`
as a plain-text report with an executive summary, a KPI table, bottleneck
and utilization sections, a heuristic-driven risks list, and a closing
recommendation. `export.py` serializes the same underlying data
(events, `KPIResult`, `RedesignDiff`) to JSON or CSV for downstream tools.

## What Phase 2 deliberately leaves out

- True concurrent, event-driven scheduling across cases (the capacity
  model processes cases in arrival order rather than running a full
  discrete-event simulation with a global event heap).
- Persistence, a web UI, or workflow authoring tools.
- Multi-currency or time-zone-aware cost/scheduling models.

These remain natural extensions for later phases once the redesign and
capacity model have proven themselves on more examples.
