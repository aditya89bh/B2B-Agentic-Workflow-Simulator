# Changelog

## Phase 6 - Organizational Digital Twin

Lifts the simulator from individual-workflow analysis to the full organizational
level: departments, teams, budgets, shared resources, multi-workflow runs,
growth projections, restructuring scenarios, and a composite health score.  All
Phase 1–5 APIs remain fully backward compatible.

- **Organization model** (`org_model.py`): `Organization`, `Department`, `Team`,
  `Role`, `ReportingLine`, and `OrgUnit` give every workflow a home inside a
  structured hierarchy.  `Organization.validate()` checks referential integrity.
  `org_units()` projects the hierarchy as a traversable flat list.

- **Budget model** (`budget.py`): `BudgetAllocation`, `DepartmentBudget`, and
  `OrgBudget` track spend across five categories (operating, implementation, AI
  tooling, hiring, training), surface utilization, overruns, and a 0–100
  budget pressure score.

- **Shared resource pool** (`shared_resources.py`): `SharedResource`,
  `ResourceContention`, and `SharedResourcePool` model resources shared across
  workflows (legal reviewers, finance approvers, AI agents, software tools,
  external vendors), computing contention ratios and qualitative overload risk
  (`none` / `moderate` / `high` / `critical`).

- **Cross-workflow simulation** (`cross_workflow.py`): `CrossWorkflowSimulator`
  runs multiple workflows against one `Organization`, producing a
  `CrossWorkflowResult` that aggregates per-workflow `SimulationResult` objects.

- **Restructuring simulation** (`restructuring.py`): `RestructuringScenario` and
  `evaluate_restructuring` model seven organizational design changes — centralize
  team, decentralize team, add shared services, outsource stage, create AI ops
  team, hire additional staff, reduce approval layers — projecting cost,
  cycle-time, risk, staffing, and budget impacts.
  `compare_restructuring_scenarios` ranks a set by net benefit score.

- **Growth projection engine** (`growth.py`): `GrowthConfig` and `project_growth`
  generate a 12-month forecast of case volume, cost, headcount, budget, AI
  adoption, and capacity utilization; breaking points (capacity or budget
  overload) are flagged with explanatory reasons.

- **Organizational health score** (`org_health.py`): `compute_org_health` scores
  eight dimensions (utilization balance, queue pressure, budget pressure,
  compliance risk, SLA risk, AI readiness, single points of failure, cross-team
  dependency load) into a weighted composite 0–100 score with a letter grade
  (A–F) and per-dimension explanations.

- **Org digital twin report** (`org_report.py`): `OrgDigitalTwinReport` bundles
  all Phase 6 analysis results; `generate_org_digital_twin_report` renders them
  as a single multi-section plain-text document.

- **HTML renderers**: `html_report.py` gains `render_org_health_html`,
  `render_org_budget_html`, `render_org_growth_html`, and
  `render_org_executive_html` for standalone HTML org reports.

- **Bundled B2B SaaS example** (`examples/saas_org.py`): `build_saas_org`,
  `build_saas_org_budget`, and `build_saas_shared_resources` provide a
  pre-built 6-department, 18-role B2B SaaS company with the three existing
  workflows wired in.

- **Seven new CLI commands**: `run-org`, `org-health`, `org-budget-analysis`,
  `org-resource-contention`, `org-growth-projection`, `org-restructure-scenario`,
  `org-executive-report`.

- **Documentation**: `docs/organization_model.md`, `docs/budget_modeling.md`,
  `docs/shared_resources.md`, `docs/org_growth_projection.md`,
  `docs/restructuring_simulation.md`, `docs/org_health_score.md`;
  `docs/architecture.md`, `docs/getting_started.md`, and `README.md` updated.

- **Tests**: 296 new tests across 11 new test files covering all Phase 6
  modules, HTML escaping, CLI commands, and backward compatibility.

## Phase 5 - Enterprise Decision-Support Platform

Transformed the simulator from an enterprise workflow simulator into an
enterprise decision-support platform: the simulator now reasons about
governance, compliance, business risk, organizational policies, and AI
adoption, not just workflow execution, while remaining fully backward
compatible with every prior phase.

- Multi-resource tasks: `Node.additional_actor_ids` lets a task require
  more than one actor (or pool) simultaneously (e.g. Manager + Legal, AI
  Agent + Human Reviewer). `multi_resource.py` adds
  `schedule_multi_resource_execution()`, synchronizing every participant's
  earliest joint availability across both simulation engines via new
  non-mutating `ActorScheduler.peek_free_at()`/`PoolScheduler.peek_earliest_start()`
  methods. `KPIResult` gains `total_coordination_delay_minutes`,
  `node_coordination_delay_minutes`, and `multi_resource_task_count`.
  `workflow_io.py` persists `additional_actor_ids` in JSON. Single-actor
  workflows are byte-for-byte unaffected.
- Business policy engine: `policy.py` adds `ApprovalPolicy`,
  `RoutingPolicy`, `EscalationPolicy`, `RetryPolicy`,
  `BusinessHoursPolicy`, `MandatoryHumanReviewPolicy`, and
  `SeparationOfDutiesPolicy`, each checked structurally against a
  `Workflow` by `evaluate_policies()`, producing a `PolicyEvaluation` with
  severity-classified `PolicyViolation` records and a plain-text report.
- Compliance engine: `compliance.py` adds `GDPRApprovalRequirement`,
  `AuditRequirement`, `FinancialApprovalChainRequirement`,
  `SegregationOfDutiesRequirement`, `MandatoryDocumentationRequirement`,
  `RecordRetentionRequirement`, and `RegulatoryCheckpointRequirement`,
  checked by `evaluate_compliance()` into a `ComplianceReport` with
  violations, a compliance score, and informational `AuditFinding`
  records.
- SLA engine: `sla.py` adds `CompletionSLA`, `ResponseSLA`, and
  `EscalationSLA`, checked by `evaluate_sla()` against a simulation's
  event log into an `SLAReport` with attainment rate, breach count,
  average breach duration, breach causes, and estimated financial
  penalties.
- Organizational risk engine: `risk.py` adds `compute_risk()`, scoring a
  workflow across six categories (operational, compliance, AI failure,
  staffing, process complexity, single point of failure) into a
  `RiskAssessment` with an overall score and an explainable list of
  `RiskFactor` records behind every category.
- Recommendation engine: `recommendation.py` adds
  `generate_recommendations()`, producing a prioritized `RecommendationSet`
  of actionable suggestions (automate task, keep human review, increase/
  reduce staffing, merge/split activities, introduce a memory-enabled
  agent, introduce/remove an approval gate, redesign an escalation path),
  each required to carry reasoning, affected KPIs, expected benefit, and a
  confidence level.
- AI adoption assessment: `ai_adoption.py` adds `assess_ai_adoption()`,
  scoring automation readiness, AI maturity, human dependency, governance,
  explainability, and rollout complexity into a readiness index and a
  pilot/phased-rollout/full-deployment/not-recommended recommendation.
- Executive assessment report: `executive_report.py` adds
  `build_executive_assessment()` and `generate_executive_report()`,
  combining KPI summary, ROI, SLA performance, compliance, policy
  violations, organizational risk, recommendations, and AI adoption into
  one plain-text or HTML report, gracefully omitting any section whose
  optional input was not supplied.
- Governance examples: `examples/governance.py` defines concrete,
  business-realistic policies, compliance requirements, and SLAs for all
  three bundled example workflows, including scenarios that deliberately
  surface a segregation-of-duties gap and a mandatory-human-review
  violation introduced by an AI-augmented redesign.
- CLI: added `policy-analysis`, `compliance-analysis`, `risk-analysis`,
  `readiness-analysis`, `recommend-redesign`, and `executive-report`, each
  supporting `--variant before|after` (where applicable) and an optional
  `--html-output`.
- Unit test coverage for multi-resource scheduling and coordination delay,
  every policy and compliance requirement type and their violations,
  audit findings, SLA breach detection and penalty calculation, risk
  scoring across every category, recommendation generation and
  confidence ranking, AI readiness scoring, executive report assembly and
  rendering, HTML escaping for every new report type, every new CLI
  command, and backward compatibility of every prior phase's API.
- Documentation: updated README, architecture, and getting-started docs;
  added `docs/policy_engine.md`, `docs/compliance.md`,
  `docs/sla_modeling.md`, `docs/risk_engine.md`,
  `docs/recommendation_engine.md`, and `docs/ai_adoption.md`; documented
  multi-resource tasks in `docs/team_capacity.md`.

## Phase 4 - Enterprise Process Simulation

Transformed the simulator from a single-process modeling tool into an
enterprise-grade business process simulation engine: true event-driven
scheduling, realistic arrival patterns, team-based workforce modeling,
Monte Carlo variability analysis, multi-parameter sensitivity, and
capacity planning.

- Discrete-event simulation engine: `discrete_event.py` adds
  `DiscreteEventEngine`, processing arrivals and task completions
  through a single global, time-ordered priority queue instead of one
  case at a time. `SimulationRunner.run()` accepts `engine="simple"`
  (default, unchanged) or `engine="discrete"`; both share the same
  scheduling helpers and produce identical results under light
  contention. Added `TASK_QUEUED` and `RESOURCE_RELEASED` events for
  fine-grained queueing visibility in capacity-aware runs.
- Advanced arrival modelling: `arrivals.py` adds `ArrivalModel`
  supporting fixed, uniform-random, batched, business-hour, and
  peak-hour arrival patterns, fully seeded and deterministic; wired
  into both simulation engines via `arrival_model=`.
- Queueing analysis: `queueing.py` reconstructs queue depth over time,
  actor idle minutes, and throughput from a run's event log, and
  classifies each actor's queue trend as growing, collapsing, or
  stable using a time-weighted comparison across the run.
- Team pools and workforce scheduling: `primitives/worker.py` and
  `primitives/shift.py` add `Worker` and `Shift`; `pool.py` adds
  `ActorPool` (a team of workers scheduled as one actor) and
  `PoolScheduler` (least-loaded routing respecting shift days/hours,
  overtime capacity, and unavailable workers). `KPIResult` gains
  `pool_utilization` and `worker_utilization` for team-level and
  per-worker capacity reporting. Wired into both simulation engines.
- Monte Carlo analysis: `monte_carlo.py` adds `run_monte_carlo()` and
  `run_monte_carlo_comparison()`, re-simulating a workflow (or a
  before/after pair) across many seeds and reporting mean, min, max,
  median, P10, and P90 for every KPI, ROI, and payback, plus plain-text
  and HTML executive reports explaining outcome variability.
- Multi-parameter sensitivity: `sensitivity_grid.py` extends the
  single-parameter sweep to a two-dimensional grid, classifying every
  `(x, y)` combination as a safe, negative-ROI, or operationally
  unstable operating region; plain-text and HTML ROI matrix reports.
- Capacity planning: `capacity_planning.py` adds `analyze_capacity()`
  (staffing recommendations against a target utilization, flagging
  overloaded/underutilized resources) and `simulate_hiring()`
  (re-simulates a workflow with proposed additional pool workers to
  verify a specific hire's impact on utilization, queue depth, and
  wait time), with plain-text and HTML reports.
- CLI: added `monte-carlo-example`, `monte-carlo-portfolio`,
  `sensitivity-grid-example`, `capacity-analysis`, and
  `team-utilization`; `run-example` and `compare-example` now accept
  `--engine simple|discrete`.
- Unit test coverage for discrete-event scheduling and ordering,
  arrival models, actor pools and shift scheduling, queue behavior
  analysis, Monte Carlo aggregation and percentile calculations,
  multi-parameter sensitivity and region classification, capacity
  planning and hiring simulation, every new CLI command, and
  backward compatibility of the existing simple-engine API.
- Documentation: updated README, architecture, and capacity modeling
  docs; added `docs/discrete_event_engine.md`, `docs/team_capacity.md`,
  `docs/monte_carlo.md`, `docs/advanced_sensitivity.md`, and
  `docs/capacity_planning.md`.

## Phase 3 - Portfolios, Sensitivity Analysis, and Persistence

Added the tooling needed to run this beyond a single workflow: comparing
several redesigns as a program, testing how sensitive an ROI case is to
its underlying assumptions, persisting workflow definitions outside of
Python, and sharing results as static HTML.

- Portfolio model: `WorkflowPortfolio` in `portfolio.py` aggregates
  several before/after workflow comparisons, ranks them by total cost
  savings, ROI percentage, or per-case savings, and rolls up aggregate
  before/after cost, cost savings, wait-time savings, and a combined
  payback period.
- Portfolio report: `generate_portfolio_report()` in `report.py` renders
  a plain-text report with an executive summary, workflow ranking,
  aggregate ROI/payback, consolidated risks across every workflow, and a
  recommended rollout order.
- Sensitivity analysis: `run_sensitivity_sweep()` in `sensitivity.py`
  sweeps AI error rate, AI cost per execution, human hourly cost,
  arrival interval, or implementation cost across a before/after pair,
  fully seeded and reproducible; `SensitivityResult.break_even_range()`
  identifies the parameter range where cost savings cross from positive
  to negative.
- Third bundled example: customer support ticket resolution, with
  realistic failure paths (wrong classification, missing customer
  context, low-confidence response, delayed escalation) and an
  AI-augmented redesign that introduces a Support Reviewer role for
  complex cases while reserving the Specialist for genuine escalations.
- Persistent workflow definitions: `workflow_io.py` adds
  `save_workflow()`/`load_workflow()` plus stdlib-only structural
  validation (`validate_workflow_dict()`, no schema library dependency);
  every bundled example ships a matching JSON definition under
  `examples/data/`.
- HTML report renderer: `html_report.py` renders a `RedesignDiff` or
  `WorkflowPortfolio` as a single, self-contained HTML document with
  inline CSS and fully escaped interpolated text -- no frontend
  framework, no external assets.
- CLI: added `run-portfolio`, `compare-portfolio` (with `--rank-by` and
  optional `--html-output`), `sensitivity-example`, `save-example`,
  `load-example`, and `html-report-example`; registered the customer
  support example alongside the existing two.
- Unit test coverage for the portfolio model and report, sensitivity
  sweeps and break-even detection, the customer support example, JSON
  load/save and validation errors, HTML report escaping, and every new
  CLI command.
- Documentation: updated README, architecture, and getting-started
  docs; added `docs/portfolio_analysis.md`, `docs/sensitivity_analysis.md`,
  and `docs/json_workflows.md`.

## Phase 2 - Redesign Analysis and Capacity Modeling

Added the tooling needed to turn a simulation run into a business case:
capacity-aware queueing, realistic duration variance, a structured
redesign comparison with ROI/payback, plain-text reporting, export
support, and a second business example.

- Capacity modeling: `ActorScheduler` models actors as single-server
  queues with daily capacity limits (`available_hours_per_day` on every
  actor); `SimulationRunner.run()` accepts an optional
  `arrival_interval_minutes` to enable queueing, wait time tracking, and
  per-actor utilization.
- Duration variance: `DurationModel` primitive supports fixed, uniform,
  and triangular sampling, fully seeded and reproducible; integrated
  into `Node` and the simulation runner.
- Redesign diff engine: `compare_workflows()` in `redesign.py` produces a
  structured `RedesignDiff` (completion rate, failure rate, cost,
  cost per case, cycle time, wait time, escalation rate, bottlenecks,
  utilization) plus an `ROIAnalysis` with payback logic.
- ROI report: `generate_report()` in `report.py` renders a `RedesignDiff`
  as a plain-text report with an executive summary, KPI table,
  bottlenecks, utilization, risks, and a recommendation.
- Export support: `export.py` serializes event logs, `KPIResult`
  summaries, and `RedesignDiff` comparisons to JSON, and comparisons to
  CSV.
- Second bundled example: invoice processing (accounts payable), with
  realistic exception paths (missing PO, mismatched amount, vendor data
  issue, approval delay) and an AI-augmented redesign that keeps a human
  AP Specialist in the loop for every exception.
- CLI: `run-example` and `compare-example` now support both bundled
  examples; added `compare-example` (full ROI report, with
  `--implementation-cost` and `--arrival-interval`) and `export-example`
  (`--format json|csv`).
- Unit test coverage for capacity constraints, queueing, wait time,
  utilization, duration distributions, the redesign diff engine, the ROI
  report, JSON/CSV export, the invoice processing example, and the new
  CLI commands.
- Documentation: updated README, architecture, and getting-started docs;
  added `docs/redesign_analysis.md` and `docs/capacity_modeling.md`.

## Phase 1 - Foundation

Established the core domain model and a working end-to-end simulation.

- Core primitives: `Node`, `Edge`, `Actor`, `HumanActor`, `AIAgentActor`,
  `Task`, `Event`.
- `Workflow` graph model with structural validation.
- `KPIResult` aggregation object with derived business metrics.
- `SimulationRunner`: seeded, reproducible execution engine.
- Bundled example: sales lead qualification, before (human-only) and
  after (AI-augmented) variants.
- `b2b-simulator` CLI with a `run-example` command that prints a
  before/after KPI comparison.
- Unit test coverage for every primitive, the workflow model, the
  simulation runner, the example workflow, and the CLI.
- Project scaffolding: `pyproject.toml`, README, architecture and
  getting-started docs, MIT license.
