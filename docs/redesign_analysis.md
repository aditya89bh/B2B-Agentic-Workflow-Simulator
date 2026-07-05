# Redesign Analysis

This document explains how to read the output of `compare_workflows()`
and `generate_report()`, and how to interpret it as a consultant, ops
leader, or founder deciding whether to invest in a redesign.

## The comparison model

A redesign analysis always starts from two simulation runs: a "before"
run of the current-state workflow, and an "after" run of a proposed
redesign. Both runs should use:

- The same number of cases (`num_cases`).
- The same random seed, so differences reflect the workflow definitions,
  not sampling noise.
- The same `arrival_interval_minutes`, if you are evaluating capacity
  effects (see `docs/capacity_modeling.md`).

`compare_workflows(before_kpi, after_kpi, implementation_cost=None)`
takes the two `KPIResult` objects and returns a `RedesignDiff`.

## Reading a `RedesignDiff`

### Headline metrics (`diff.metrics`)

Each metric is a `MetricDelta` with `before`, `after`, `delta` (after
minus before), and `percent_change` (relative to `before`, or `None` if
`before` was zero):

| Metric | What it means |
|---|---|
| Completion rate | Fraction of cases that reached a terminal node. Higher is better. |
| Failure rate | Fraction of cases that ended in a system error. Lower is better. |
| Total cost | Aggregate simulated cost across all cases. Lower is better. |
| Cost per case | `Total cost / total cases`. The number to quote in an ROI pitch. |
| Cycle time (minutes) | Average end-to-end time per case, including wait time. |
| Wait time (minutes) | Average time per case spent queued for a busy actor. Zero unless `arrival_interval_minutes` was set. |
| Escalation rate | Fraction of cases with at least one AI-to-human escalation. Not inherently good or bad -- context-dependent. |

### Bottlenecks (`diff.before_bottlenecks`, `diff.after_bottlenecks`)

The top three nodes by total execution time in each variant. Comparing
these two lists shows whether the redesign actually moved the
bottleneck, or just relocated it (a common failure mode: automating the
busiest stage sometimes reveals a *new* bottleneck at the next stage).

### Utilization (`diff.before_utilization`, `diff.after_utilization`)

Per-actor utilization (busy time / available capacity), populated only
when the simulations were run with `arrival_interval_minutes` set. An
actor above roughly 85-90% utilization is at risk of becoming a
bottleneck under real-world variability, even if the simulated average
looks fine.

### ROI (`diff.roi`)

- `total_cost_savings`: `before.total_cost - after.total_cost` for the
  simulated case volume. Positive means the redesign is cheaper.
- `cost_savings_per_case`: the same, normalized per case -- the most
  portable number, since it does not depend on how many cases you
  simulated.
- `roi_percentage`: savings as a percentage of the "before" cost.
- `payback_in_cases` and `payback_feasible`: if you pass
  `implementation_cost`, this tells you how many cases' worth of savings
  it takes to recover that investment. `payback_feasible` is `False`
  when the redesign does not produce net per-case savings, regardless of
  the implementation cost -- in that scenario, more volume never pays
  the investment back.

## Reading the plain-text report

`generate_report(diff)` renders the same data as a report with six
sections:

1. **Executive summary** -- three to four sentences a non-technical
   stakeholder can read standalone.
2. **KPI comparison** -- the full metric table.
3. **Bottlenecks** -- top time-consuming stages, before and after.
4. **Actor utilization** -- per-actor load, before and after (or a note
   that no capacity data was collected).
5. **Risks** -- heuristic flags: rising failure rate, high escalation
   rate (>20%), any actor above 90% utilization after the redesign, or a
   drop in completion rate. These are meant as prompts for follow-up
   investigation, not a certified risk assessment.
6. **Recommendation** -- one of three stances, chosen from cost and
   quality deltas plus payback feasibility:
   - *Proceed with a pilot rollout*: cost improves, completion and
     failure rates hold or improve, and payback is feasible (or no
     implementation cost was given).
   - *Limited pilot with close monitoring*: cost improves but quality
     metrics move in the wrong direction.
   - *Further redesign iteration before adoption*: the redesign does not
     produce a net cost improvement under the simulated assumptions.

## Worked example

```bash
b2b-simulator compare-example invoice-processing --cases 300 --implementation-cost 8000
```

This simulates 300 invoices through both the manual and AI-augmented
invoice processing workflows, computes the diff, and prints the report,
including a payback estimate in terms of "how many invoices' worth of
savings recover the $8,000 implementation cost."

## Exporting the diff

`export.py` can serialize the same `RedesignDiff` to JSON (full detail,
including bottlenecks and utilization) or CSV (the metric table only):

```bash
b2b-simulator export-example invoice-processing --format json --output-dir exports
```

See `docs/getting_started.md` for the full export CLI reference.
