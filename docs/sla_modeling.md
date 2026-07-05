# SLA Modeling

Policies and compliance requirements (`docs/policy_engine.md`,
`docs/compliance.md`) are checked against a workflow's *structure* -- do the
right gates and controls exist in the graph? SLAs are different: they are
checked against what actually happened during a simulation run, because
"did we respond within the deadline?" is a question about timing, not
shape. `sla.py` defines three kinds of service-level agreement, replays a
`SimulationResult`'s event log per case, and reports attainment, breach
counts, average breach duration, breach causes, and an optional estimated
financial penalty.

## SLA types

- **`CompletionSLA`** -- the whole case must reach a terminal state
  (completed or failed) within `deadline_minutes` of arrival.
- **`ResponseSLA`** -- the first execution of `node_id` must start within
  `deadline_minutes` of the case's arrival. Models rules like "a ticket
  must be triaged within 15 minutes."
- **`EscalationSLA`** -- once `node_id` raises an escalation, some
  follow-up action (a new task starting, or the case ending) must occur
  within `deadline_minutes` of the escalation. Models rules like "an
  escalated case must be picked up within an hour."

Every SLA type accepts an optional `penalty_per_minute`; when set, a breach
is costed at `breach_minutes * penalty_per_minute` and rolled up into
`SLAReport.total_penalty`.

```python
from b2b_workflow_simulator.sla import CompletionSLA, ResponseSLA, evaluate_sla, generate_sla_report
from b2b_workflow_simulator.simulation import SimulationRunner

slas = [
    CompletionSLA(
        name="invoice-cycle-time",
        deadline_minutes=120.0,
        penalty_per_minute=0.50,
        description="Invoices should clear intake through payment scheduling within 2 hours.",
    ),
    ResponseSLA(
        name="approval-response-time",
        node_id="approval",
        deadline_minutes=60.0,
        description="An invoice should reach the approval stage within an hour of intake.",
    ),
]

result = SimulationRunner(seed=1).run(workflow, num_cases=300)
report = evaluate_sla(result, slas)
print(generate_sla_report(report))
```

There is no dedicated CLI command for the SLA engine alone -- SLA results
appear as a section of the executive report (`b2b-simulator executive-report`,
see `docs/ai_adoption.md`), since SLA attainment is usually reviewed
alongside the other governance and risk signals rather than in isolation.

## Attainment, breaches, and penalties

`evaluate_sla(result, slas)` groups `result.events` by `case_id`, checks
every SLA rule against every case it applies to, and returns an `SLAReport`:

- **`attainment_rate`** -- the fraction of applicable (rule, case) checks
  that met their deadline. A case for which a rule does not apply (e.g. a
  `ResponseSLA` for a node the case never reached) is excluded from the
  denominator entirely, rather than counted as a pass or a fail.
- **`breach_count`** / **`breaches`** -- the total number of missed
  deadlines and the full list of `SLABreach` records (rule, case, node,
  actual vs. deadline minutes, and penalty if configured).
- **`average_breach_minutes`** -- how far over deadline, on average, a
  breach ran; useful for distinguishing "breaches by a hair" from
  "breaches that blow past the deadline."
- **`breach_causes()`** -- breach counts grouped by rule name, so a report
  can show which specific SLA is driving most of the misses.
- **`total_penalty`** -- the sum of every breach's estimated financial
  penalty, `0.0` if no rule configured `penalty_per_minute`.

## Worked example: does capacity-aware queueing blow the response SLA?

```python
from b2b_workflow_simulator.sla import ResponseSLA, evaluate_sla, generate_sla_report
from b2b_workflow_simulator.simulation import SimulationRunner

sla = ResponseSLA(name="triage-response-time", node_id="triage", deadline_minutes=15.0)

light_load = SimulationRunner(seed=1).run(workflow, num_cases=200, arrival_interval_minutes=20.0)
heavy_load = SimulationRunner(seed=1).run(workflow, num_cases=200, arrival_interval_minutes=4.0)

print(generate_sla_report(evaluate_sla(light_load, [sla])))
print(generate_sla_report(evaluate_sla(heavy_load, [sla])))
```

Under light arrival load, queueing rarely pushes a case's first triage past
15 minutes, so attainment stays near 100%. Under heavy load, the same
workflow and the same SLA rule show a materially lower attainment rate and
a nonzero average breach duration -- the SLA engine turns "utilization is
high" (a capacity signal) into "customers are actually waiting too long" (a
service-level signal), which is the number that matters to a customer
contract or an internal service-level review.

## What this model does not do

- It does not enforce SLAs during simulation (an SLA is measured after the
  fact by replaying the event log, not used to change scheduling
  decisions -- a case that would breach an SLA is not prioritized
  differently by the scheduler).
- It does not model SLA rules that depend on more than one node's timing
  relative to each other beyond the three built-in shapes (completion,
  first response, post-escalation follow-up).
- It does not aggregate penalties into the ROI/redesign diff engine
  automatically -- `SLAReport.total_penalty` is reported alongside, not
  folded into, `RedesignDiff`'s cost savings figure, since whether an SLA
  penalty is a real cash cost or an internal target varies by organization.
