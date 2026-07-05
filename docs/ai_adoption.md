# AI Adoption Assessment

Every other Phase 5 engine can be run on a workflow that has no AI agents
in it at all. `ai_adoption.py` asks a more pointed question that only
matters once AI is on the table: *is this workflow, as simulated, actually
ready for AI to take on more of it, and if so, how much?* `assess_ai_adoption()`
scores six dimensions and combines them into a single readiness index with
a concrete rollout recommendation.

## The six scores

- **Automation readiness** -- combines the current fraction of nodes
  already running on AI agents with the workflow's overall simulated
  stability (`1 - failure_rate`), on the reasoning that a workflow already
  succeeding reliably is a safer base to automate further.
- **AI maturity** -- for workflows with AI agents, the average error rate
  and escalation rate across every distinct agent in use, inverted into a
  0-100 score (100 = flawless, 0 = highly unreliable). Zero for workflows
  with no AI agents at all -- there is no track record to score.
- **Human dependency** -- the share of simulated task volume still
  requiring a human actor. Falls back to a structural count of human-staffed
  nodes if the KPI result has no per-node visit data.
- **Governance score** -- sharpened by an optional `PolicyEvaluation`: fewer
  policy violations (weighted by severity) means a higher score. Without a
  policy evaluation, falls back to a structural check of how many AI-staffed
  nodes have a reachable human fallback if the agent fails.
- **Explainability score** -- the inverse of AI agents' average escalation
  rate: an agent that frequently defers to a human is, by that same signal,
  less able to resolve cases autonomously and explainably.
- **Rollout complexity** -- driven by workflow size, average branching
  factor, and the number of multi-resource task executions (which require
  coordinating multiple actors, adding operational complexity beyond a
  single-actor AI rollout).

```python
from b2b_workflow_simulator.ai_adoption import assess_ai_adoption, generate_ai_adoption_report
from b2b_workflow_simulator.simulation import SimulationRunner

result = SimulationRunner(seed=1).run(workflow, num_cases=300)
assessment = assess_ai_adoption(workflow, result.kpi)
print(generate_ai_adoption_report(assessment))
```

Passing an optional `policy_evaluation` sharpens the governance score with
real violation data:

```python
from b2b_workflow_simulator.ai_adoption import assess_ai_adoption
from b2b_workflow_simulator.policy import evaluate_policies

policy_evaluation = evaluate_policies(workflow, policies)
assessment = assess_ai_adoption(workflow, result.kpi, policy_evaluation)
```

From the CLI:

```bash
b2b-simulator readiness-analysis invoice-processing --variant after --cases 300
b2b-simulator readiness-analysis invoice-processing --variant after --html-output readiness.html
```

## Readiness index and rollout recommendation

`readiness_index` averages all six scores (using AI maturity when AI agents
are present, automation readiness as a substitute when there are none), and
`recommendation` maps that index to one of four outcomes:

- **Full deployment** -- readiness index at or above 75, with governance
  above the safety floor.
- **Phased rollout** -- readiness index at or above 55.
- **Pilot** -- readiness index at or above 35, *or* readiness is higher but
  governance score is below 40 -- a low governance score caps the
  recommendation at a pilot regardless of how strong the other five scores
  are, since rolling out further without adequate governance is exactly the
  failure mode this engine exists to prevent.
- **Not recommended** -- readiness index below 35.

Every `AIAdoptionAssessment` carries a `reasoning` tuple explaining each
score and the final recommendation in plain language, so the recommendation
is never presented as a bare label.

## Executive assessment report

`executive_report.py` bundles every Phase 5 engine's output for one
workflow into a single `ExecutiveAssessment`: KPI summary, ROI (if a
`RedesignDiff` is supplied), SLA performance, compliance, policy
violations, organizational risk, recommendations, and this AI adoption
assessment, in that order.

```python
from b2b_workflow_simulator.executive_report import (
    build_executive_assessment,
    generate_executive_report,
)
from b2b_workflow_simulator.redesign import compare_workflows

diff = compare_workflows(before_result.kpi, after_result.kpi, implementation_cost=8000.0)
assessment = build_executive_assessment(
    after_workflow,
    after_result.kpi,
    redesign_diff=diff,
    policy_evaluation=policy_evaluation,
    compliance_report=compliance_report,
    sla_report=sla_report,
)
print(generate_executive_report(assessment))
```

Every optional argument that is omitted renders as a clearly labeled
"omitted" section rather than being silently skipped, so a reader always
knows whether a section is missing because it does not apply or because the
data was not supplied.

From the CLI, a single command runs both workflow variants, evaluates every
attached policy/compliance/SLA definition for the bundled example, and
prints (or writes as HTML) the full report:

```bash
b2b-simulator executive-report invoice-processing --cases 300 --implementation-cost 8000
b2b-simulator executive-report invoice-processing --cases 300 --html-output executive.html
```

## Worked example: is the AI-augmented invoice workflow ready for full deployment?

```bash
b2b-simulator readiness-analysis invoice-processing --variant after --cases 300
b2b-simulator executive-report invoice-processing --cases 300 --implementation-cost 8000
```

The bundled example's AI agents run at low error and escalation rates, and
the attached governance policies pass cleanly, so the readiness assessment
typically recommends full deployment or a phased rollout -- but the
executive report in the same run also surfaces the segregation-of-duties
compliance gap covered in `docs/compliance.md`. That combination -- "ready
to deploy, but fix this control gap first" -- is exactly the nuanced,
multi-signal read an executive report exists to produce, instead of a
single readiness number that would either overstate confidence or bury a
real caveat.

## What this model does not do

- It does not measure actual AI model quality or benchmark performance --
  every score is derived from the `AIAgentActor` parameters used in
  simulation (`error_rate`, `escalation_rate`) and the workflow's
  structure, not from evaluating a real model.
- It does not account for organizational change-management readiness
  (training, stakeholder buy-in, process documentation) beyond what is
  captured structurally as governance and documentation requirements in
  `compliance.py`.
- It does not simulate a phased rollout itself -- the recommendation is a
  single categorical outcome; modeling what a phased rollout's own
  intermediate KPIs would look like requires building and simulating an
  intermediate workflow variant, the same way "before" and "after" variants
  are built for redesign comparisons.
