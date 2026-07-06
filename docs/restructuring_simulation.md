# Restructuring Simulation

`restructuring.py` evaluates organizational design changes analytically,
applying directional heuristics to the current KPI baseline to project cost,
cycle-time, risk, staffing, and budget impacts.

## Scenario types

| Constant | Label | Typical effect |
|---|---|---|
| `CENTRALIZE_TEAM` | Centralize Team | Reduces cost and duplication; mild risk reduction |
| `DECENTRALIZE_TEAM` | Decentralize Team | Cuts cycle time; slight cost increase |
| `ADD_SHARED_SERVICES` | Add Shared Services Function | Reduces cost; adds coordination overhead |
| `OUTSOURCE_STAGE` | Outsource Workflow Stage | Variable cost; increases vendor risk |
| `CREATE_AI_OPS_TEAM` | Create AI Operations Team | Largest cost and cycle-time reduction |
| `HIRE_ADDITIONAL_STAFF` | Hire Additional Staff | Reduces cycle time at hiring cost |
| `REDUCE_APPROVAL_LAYERS` | Reduce Approval Layers | Cuts cycle time; increases process risk |

## Evaluating a single scenario

```python
from b2b_workflow_simulator.restructuring import (
    CREATE_AI_OPS_TEAM,
    RestructuringScenario,
    evaluate_restructuring,
)

scenario = RestructuringScenario(
    scenario_id="ai-ops",
    scenario_type=CREATE_AI_OPS_TEAM,
    description="Create a dedicated AI Operations team",
    parameters={"headcount_delta": 2, "cost_reduction_fraction": 0.15},
)

impact = evaluate_restructuring(org, kpi_results, scenario, org_budget)
print(f"Cost impact:   ${impact.cost_impact:+,.0f}/year")
print(f"Cycle time:    {impact.cycle_time_impact_minutes:+.1f} min")
print(f"Risk delta:    {impact.risk_delta:+.1f}")
print(f"Staffing:      {impact.staffing_delta:+d}")
print(f"Is cost positive: {impact.is_cost_positive}")
print(f"Is risk positive: {impact.is_risk_positive}")
for rec in impact.recommendations:
    print(f"  - {rec}")
```

## Comparing multiple scenarios

```python
from b2b_workflow_simulator.restructuring import (
    CENTRALIZE_TEAM, HIRE_ADDITIONAL_STAFF, REDUCE_APPROVAL_LAYERS,
    RestructuringScenario, compare_restructuring_scenarios,
    generate_restructuring_report,
)

scenarios = [
    RestructuringScenario("s1", CENTRALIZE_TEAM, "Centralize sales ops"),
    RestructuringScenario("s2", HIRE_ADDITIONAL_STAFF, "Add 2 CS agents",
                          parameters={"headcount_delta": 2}),
    RestructuringScenario("s3", REDUCE_APPROVAL_LAYERS, "Remove 1 approval layer",
                          parameters={"approval_layers_removed": 1}),
]

impacts = compare_restructuring_scenarios(org, kpi_results, scenarios, org_budget)
print(generate_restructuring_report(impacts))
```

Results are sorted by `net_benefit_score`, a composite of cost savings (40%),
cycle-time reduction (30%), and risk reduction (30%).

## Tunable parameters

Each scenario type recognizes specific keys in `parameters`:

| Key | Type | Used by |
|---|---|---|
| `headcount_delta` | int | All types |
| `cost_reduction_fraction` | float (0–1) | `CENTRALIZE_TEAM`, `CREATE_AI_OPS_TEAM`, `ADD_SHARED_SERVICES` |
| `cycle_time_reduction_fraction` | float (0–1) | Most types |
| `approval_layers_removed` | int | `REDUCE_APPROVAL_LAYERS` |
| `outsource_cost_per_case` | float | `OUTSOURCE_STAGE` |
| `hourly_cost_per_hire` | float | `HIRE_ADDITIONAL_STAFF` |

## CLI

```bash
b2b-simulator org-restructure-scenario create_ai_ops_team \
  --cases 200 --seed 42
```
