# Budget Modeling

`budget.py` provides a lightweight departmental budget layer for the
organizational digital twin.  It tracks how much each department has allocated
across standard categories, records spend, surfaces overruns, and feeds the
budget pressure signal used by the org health score.

## Budget categories

| Constant | Label |
|---|---|
| `OPERATING` | Operating |
| `IMPLEMENTATION` | Implementation |
| `AI_TOOLING` | AI Tooling |
| `HIRING` | Hiring |
| `TRAINING` | Training |

## Building a department budget

```python
from b2b_workflow_simulator.budget import (
    AI_TOOLING, HIRING, OPERATING, TRAINING,
    DepartmentBudget, OrgBudget,
)

sales_budget = DepartmentBudget(dept_id="sales", annual_budget=800_000.0)
sales_budget.allocate(OPERATING, 500_000.0)
sales_budget.allocate(HIRING,    150_000.0)
sales_budget.allocate(AI_TOOLING, 100_000.0)
sales_budget.allocate(TRAINING,   50_000.0)

# Record spend as the simulation runs
sales_budget.record_spend(OPERATING, 120_000.0)

print(f"Utilization: {sales_budget.utilization:.1%}")
print(f"Remaining:   ${sales_budget.remaining_budget:,.0f}")
print(f"Overrun:     {sales_budget.has_overrun}")
```

## Organization-level budget

```python
org_budget = OrgBudget(org_id="acme")
org_budget.add_dept_budget(sales_budget)
# ... add more department budgets

print(f"Total budget:      ${org_budget.total_budget:,.0f}")
print(f"Total spent:       ${org_budget.total_spent:,.0f}")
print(f"Overall util:      {org_budget.overall_utilization:.1%}")
print(f"Departments over:  {org_budget.overrun_departments()}")
print(f"Spend by category: {org_budget.spend_by_category()}")
```

## Budget pressure score

`OrgBudget.budget_pressure_score()` returns a 0–100 scalar used by the org
health engine.  It combines overall utilization (80 points max) with the
fraction of departments that are over budget (20 points max).

## Bundled example

`b2b_workflow_simulator.examples.saas_org.build_saas_org_budget()` returns a
ready-to-use `OrgBudget` for the six-department SaaS company with realistic
allocation amounts.
