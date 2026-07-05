# Organizational Risk Engine

KPIs describe what happened. Policy and compliance evaluations describe
whether the workflow's structure is allowed. `risk.py` answers a third
question that none of those cover on their own: "how exposed is this
organization, going forward, to this workflow failing in some way?"
`compute_risk()` scores a workflow across six risk categories and produces
an explainable list of `RiskFactor` records backing each score, so a risk
score is never just a number without a reason attached.

## Risk categories

`RiskAssessment.category_scores` holds one 0-100 score per category, capped
at 100 even if the underlying factors would sum higher:

- **Operational** -- driven by the simulated failure rate and how much of
  average cycle time is spent waiting in a queue rather than being worked.
- **Compliance** -- driven by an attached `PolicyEvaluation` and/or
  `ComplianceReport`, when supplied; stays at zero if neither is provided,
  since compliance risk without governance data would just be a guess.
- **AI Failure** -- driven by every AI agent's error rate and escalation
  rate, plus a check for whether each AI-operated node has a reachable
  human fallback if the agent fails outright.
- **Staffing** -- driven by actor and pool utilization from the KPI result;
  any resource at or above 90% utilization contributes a factor, scaled by
  how far over the threshold it runs.
- **Process Complexity** -- driven by node/edge count, average branching
  factor, and whether any nodes participate in a retry/rework cycle.
- **Single Point of Failure** -- driven by how many distinct workflow
  stages are all assigned to the same non-pooled actor; an actor performing
  several stages means its unavailability halts all of them at once.

```python
from b2b_workflow_simulator.risk import compute_risk, generate_risk_report
from b2b_workflow_simulator.simulation import SimulationRunner

result = SimulationRunner(seed=1).run(workflow, num_cases=300)
assessment = compute_risk(workflow, result.kpi)
print(generate_risk_report(assessment))
```

Passing an optional `policy_evaluation` and/or `compliance_report` sharpens
the Compliance category with real violation data instead of leaving it at
zero:

```python
from b2b_workflow_simulator.compliance import evaluate_compliance
from b2b_workflow_simulator.policy import evaluate_policies
from b2b_workflow_simulator.risk import compute_risk

policy_evaluation = evaluate_policies(workflow, policies)
compliance_report = evaluate_compliance(workflow, requirements)
assessment = compute_risk(workflow, result.kpi, policy_evaluation, compliance_report)
```

From the CLI:

```bash
b2b-simulator risk-analysis invoice-processing --variant after --cases 300
b2b-simulator risk-analysis invoice-processing --variant after --arrival-interval 8 --html-output risk.html
```

## Overall score and explainability

`RiskAssessment.overall_score` is the average of the six category scores.
Every category score is backed by zero or more `RiskFactor` records
(`assessment.factors_for(category)`), each carrying a human-readable
`description` and a `weight` -- the score is always the sum of its factors'
weights (capped at 100), never a magic number computed some other way.
`assessment.top_factors(n)` returns the highest-weighted factors across
every category, which is what an executive report should lead with: not
"AI Failure is 80/100" on its own, but "'erp_entry' has no reachable human
fallback if the AI agent fails" as the specific, actionable reason why.

## Worked example: quantifying a single point of failure introduced by a redesign

The bundled invoice processing example's "after" (AI-augmented) variant
assigns `approval`, `erp_entry`, and `payment_scheduling` all to the same
`approval_agent` actor -- a single point of failure that a KPI comparison
alone would never surface, since cost and cycle time both look strictly
better under the redesign:

```bash
b2b-simulator risk-analysis invoice-processing --variant after --cases 300
```

The report's Single Point of Failure category scores well above zero, with
a factor explicitly naming the actor and the three stages it alone
performs. That is the concrete, board-ready version of "don't put all your
eggs in one basket" -- a specific actor, a specific list of stages, and a
specific consequence if that actor becomes unavailable.

## What this model does not do

- It does not simulate the risk events themselves (e.g. it does not run a
  scenario where the sole approval actor is actually taken offline; it
  identifies the exposure structurally and via observed rates, not through
  fault injection).
- It does not weight categories against each other by business importance
  -- `overall_score` is a simple unweighted average across all six
  categories; a caller who considers compliance risk more severe than
  process complexity for their organization should weight the category
  scores themselves before combining them.
- It does not track risk trends across multiple runs or workflow revisions
  (each `compute_risk()` call is a point-in-time snapshot, the same way
  `compare_workflows()` snapshots two `KPIResult` objects rather than
  tracking history).
