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
primitives/           Data-only building blocks (Node, Edge, Actor, Task, Event,
                      DurationModel, Worker, Shift)
workflow.py           Graph structure + structural validation
workflow_io.py        JSON (de)serialization + stdlib schema validation for Workflow
capacity.py           ActorScheduler: per-actor queueing and daily capacity limits
arrivals.py           ArrivalModel: fixed/uniform/batched/business-hour/peak-hour patterns
pool.py               ActorPool + PoolScheduler: team capacity, least-loaded routing
queueing.py           Queue depth, growth/collapse, idle time, throughput analysis
discrete_event.py     DiscreteEventEngine: global priority-queue simulation
kpi.py                Aggregation of simulation output into business metrics
simulation.py         Execution engine (simple engine; dispatches to DiscreteEventEngine)
redesign.py           Before/after comparison of two KPIResult objects, plus ROI
portfolio.py          Aggregation and ranking across several RedesignDiff results
sensitivity.py        Parameter sweeps over a before/after pair, break-even detection
sensitivity_grid.py   Two-parameter sensitivity grids, ROI/region classification
monte_carlo.py        Repeated seeded runs, percentile statistics, variability reports
capacity_planning.py  Staffing recommendations and hiring simulation
multi_resource.py     Synchronized scheduling for tasks needing several actors at once
policy.py             Business policy engine: governance rules checked against workflow structure
compliance.py         Compliance engine: regulatory/audit requirements and audit findings
sla.py                SLA engine: deadline tracking and breach analysis over an event log
risk.py               Organizational risk engine: category scores and explainable risk factors
recommendation.py     Recommendation engine: actionable, reasoned suggestions
ai_adoption.py        AI adoption readiness scoring and rollout recommendation
executive_report.py   Bundles every analysis above into one executive assessment report
report.py             Plain-text rendering of a RedesignDiff or WorkflowPortfolio
html_report.py        Static HTML rendering of all report types
export.py             JSON/CSV serialization of events, KPIs, and diffs
examples/             Concrete, business-realistic Workflow instances + sample JSON
                      (including examples/governance.py: policy/compliance/SLA definitions)
cli.py                Thin argument-parsing layer over the above
```

Each layer only depends on the ones listed above it. `primitives` has no
dependencies within the package. `workflow.py` and `capacity.py` depend
only on `primitives`. `workflow_io.py` depends on `primitives` and
`workflow.py` to build/serialize a `Workflow`, but not on `simulation.py`
-- persistence and execution are independent concerns. `kpi.py` is
standalone data. `arrivals.py` depends only on the standard library.
`pool.py` depends on `primitives` (specifically `Worker` and `Shift`)
and mirrors `capacity.py`'s scheduling role for teams instead of single
actors. `queueing.py` depends only on `simulation.py`'s `SimulationResult`
shape, replaying its event log rather than hooking into execution
itself. `discrete_event.py` depends on `primitives`, `workflow.py`,
`capacity.py`, `pool.py`, and shares its scheduling helpers with
`simulation.py` (which imports from it, not the reverse, keeping the
simple engine as the default with no import-time cost for the
discrete-event path). `simulation.py` depends on `primitives`,
`workflow.py`, `capacity.py`, `pool.py`, `arrivals.py`, and `kpi.py`.
`redesign.py` depends only on `kpi.py`, so a `RedesignDiff` can be built
from any two `KPIResult` objects without touching the simulation engine
at all -- useful for testing and for future integrations that produce
KPIs some other way. `portfolio.py` depends only on `kpi.py` and
`redesign.py`, following the same pattern: it aggregates
already-computed `RedesignDiff` results rather than running simulations
itself. `sensitivity.py`, `sensitivity_grid.py`, and `monte_carlo.py` all
depend on `simulation.py` and `redesign.py`, since each has to actually
re-run the simulation (once per swept value, once per grid cell, or
once per seed, respectively) to observe how outcomes change.
`capacity_planning.py` depends on `kpi.py`, `pool.py`, `queueing.py`,
and `simulation.py`. `multi_resource.py` depends on `primitives`,
`capacity.py`, and `pool.py`, sharing their scheduling primitives so a
multi-resource task's participants are reserved through the exact same
calendars single-actor and pooled tasks use. `policy.py` and
`compliance.py` each depend only on `workflow.py` (and, for
`BusinessHoursPolicy`, `pool.py`), since every check they perform is
structural -- no simulation is required to evaluate a policy or
compliance requirement. `sla.py` depends on `simulation.py` (specifically
`SimulationResult`) instead, since SLA attainment is checked against an
event log from an actual run. `risk.py` depends on `kpi.py`, `policy.py`,
`compliance.py`, `pool.py`, and `workflow.py`, combining structural and
simulated signals into one risk picture; its `policy_evaluation` and
`compliance_report` parameters are optional so risk can still be computed
for a workflow with no governance data attached. `recommendation.py`
depends on `kpi.py`, `risk.py`, and `workflow.py`. `ai_adoption.py`
depends on `kpi.py`, `policy.py`, and `workflow.py`.
`executive_report.py` depends on all of the above plus `redesign.py`,
orchestrating every Phase 5 engine into one bundled result without
introducing a new computation path of its own. `report.py` and
`html_report.py` depend on `redesign.py`, `portfolio.py`,
`monte_carlo.py`, `sensitivity_grid.py`, `capacity_planning.py`,
`policy.py`, `compliance.py`, `sla.py`, `risk.py`, `recommendation.py`,
`ai_adoption.py`, and `executive_report.py`, and `export.py` depends on
`redesign.py` (and `kpi.py`/`primitives`), keeping "how we compute
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

`SimulationRunner.run(workflow, num_cases, arrival_interval_minutes=None, arrival_model=None, engine="simple")`
simulates `num_cases` cases. Each case starts at `workflow.entry_node_id`
and repeats the following until it reaches a terminal node or fails:

1. Resolve the node's assigned actor (a single `HumanActor`/`AIAgentActor`,
   or an `ActorPool`).
2. Sample a duration from the node's `DurationModel` (fixed by default)
   and scale it by the actor's (or, for a pool, the routed worker's)
   `speed_multiplier`; compute cost accordingly.
3. If `arrival_interval_minutes` or `arrival_model` was given, ask the
   run's `ActorScheduler` (single actor) or `PoolScheduler` (pool) when
   this resource can actually start the task -- this is where queueing,
   daily capacity limits, and shift schedules are enforced (see
   `docs/capacity_modeling.md` and `docs/team_capacity.md`). Otherwise
   the resource is always immediately available, matching Phase 1
   behavior exactly.
4. Roll against the resource's `error_rate` to decide whether the task
   fails; a failure ends the case immediately as a `CASE_FAILED` event.
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

`engine="simple"` (the default) processes cases one at a time in
arrival order, as described above. `engine="discrete"` dispatches to
`DiscreteEventEngine`, which processes the same per-case logic but
through a single global, time-ordered priority queue of arrival and
task-completion events, giving a more general model of contention
across many simultaneously in-flight cases. Both engines share the same
scheduling helpers and produce the same `SimulationResult` shape; see
`docs/discrete_event_engine.md` for when the two can diverge and why.
`arrival_model` (an `ArrivalModel` from `arrivals.py`) is an alternative
to `arrival_interval_minutes` for generating non-uniform arrival
patterns -- uniform-random gaps, batched arrivals, or business-hour/
peak-hour spacing -- while remaining fully deterministic for a given
seed.

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

## Team pools, queueing analysis, and workforce scheduling

`pool.py` extends single-actor capacity to `ActorPool`: a team of
`Worker`s, each with independent cost, speed, reliability, shift
schedule, and availability. `PoolScheduler` routes each task to
whichever available worker can start soonest ("least-loaded" routing),
respecting shift days/hours and any overtime capacity, and tracks
utilization at both the pool and individual-worker level. `queueing.py`
replays a run's event log to reconstruct queue depth over time, actor
idle minutes, and throughput, and classifies each actor's queue as
growing, collapsing, or stable using a time-weighted comparison of the
first and second halves of its observed timeline. See
`docs/team_capacity.md`.

## Monte Carlo analysis

A single seeded run is one plausible outcome, not the range of outcomes
real random variation produces. `monte_carlo.py` re-runs a workflow (or
a before/after pair) once per seed and summarizes each metric's
distribution -- mean, min, max, median, P10, P90, and standard
deviation -- via `run_monte_carlo()`/`run_monte_carlo_comparison()`,
with plain-text and HTML executive reports that translate the
statistics into a plain-language read on how much confidence to place
in a point estimate. See `docs/monte_carlo.md`.

## Multi-parameter sensitivity

`sensitivity_grid.py` extends `sensitivity.py`'s single-parameter sweep
to a two-dimensional grid, re-simulating a before/after pair once per
`(x, y)` combination of two swept assumptions. Every grid cell is
classified as a safe, negative-ROI, or operationally unstable operating
region, surfacing interactions between assumptions (e.g. AI cost and
error rate moving together) that two independent single-parameter
sweeps cannot capture. See `docs/advanced_sensitivity.md`.

## Capacity planning

`capacity_planning.py` turns simulated utilization into a staffing
decision: `analyze_capacity()` classifies each actor or pool as
overloaded, underutilized, or balanced against a target utilization and
recommends a headcount change, while `simulate_hiring()` actually
re-runs the simulation with proposed additional workers to verify a
specific hire relieves the queueing pressure it is meant to relieve,
rather than trusting a headcount formula in isolation. See
`docs/capacity_planning.md`.

## Multi-resource tasks

`Node.additional_actor_ids` lets a task require more than one actor (or
pool) simultaneously -- e.g. a Manager-and-Legal sign-off. Both engines
detect this and delegate to `multi_resource.schedule_multi_resource_execution()`,
which finds the joint time every participant is free, reserves that slot
on each of their calendars, and sums their costs, while the primary actor
(`Node.actor_id`) still determines the task's visible duration, error rate,
and escalation behavior -- keeping single-actor workflows byte-for-byte
unaffected. The extra wait synchronization adds beyond the fastest
participant's own availability is tracked separately as coordination delay
on `KPIResult`. See `docs/team_capacity.md`.

## Governance: policies and compliance

Where the rest of the engine answers "what happens," `policy.py` and
`compliance.py` answer "is what happens allowed to happen this way,"
checked against a workflow's structure independent of any simulation run.
`policy.py` models internal governance rules an organization chooses to
enforce (approval gates, routing restrictions, escalation paths, retry
safety, business hours, mandatory human review, separation of duties);
`compliance.py` models external regulatory/audit obligations (GDPR-style
consent gates, financial approval chains, segregation of duties, mandatory
documentation, record retention, regulatory checkpoints) and additionally
produces informational `AuditFinding` records alongside hard violations.
Both are plain dataclasses evaluated by a single dispatch function
(`evaluate_policies`/`evaluate_compliance`) against a `Workflow`, following
the same "data in, structured result out" shape as everything else in this
codebase. See `docs/policy_engine.md` and `docs/compliance.md`.

## SLA tracking

`sla.py` is the one governance-adjacent engine that checks a simulation's
*actual timing* rather than workflow structure: `CompletionSLA`,
`ResponseSLA`, and `EscalationSLA` rules are replayed against a
`SimulationResult`'s event log, per case, to compute attainment rate,
breach count, average breach duration, breach causes, and an optional
estimated financial penalty. See `docs/sla_modeling.md`.

## Organizational risk, recommendations, and AI adoption

`risk.py` scores a workflow across six categories (operational, compliance,
AI failure, staffing, process complexity, single point of failure),
combining KPI signals, workflow structure, and optional policy/compliance
results into an overall score backed by an explainable list of
`RiskFactor` records. `recommendation.py` turns those signals (plus its
own independent heuristics) into a prioritized list of actionable
`Recommendation` objects, each required to carry reasoning, affected KPIs,
an expected benefit, and a confidence level. `ai_adoption.py` scores six
different dimensions specific to AI rollout decisions (automation
readiness, AI maturity, human dependency, governance, explainability,
rollout complexity) into a single readiness index and a categorical
recommendation (pilot, phased rollout, full deployment, not recommended).
See `docs/risk_engine.md`, `docs/recommendation_engine.md`, and
`docs/ai_adoption.md`.

## Executive assessment report

`executive_report.py` is the top of the reporting stack: `build_executive_assessment()`
runs the risk and AI adoption engines (and, given supplied results, folds
in ROI, SLA, compliance, and policy sections) into one `ExecutiveAssessment`,
and `generate_executive_report()`/`render_executive_html()` render it as a
single plain-text or HTML document combining KPI summary, ROI, SLA
performance, compliance, policy violations, organizational risk,
recommendations, and AI adoption -- the same underlying data every other
report type in this codebase renders, assembled into the one document an
executive sponsor actually needs to read. See `docs/ai_adoption.md`.

## Phase 6: Organizational digital twin layer

Phase 6 adds an org-level layer that sits above individual workflows:

```
org_model.py          Organization, Department, Team, Role, ReportingLine, OrgUnit
budget.py             BudgetAllocation, DepartmentBudget, OrgBudget
shared_resources.py   SharedResource, ResourceContention, SharedResourcePool
cross_workflow.py     CrossWorkflowSimulator: run multiple workflows against one org
restructuring.py      RestructuringScenario, evaluate_restructuring (7 scenario types)
growth.py             GrowthConfig, GrowthProjection: 12-month demand forecasting
org_health.py         OrgHealthScore: 8-dimension composite health score with grades
org_report.py         OrgDigitalTwinReport, generate_org_digital_twin_report
examples/saas_org.py  Bundled B2B SaaS org (6 depts, 6 teams, 18 roles, 3 workflows)
```

HTML renderers added to `html_report.py`: `render_org_health_html`,
`render_org_budget_html`, `render_org_growth_html`, `render_org_executive_html`.

CLI commands added: `run-org`, `org-health`, `org-budget-analysis`,
`org-resource-contention`, `org-growth-projection`, `org-restructure-scenario`,
`org-executive-report`.

Dependency order within Phase 6:

1. `org_model` (no Phase 6 deps)
2. `budget` (no Phase 6 deps)
3. `shared_resources` (no Phase 6 deps)
4. `cross_workflow` → `org_model`, `simulation`
5. `restructuring` → `org_model`, `budget`, `kpi`
6. `growth` → `org_model`, `budget`
7. `org_health` → `org_model`, `budget`, `shared_resources`, `growth`, `kpi`
8. `org_report` → all Phase 6 modules above

## What this codebase deliberately leaves out

- A web UI or a GUI workflow authoring tool (JSON persistence supports
  hand-editing or future tooling, but no such tooling is included here).
- Multi-currency or time-zone-aware cost/scheduling models.
- Cross-training or skill differences within a pool beyond
  `speed_multiplier`/`error_rate`, and workers moving between pools
  mid-simulation.
- Optimization across multiple simultaneous staffing decisions (each
  sensitivity grid or hiring simulation evaluates one scenario at a
  time; comparing several means running the function once per scenario).
- A built-in library of named regulations (GDPR, SOX, HIPAA, etc.) --
  `compliance.py` models the *shapes* these obligations commonly take
  (consent gates, approval chains, segregation of duties, retention,
  checkpoints), not a database of jurisdiction-specific rules.
- Enforcing policies, compliance requirements, or SLAs during simulation
  itself -- all three are evaluated after the fact, against a workflow's
  structure or a completed run's event log, rather than changing
  scheduling decisions while a simulation is in progress.
- In-simulation shared resource enforcement (contention is computed
  analytically post-run, not modelled through the discrete-event engine).

These remain natural extensions for later phases once the current
models have proven themselves on more examples.
