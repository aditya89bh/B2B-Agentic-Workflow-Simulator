# Organizational Health Score

`org_health.py` distils the state of an organization into a single 0–100 score
across eight weighted dimensions.  Higher is healthier.  A letter grade (A–F)
makes the overall result easy to communicate to non-technical stakeholders.

## Eight health dimensions

| Dimension | Weight | Measures |
|---|---|---|
| Utilization Balance | 1.5 | Actor workload spread + shared resource bottlenecks |
| Queue Pressure | 1.5 | Case wait time + critically overloaded shared resources |
| Budget Pressure | 1.0 | Spend vs. budget + near-term budget breaking points |
| Compliance Risk | 1.0 | Workflow failure rate as a compliance proxy |
| SLA Risk | 1.0 | Escalation rate, peak cycle time + growth breaking points |
| AI Readiness | 1.0 | AI agent fraction and AI escalation rate |
| Single Points of Failure | 1.5 | High-utilization actors, single-role depts, bottleneck shared resources |
| Workflow Concentration Risk | 0.5 | Workflows-per-team as coordination concentration proxy |

## Computing the score

```python
from b2b_workflow_simulator.org_health import compute_org_health, generate_org_health_report

health_score = compute_org_health(
    org=org,
    org_budget=org_budget,        # optional; improves budget pressure accuracy
    shared_resources=pool,        # optional; affects util balance, queue pressure, SPOF
    kpi_results=kpi_results,      # dict[workflow_id, KPIResult]
    growth_projection=projection, # optional; affects SLA risk and budget pressure
)

print(f"Score: {health_score.overall_score:.1f}/100  Grade: {health_score.grade}")
print(generate_org_health_report(health_score))
```

## Accessing individual factors

```python
from b2b_workflow_simulator.org_health import AI_READINESS, BUDGET_PRESSURE

ai_factor = health_score.factor(AI_READINESS)
print(f"{ai_factor.name}: {ai_factor.score:.1f}/100")
print(f"  {ai_factor.explanation}")

# Three worst-scoring dimensions (biggest risks)
for risk in health_score.top_risks(3):
    print(f"  {risk.name}: {risk.score:.1f} — {risk.explanation}")
```

## Grade thresholds

| Grade | Minimum score |
|---|---|
| A | 90 |
| B | 80 |
| C | 70 |
| D | 60 |
| F | < 60 |

## CLI

```bash
b2b-simulator org-health --cases 200 --seed 42 --html-output health.html
```

## Interpretation notes

- **Utilization Balance** and **Single Points of Failure** carry weight 1.5
  because overloaded or isolated actors are the most common cause of workflow
  breakdown in practice.
- **Cross-Team Dependency** carries weight 0.5 because some cross-team
  coordination is expected and healthy; only extreme fragmentation is penalised.
- All scores are analytical approximations derived from simulation KPIs and the
  org model.  They are directional signals, not audited measurements.
