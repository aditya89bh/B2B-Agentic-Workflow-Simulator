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
primitives/    Data-only building blocks (Node, Edge, Actor, Task, Event, DurationModel)
workflow.py    Graph structure + structural validation
workflow_io.py JSON (de)serialization + stdlib schema validation for Workflow
capacity.py    ActorScheduler: per-actor queueing and daily capacity limits
kpi.py         Aggregation of simulation output into business metrics
simulation.py  Execution engine (stateless aside from its seeded RNG)
redesign.py    Before/after comparison of two KPIResult objects, plus ROI
portfolio.py   Aggregation and ranking across several RedesignDiff results
sensitivity.py Parameter sweeps over a before/after pair, break-even detection
report.py      Plain-text rendering of a RedesignDiff or WorkflowPortfolio
html_report.py Static HTML rendering of a RedesignDiff or WorkflowPortfolio
export.py      JSON/CSV serialization of events, KPIs, and diffs
examples/      Concrete, business-realistic Workflow instances + sample JSON
cli.py         Thin argument-parsing layer over the above
```

Each layer only depends on the ones listed above it. `primitives` has no
dependencies within the package. `workflow.py` and `capacity.py` depend
only on `primitives`. `workflow_io.py` depends on `primitives` and
`workflow.py` to build/serialize a `Workflow`, but not on `simulation.py`
-- persistence and execution are independent concerns. `kpi.py` is
standalone data. `simulation.py` depends on `primitives`, `workflow.py`,
`capacity.py`, and `kpi.py`. `redesign.py` depends only on `kpi.py`, so a
`RedesignDiff` can be built from any two `KPIResult` objects without
touching the simulation engine at all -- useful for testing and for
future integrations that produce KPIs some other way. `portfolio.py`
depends only on `kpi.py` and `redesign.py`, following the same pattern:
it aggregates already-computed `RedesignDiff` results rather than
running simulations itself. `sensitivity.py` is the one exception that
does depend on `simulation.py`, since a sweep has to actually re-run the
simulation at each parameter value. `report.py` and `html_report.py`
both depend on `redesign.py` and `portfolio.py`, and `export.py` depends
on `redesign.py` (and `kpi.py`/`primitives`), keeping "how we compute
results" fully separate from "how we present them."

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

## Portfolio aggregation and ranking

A single `RedesignDiff` answers "should we do this one redesign?" A
`WorkflowPortfolio` (in `portfolio.py`) answers a different question:
"across everything we could redesign, where should we start?" It holds
a list of `PortfolioEntry` objects, each wrapping the raw before/after
`KPIResult` pair plus the `RedesignDiff` computed from them, and
provides `ranked(by=...)` (sorting entries by total cost savings, ROI
percentage, or per-case savings) and `summary()` (aggregate before/after
cost, total savings, total wait-time saved, and a combined payback
period, computed from raw KPI totals rather than re-deriving them from
averaged deltas). See `docs/portfolio_analysis.md` for the full model
and the assumptions behind the aggregate payback figure.

## Sensitivity sweeps and break-even detection

`sensitivity.py` re-simulates a before/after pair while varying one
assumption at a time -- AI error rate, AI cost per execution, human
hourly cost, arrival interval, or implementation cost -- and returns a
`SensitivityResult` with one `RedesignDiff` per value tested. Because
`implementation_cost` only affects the ROI calculation and not the
simulation itself, that sweep simulates once and reuses the result
across every value rather than re-running the simulation redundantly.
`SensitivityResult.break_even_range()` scans consecutive points for a
sign change in a chosen metric (total cost savings by default) and
returns the bracketing pair of parameter values, giving a concrete
answer to "how much can this assumption move before the redesign stops
paying off?" See `docs/sensitivity_analysis.md`.

## Persisting workflow definitions

`workflow_io.py` converts a `Workflow` to and from a plain JSON-
compatible `dict`, plus a validation pass (`validate_workflow_dict`)
implemented as a direct tree walk with `isinstance` checks rather than
a schema library dependency -- the structure is simple enough (actors,
nodes, edges, each with a handful of typed fields) that hand-written
validation is both sufficient and easier to read than a general-purpose
JSON Schema. `save_workflow`/`load_workflow` wrap this with file I/O.
Every bundled example ships a matching JSON definition under
`examples/data/`, generated directly from the Python builders, so the
two representations cannot silently drift apart (a test asserts every
sample file loads and validates). See `docs/json_workflows.md`.

## HTML reporting

`html_report.py` renders the same underlying `RedesignDiff` and
`WorkflowPortfolio` data that `report.py` renders as plain text, but as
a single, self-contained HTML document with inline CSS -- no frontend
framework, no external assets, nothing that needs a server. Every piece
of interpolated text (workflow names, node ids, risk messages) is
escaped via the stdlib `html` module, so the renderer is safe even if a
workflow definition contains characters that would otherwise break the
page. `report.py` and `html_report.py` share the same value-formatting
and risk/recommendation helper functions so the two presentations never
disagree about what a number means.

## What Phase 3 deliberately leaves out

- True concurrent, event-driven scheduling across cases (the capacity
  model processes cases in arrival order rather than running a full
  discrete-event simulation with a global event heap).
- A web UI or a GUI workflow authoring tool (JSON persistence supports
  hand-editing or future tooling, but no such tooling is included here).
- Multi-currency or time-zone-aware cost/scheduling models.
- Multi-parameter sensitivity sweeps (each sweep varies exactly one
  assumption at a time; joint sensitivity across two or more parameters
  would require a grid search, deliberately left out to avoid
  over-engineering a feature with no example driving its design yet).

These remain natural extensions for later phases once the redesign,
capacity, portfolio, and sensitivity models have proven themselves on
more examples.
