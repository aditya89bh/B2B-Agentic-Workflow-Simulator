# Org Growth Projection

`growth.py` generates a 12-month forward view of case volume, cost, headcount,
budget, AI adoption, and capacity utilization.  It identifies *breaking points*:
months where the organization can no longer absorb incoming demand under current
staffing or budget assumptions.

## GrowthConfig parameters

| Parameter | Default | Description |
|---|---|---|
| `monthly_growth_rate` | 0.05 | Fractional MoM case volume increase |
| `seasonal_multipliers` | `[1.0] * 12` | Per-month demand multipliers (Jan–Dec) |
| `headcount_growth_rate` | 0.0 | Fractional MoM headcount increase |
| `ai_adoption_increase_rate` | 0.0 | Monthly increment in AI adoption (0–1) |
| `initial_ai_adoption` | `None` | Starting AI adoption (0–1). When `None`, automatically derived from `org.ai_agent_count() / org.total_headcount()` so an org already 30% AI-staffed begins the projection at 0.30. Set explicitly to override. |
| `budget_increase_rate` | 0.0 | Fractional MoM budget increase |
| `base_cases_per_month` | 200 | Baseline monthly case volume |
| `base_cost_per_case` | 100.0 | Baseline cost per completed case |
| `base_headcount` | 10 | Starting headcount |
| `actor_capacity_per_head` | 480.0 | Available minutes per person per day |
| `simulation_days_per_month` | 22 | Working days per month |

## Running a projection

```python
from b2b_workflow_simulator.growth import GrowthConfig, project_growth, generate_growth_report
from b2b_workflow_simulator.examples.saas_org import build_saas_org, build_saas_org_budget

org = build_saas_org()
org_budget = build_saas_org_budget()

config = GrowthConfig(
    monthly_growth_rate=0.08,       # 8% MoM growth
    base_cases_per_month=200,
    base_headcount=18,
    headcount_growth_rate=0.02,     # hire 2% more people each month
    ai_adoption_increase_rate=0.03, # AI adoption grows +3pp/month
)

projection = project_growth(org, org_budget, config)
print(generate_growth_report(projection))
```

## Accessing specific horizons

```python
for point in projection.three_month():
    print(f"Month {point.month}: {point.projected_cases} cases, "
          f"${point.projected_cost:,.0f} cost, "
          f"{point.capacity_utilization:.1%} utilization")

for point in projection.six_month():
    ...

for point in projection.twelve_month():
    ...
```

## Breaking points

A breaking point is flagged when either:

- Projected demand minutes exceed available capacity minutes (capacity overload).
- Projected cost exceeds projected monthly budget by more than 15% (budget
  overload).

```python
bp = projection.first_breaking_point()
if bp:
    print(f"Breaking point at month {bp.month}: {bp.breaking_point_reason}")
else:
    print("No breaking points within 12-month horizon.")

for bp in projection.breaking_points():
    print(f"  Month {bp.month}: {bp.breaking_point_reason}")
```

## CLI

```bash
b2b-simulator org-growth-projection \
  --monthly-growth-rate 0.08 \
  --base-cases 200 \
  --base-headcount 18 \
  --headcount-growth 0.02 \
  --ai-adoption-rate 0.03 \
  --html-output growth.html
```
