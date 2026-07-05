# Sensitivity Analysis

A redesign diff answers "does this redesign pay off, given our current
assumptions about AI cost, error rates, and staffing?" Sensitivity
analysis answers the follow-up question every stakeholder actually
asks: "how confident should we be in those assumptions, and how much
can they move before the answer changes?"

This page covers varying one assumption at a time. For sweeping two
assumptions together over a grid (e.g. AI cost and AI error rate moving
in tandem), see `docs/advanced_sensitivity.md`.

## The sweep engine

`run_sensitivity_sweep()` in `sensitivity.py` re-simulates a before/after
workflow pair once per value of a single parameter, holding everything
else fixed (including the random seed, so only the swept parameter
drives the change in outcome):

```python
from b2b_workflow_simulator.examples.invoice_processing import (
    build_after_workflow,
    build_before_workflow,
)
from b2b_workflow_simulator.sensitivity import format_sensitivity_table, run_sensitivity_sweep

result = run_sensitivity_sweep(
    build_before_workflow,
    build_after_workflow,
    parameter="ai_cost_per_execution",
    values=[0.0, 5.0, 10.0, 20.0, 40.0],
    num_cases=300,
    seed=7,
)
print(format_sensitivity_table(result))
```

`build_before`/`build_after` are zero-argument callables that return a
*fresh* `Workflow` each time -- exactly the shape of the `build_before_workflow`/
`build_after_workflow` functions every bundled example already exposes.
This matters because the sweep mutates a copy of the workflow at each
value; passing a function that returns a cached, shared `Workflow`
instance would still work correctly (the sweep defensively deep-copies
its inputs), but is not the intended usage pattern.

## Supported parameters

| `parameter` | What it changes | Applied to |
|---|---|---|
| `ai_error_rate` | `error_rate` on every `AIAgentActor` | "after" workflow only |
| `ai_cost_per_execution` | `cost_per_execution` on every `AIAgentActor` | "after" workflow only |
| `human_hourly_cost` | `hourly_cost` on every `HumanActor` | both workflows (labor cost inflation affects the whole market, not just the redesign) |
| `arrival_interval` | `arrival_interval_minutes` passed to the simulation runner | both workflows |
| `implementation_cost` | The one-time cost used in the ROI/payback calculation | not simulated at all -- see below |

`implementation_cost` is a special case: it never affects the
simulation, only the ROI calculation on top of it. The sweep engine
recognizes this and simulates each workflow exactly once, reusing the
result across every value instead of re-running an identical simulation
redundantly.

## Reading the table

```
Sensitivity: ai_cost_per_execution
       Value      Cost Savings     ROI %  Completion After
----------------------------------------------------------
           0          7,699.43    +85.8%             91.3%
           5          2,044.43    +22.8%             91.3%
          10         -3,610.57    -40.2%             91.3%
          20        -14,920.57   -166.2%             91.3%

Break-even for cost savings occurs between ai_cost_per_execution = 5 and 10.
```

Each row is one simulated value. "Cost Savings" and "ROI %" come from
the `RedesignDiff` computed at that value; "Completion After" is
included because some parameters (notably `ai_error_rate`) trade cost
savings against completion rate in a way the cost column alone would
hide -- a redesign that "saves money" by failing cases faster is not
actually a win.

## Break-even detection

`SensitivityResult.break_even_range(metric=...)` scans consecutive
points (in the order `values` was supplied) for a sign change in
`metric` (total cost savings by default) and returns the bracketing
`(lower, upper)` pair of parameter values where the crossing happens.
This is deliberately a *range*, not a single interpolated point: with
only a handful of simulated values, claiming false precision about the
exact break-even value would overstate what the sweep actually
measured. If you need a tighter estimate, supply more values in the
range identified by the first pass.

If the metric never changes sign across the supplied values, the sweep
reports that plainly rather than guessing -- either the range tested
was too narrow, or the redesign is robust to that parameter across the
entire range you tested (a genuinely useful thing to know).

## Worked example: how expensive can the AI get?

```bash
b2b-simulator sensitivity-example invoice-processing --parameter ai_cost_per_execution --values 0,5,10,20,40
```

This answers a concrete vendor-negotiation question: "if the AI API
provider raises their per-call price, at what price does this redesign
stop being worth it?"

## Worked example: how wrong can the AI be?

```bash
b2b-simulator sensitivity-example customer-support-ticket-resolution --parameter ai_error_rate --values 0.0,0.1,0.2,0.3,0.5
```

Because a failed task ends the case immediately (see
`docs/redesign_analysis.md` on failure rate), a *higher* AI error rate
can sometimes look like it "saves money" in the cost-savings column,
even as completion rate collapses. This is exactly why the sensitivity
table always shows completion rate alongside cost savings -- read them
together, not the cost column in isolation.
