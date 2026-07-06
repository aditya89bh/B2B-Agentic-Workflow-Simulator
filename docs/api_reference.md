# API Reference

Quick-reference for the major public objects.  All are importable from the
package; see each entry's import path.

---

## Core simulation stack

### `Workflow`
```python
from b2b_workflow_simulator.workflow import Workflow
```
The blueprint for a business process: a validated, directed graph of `Node`s
connected by `Edge`s, each operated by an `Actor`.

| Member | Type | Description |
|---|---|---|
| `workflow_id` | `str` | Stable unique identifier |
| `name` | `str` | Human-readable name |
| `entry_node_id` | `str` | Starting node for every case |
| `add_actor(actor)` | method | Register an actor |
| `add_node(node)` | method | Register a node (actor must exist) |
| `add_edge(edge)` | method | Register a directed edge |
| `validate()` | method | Raise `ValueError` if structurally invalid |
| `nodes` | `dict[str, Node]` | All registered nodes |
| `actors` | `dict[str, Actor]` | All registered actors |
| `edges` | `list[Edge]` | All registered edges |
| `outgoing_edges(node_id)` | method | Edges leaving a node |

### `Node`
```python
from b2b_workflow_simulator.primitives import Node
```
One stage of work in the workflow.

| Field | Type | Description |
|---|---|---|
| `node_id` | `str` | Unique identifier |
| `name` | `str` | Human-readable stage name |
| `actor_id` | `str` | Actor that performs this stage |
| `base_duration_minutes` | `float` | Base duration (before speed multiplier) |
| `duration_model` | `DurationModel` | How duration varies (`fixed`/`uniform`/`triangular`) |
| `is_terminal` | `bool` | Whether reaching this node ends the case |
| `additional_actor_ids` | `list[str]` | Extra actors for multi-resource nodes |

### `Edge`
```python
from b2b_workflow_simulator.primitives import Edge
```
A directed, probability-weighted transition between nodes.

| Field | Type | Description |
|---|---|---|
| `source` | `str` | Source node_id |
| `target` | `str` | Target node_id |
| `probability` | `float` | Probability of taking this edge (0–1); all outgoing edges from a node must sum to 1.0 |

### `HumanActor`
```python
from b2b_workflow_simulator.primitives import HumanActor
```

| Field | Default | Description |
|---|---|---|
| `actor_id` | required | Unique identifier |
| `hourly_cost` | required | USD/hour for this actor |
| `speed_multiplier` | `1.0` | < 1.0 = slower; > 1.0 = faster |
| `error_rate` | `0.0` | Fraction of tasks that fail |
| `available_hours_per_day` | `8.0` | Daily capacity (capacity-aware mode) |

### `AIAgentActor`
```python
from b2b_workflow_simulator.primitives import AIAgentActor
```

| Field | Default | Description |
|---|---|---|
| `cost_per_execution` | required | Flat cost per task |
| `speed_multiplier` | `1.0` | Relative to base node duration |
| `error_rate` | `0.0` | Task failure rate |
| `escalation_rate` | `0.0` | Rate at which AI defers to a human |

### `ActorPool`
```python
from b2b_workflow_simulator.pool import ActorPool
```
A team of interchangeable `Worker`s routed by least-loaded scheduling.

```python
pool = ActorPool(actor_id="cs-team", name="CS Team", workers=[...])
workflow.add_actor(pool)
```

### `Worker`
```python
from b2b_workflow_simulator.primitives.worker import Worker
```
One member of an `ActorPool`.  Has its own `hourly_cost`, `speed_multiplier`,
`error_rate`, and optional `Shift` schedule.

### `SimulationRunner`
```python
from b2b_workflow_simulator.simulation import SimulationRunner
```

```python
result = SimulationRunner(seed=42).run(
    workflow,
    num_cases=500,
    arrival_interval_minutes=10.0,  # enables queueing
    engine="simple",                # or "discrete"
    collect_events=True,            # False = KPI-only (saves ~25 MB at 50k cases)
)
```

Returns a `SimulationResult` with `.kpi` (aggregated metrics) and `.events` (audit log).

### `KPIResult`
```python
from b2b_workflow_simulator.kpi import KPIResult
```

Key properties:

| Property | Type | Description |
|---|---|---|
| `completion_rate` | `float` | Fraction of cases that completed successfully |
| `failure_rate` | `float` | Fraction of cases that failed |
| `avg_cost_per_case` | `float` | Mean total cost per case |
| `avg_cycle_time_minutes` | `float` | Mean end-to-end duration per case |
| `avg_wait_time_minutes` | `float` | Mean time cases spent queued |
| `escalation_rate` | `float` | Fraction of cases with AI-to-human escalation |
| `bottleneck_nodes(n)` | method | Top-N nodes by total duration |
| `actor_utilization` | `dict[str, float]` | Fraction of capacity used per actor |

---

## Redesign analysis

### `RedesignDiff`
```python
from b2b_workflow_simulator.redesign import RedesignDiff, compare_workflows

diff = compare_workflows(before_kpi, after_kpi, implementation_cost=10_000)
```

Key attributes: `roi`, `completion_rate`, `failure_rate`, `cycle_time_minutes`,
`cost_per_case`, `before_bottlenecks`, `after_bottlenecks`.

### `WorkflowPortfolio`
```python
from b2b_workflow_simulator.portfolio import WorkflowPortfolio

portfolio = WorkflowPortfolio(name="Q3 Transformation")
portfolio.add_entry("Invoice Processing", before_kpi, after_kpi, implementation_cost)
summary = portfolio.summary()
ranked = portfolio.ranked(by="total_cost_savings")
```

---

## Monte Carlo and sensitivity

### Monte Carlo
```python
from b2b_workflow_simulator.monte_carlo import run_monte_carlo_comparison

result = run_monte_carlo_comparison(build_before, build_after, num_cases=200,
                                    seeds=list(range(1, 51)))
```

### Sensitivity sweep
```python
from b2b_workflow_simulator.sensitivity import run_sensitivity_sweep

result = run_sensitivity_sweep(build_before, build_after,
                               parameter="ai_error_rate",
                               values=[0.0, 0.05, 0.10, 0.20])
```

---

## Governance (Phase 5)

### `PolicyEvaluation`
```python
from b2b_workflow_simulator.policy import evaluate_policies, PolicyEvaluation

evaluation = evaluate_policies(workflow, policies)
```

### `ComplianceReport`
```python
from b2b_workflow_simulator.compliance import evaluate_compliance, ComplianceReport
```

### `SLAReport`
```python
from b2b_workflow_simulator.sla import evaluate_sla, SLAReport
```

### `RiskAssessment`
```python
from b2b_workflow_simulator.risk import compute_risk, RiskAssessment
```

### `RecommendationSet`
```python
from b2b_workflow_simulator.recommendation import generate_recommendations, RecommendationSet
```

### `AIAdoptionAssessment`
```python
from b2b_workflow_simulator.ai_adoption import assess_ai_adoption, AIAdoptionAssessment
```

### `ExecutiveAssessment`
```python
from b2b_workflow_simulator.executive_report import build_executive_assessment, ExecutiveAssessment
```

---

## Organization model (Phase 6)

### `Organization`
```python
from b2b_workflow_simulator.org_model import Organization, Department, Team, Role, ReportingLine

org = Organization(org_id="acme", name="Acme Corp")
org.add_department(dept).add_team(team).add_role(role)
org.validate()
```

Key methods: `teams_for_department`, `roles_for_team`, `direct_reports`,
`manager_of`, `total_headcount`, `ai_agent_count`, `org_units`.

### `OrgBudget`
```python
from b2b_workflow_simulator.budget import OrgBudget, DepartmentBudget

budget = OrgBudget(org_id="acme")
dept_budget = DepartmentBudget(dept_id="sales", annual_budget=800_000)
dept_budget.allocate("operating", 500_000)
budget.add_dept_budget(dept_budget)
```

### `SharedResourcePool`
```python
from b2b_workflow_simulator.shared_resources import SharedResource, SharedResourcePool

pool = SharedResourcePool(org_id="acme")
pool.add_resource(SharedResource(resource_id="legal", name="Legal Counsel",
                                  resource_type="legal_reviewer",
                                  capacity_minutes_per_day=240.0,
                                  actor_ids=["reviewer_actor"]))
pool.record_usage_from_kpi(workflow_id, dept_id, actor_busy_minutes)
contentions = pool.all_contentions()
```

### `GrowthProjection`
```python
from b2b_workflow_simulator.growth import GrowthConfig, project_growth

config = GrowthConfig(monthly_growth_rate=0.05, base_cases_per_month=200,
                      initial_ai_adoption=None)  # None = derive from org
projection = project_growth(org, org_budget, config)
bp = projection.first_breaking_point()
```

### `OrgHealthScore`
```python
from b2b_workflow_simulator.org_health import compute_org_health, OrgHealthScore

health = compute_org_health(org, org_budget, shared_resources, kpi_results,
                             growth_projection=projection)
print(health.overall_score, health.grade)
for risk in health.top_risks(3):
    print(risk.name, risk.score, risk.explanation)
```

---

## Phase 7 visualization and reporting

### Workflow visualization
```python
from b2b_workflow_simulator.visualization import to_mermaid, to_text, compare_text

print(to_mermaid(workflow))   # paste into mermaid.live
print(to_text(workflow))      # plain-text graph
print(compare_text(before, after))
```

### ROI waterfall
```python
from b2b_workflow_simulator.waterfall import build_roi_waterfall, waterfall_to_text, waterfall_to_svg

waterfall = build_roi_waterfall(before_kpi, after_kpi, implementation_cost=8000)
print(waterfall_to_text(waterfall))
Path("roi.svg").write_text(waterfall_to_svg(waterfall))
```

### Bottleneck heatmap
```python
from b2b_workflow_simulator.heatmap import build_bottleneck_heatmap, heatmap_to_text, heatmap_to_svg

heatmap = build_bottleneck_heatmap(workflow, kpi, shared_resources=pool)
print(heatmap_to_text(heatmap))
```

### Executive snapshot
```python
from b2b_workflow_simulator.snapshot import build_snapshot, snapshot_to_text, snapshot_to_html

snapshot = build_snapshot(before_kpi, after_kpi, implementation_cost=8000)
print(snapshot_to_text(snapshot))
Path("snap.html").write_text(snapshot_to_html(snapshot))
```

### Assumption profiles
```python
from b2b_workflow_simulator.assumptions import AssumptionProfile, save_assumption_profile, load_assumption_profile

profile = AssumptionProfile(num_cases=500, seed=1, implementation_cost=10_000)
save_assumption_profile(profile, "base.json")
loaded = load_assumption_profile("base.json")
```

### Consultant packet
```python
from b2b_workflow_simulator.packet import generate_packet

files = generate_packet("invoice-processing", before_wf, after_wf,
                        before_result, after_result, profile,
                        output_dir=Path("packet/"))
```

---

## CLI summary

| Command | Phase | Description |
|---|---|---|
| `run-example` | 1 | Before/after KPI comparison |
| `compare-example` | 1 | Full ROI report |
| `html-report-example` | 3 | Static HTML redesign report |
| `sensitivity-example` | 3 | 1D parameter sweep |
| `sensitivity-grid-example` | 3 | 2D ROI matrix |
| `monte-carlo-example` | 4 | Monte Carlo comparison |
| `capacity-analysis` | 4 | Staffing recommendations |
| `policy-analysis` | 5 | Governance policy check |
| `compliance-analysis` | 5 | Compliance audit |
| `risk-analysis` | 5 | Organizational risk score |
| `readiness-analysis` | 5 | AI adoption readiness |
| `recommend-redesign` | 5 | Actionable recommendations |
| `executive-report` | 5 | Full executive assessment |
| `run-org` | 6 | Multi-workflow org simulation |
| `org-health` | 6 | Org health score |
| `org-budget-analysis` | 6 | Budget utilization |
| `org-resource-contention` | 6 | Shared resource bottlenecks |
| `org-growth-projection` | 6 | 12-month growth forecast |
| `org-restructure-scenario` | 6 | Restructuring impact analysis |
| `org-executive-report` | 6 | Org executive report |
| `visualize-workflow` | 7 | Mermaid / text graph |
| `roi-waterfall` | 7 | ROI decomposition chart |
| `bottleneck-heatmap` | 7 | Node pressure heatmap |
| `executive-snapshot` | 7 | One-page stakeholder summary |
| `consultant-packet` | 7 | Full deliverable directory |
| `generate-example-gallery` | 7 | Regenerate gallery outputs |
