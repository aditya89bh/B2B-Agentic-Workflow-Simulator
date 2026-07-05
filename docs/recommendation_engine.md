# Recommendation Engine

Every other Phase 5 engine reports on a workflow: what policies it
violates, how compliant it is, how risky it is. `recommendation.py` is the
one that talks back -- it turns those observations into a prioritized list
of concrete, actionable suggestions, each with reasoning, affected KPIs, an
expected benefit, and a confidence level, rather than leaving the reader to
infer what to do next from a pile of metrics.

## Recommendation kinds

`generate_recommendations(workflow, kpi, risk_assessment=None)` inspects
the workflow's structure and simulated KPIs and can emit any of the
following:

- **Automate task** -- a human-staffed node that runs on nearly every case
  (default threshold: 80%+ of cases) and has no approval semantics in its
  name is flagged as a strong automation candidate.
- **Keep human review** -- an AI agent with a high error rate or escalation
  rate (10%+) is flagged as unsafe to run fully autonomously; if a
  `risk_assessment` is supplied, its matching AI Failure factor is quoted
  directly in the reasoning.
- **Increase / reduce staffing** -- any actor or pool at 90%+ utilization
  gets an increase-staffing recommendation; any at or below 20% gets a
  reduce-staffing recommendation. Confidence is upgraded to high when a
  matching `RiskFactor` in the Staffing category corroborates it.
- **Merge activities** -- two nodes that always flow directly into each
  other (100% probability edge) and are staffed by the same actor are
  flagged as candidates for merging, since the split adds handoff overhead
  without changing who does the work.
- **Split activities** -- a node whose average simulated duration is more
  than 2x the workflow's average is flagged as possibly bundling multiple
  distinct pieces of work.
- **Introduce memory-enabled agent** -- an AI agent with a low error rate
  but a high escalation rate (15%+) suggests escalations stem from missing
  context rather than poor execution, a case for giving the agent memory of
  prior interactions rather than replacing it.
- **Introduce approval gate** -- a node whose name or ID suggests a
  financially or contractually sensitive action (payment, disbursement,
  refund, contract, payout) with no upstream approval step is flagged.
- **Remove unnecessary approval** -- an approval-named node that has run
  several times (5+) and never produced a failure is flagged as a possible
  rubber stamp worth reconsidering.
- **Redesign escalation path** -- an AI agent with a high escalation rate
  (20%+) sitting inside a retry loop is flagged, since routing an
  escalation back through the same loop that already failed risks cases
  cycling indefinitely.

```python
from b2b_workflow_simulator.recommendation import (
    generate_recommendations,
    generate_recommendation_report,
)
from b2b_workflow_simulator.risk import compute_risk
from b2b_workflow_simulator.simulation import SimulationRunner

result = SimulationRunner(seed=1).run(workflow, num_cases=300)
risk_assessment = compute_risk(workflow, result.kpi)
recommendations = generate_recommendations(workflow, result.kpi, risk_assessment)
print(generate_recommendation_report(recommendations))
```

`risk_assessment` is optional; when omitted, staffing and AI-related
recommendations are still generated, just without the risk engine's
specific factor descriptions folded into their reasoning.

From the CLI:

```bash
b2b-simulator recommend-redesign invoice-processing --variant after --cases 300
b2b-simulator recommend-redesign invoice-processing --variant after --html-output recommendations.html
```

## Every recommendation is explainable

Every `Recommendation` is a frozen dataclass with five required fields, by
design, so a recommendation can never be presented without justification:

- **`reasoning`** -- a specific, data-backed explanation of why this
  recommendation fired for this workflow.
- **`affected_kpis`** -- which `KPIResult` metrics this change would move
  (e.g. `total_cost`, `avg_cycle_time_minutes`), so the recommendation can
  be checked against a follow-up simulation run after acting on it.
- **`expected_benefit`** -- a plain-language statement of the intended
  outcome.
- **`confidence`** -- `"high"`, `"medium"`, or `"low"`, reflecting how
  strong the evidence is: structural facts (e.g. an unreliable AI agent's
  measured error rate) generally warrant higher confidence than heuristic
  pattern matches (e.g. "this node's name contains 'approval'").

`RecommendationSet.recommendations` is sorted by confidence, highest first,
so the most actionable items lead the report.

## Worked example: from risk factors to a fix

Running the risk engine and the recommendation engine back to back on the
same workflow shows how they connect:

```bash
b2b-simulator risk-analysis invoice-processing --variant after --cases 300
b2b-simulator recommend-redesign invoice-processing --variant after --cases 300
```

Where the risk report identifies *that* `approval_agent` is a single point
of failure performing three stages, the recommendation report's staffing
and human-review recommendations point at *what to do about it* -- e.g.
flagging that stage for continued human review given its escalation rate,
or recommending additional staffing if utilization is also high. Neither
report replaces the other: risk quantifies exposure, recommendations
propose a response.

## What this model does not do

- It does not rank recommendations by expected dollar impact -- confidence
  level reflects evidence strength, not magnitude of benefit; two
  recommendations at the same confidence level are not necessarily equally
  valuable.
- It does not verify that acting on a recommendation actually improves the
  workflow -- that requires building the proposed change as a new
  `Workflow` variant and re-running the simulation/redesign diff, the same
  workflow used to build every bundled "after" example in this repository.
- It does not learn from historical outcomes across multiple workflows;
  each `generate_recommendations()` call reasons purely from the one
  workflow and KPI result it is given.
