# Monte Carlo Analysis

Every simulation run so far in this project is deterministic given a
seed: the same seed always reproduces the same `KPIResult`. That is
essential for fair before/after comparison, but it means a single run
only shows *one* plausible outcome, not the range of outcomes a real
process would actually produce as random variation (which leads convert,
which tasks fail, how long each one takes) plays out differently every
time. `monte_carlo.py` answers the natural follow-up: "how much does
this outcome actually vary, and how confident should we be in it?"

## Running a Monte Carlo sweep

`run_monte_carlo()` re-simulates a single workflow once per seed and
summarizes each KPI's distribution across runs:

```python
from b2b_workflow_simulator.examples.invoice_processing import build_after_workflow
from b2b_workflow_simulator.monte_carlo import generate_monte_carlo_report, run_monte_carlo

result = run_monte_carlo(
    build_after_workflow,
    num_cases=300,
    seeds=range(1, 51),
)
print(generate_monte_carlo_report(result))
```

For before/after redesign evaluation, `run_monte_carlo_comparison()` is
usually more useful: it runs both workflows per seed (so "before" and
"after" stay paired within a seed, exactly like a single
`compare_workflows()` call) and summarizes the resulting `RedesignDiff`
metrics, including ROI and payback:

```python
from b2b_workflow_simulator.examples.invoice_processing import (
    build_after_workflow,
    build_before_workflow,
)
from b2b_workflow_simulator.monte_carlo import (
    generate_monte_carlo_comparison_report,
    run_monte_carlo_comparison,
)

result = run_monte_carlo_comparison(
    build_before_workflow,
    build_after_workflow,
    num_cases=300,
    seeds=range(1, 51),
    implementation_cost=8000.0,
)
print(generate_monte_carlo_comparison_report(result))
```

From the CLI:

```bash
b2b-simulator monte-carlo-example invoice-processing --cases 300 --seeds 1,2,3,4,5 --implementation-cost 8000
b2b-simulator monte-carlo-portfolio sales-lead-qualification invoice-processing --cases 300 --seeds 1,2,3,4,5
```

`monte-carlo-example` runs the full comparison report for one bundled
example (add `--html-output` for a shareable HTML version).
`monte-carlo-portfolio` runs the same comparison across several bundled
examples and prints a condensed mean-savings/mean-ROI summary row per
workflow, mirroring how `run-portfolio` summarizes a single-seed
portfolio.

## Reading the statistics

Every metric reports seven numbers via `MetricStats`:

| Statistic | Meaning |
|---|---|
| `mean` | Average outcome across all runs. |
| `minimum` / `maximum` | The best and worst single run observed. |
| `median` | The middle outcome; less skewed by one extreme run than the mean. |
| `p10` | 10th percentile -- 90% of runs did at least this well. A reasonable "plan for this" pessimistic bound. |
| `p90` | 90th percentile -- an optimistic-but-plausible bound. |
| `std_dev` | Sample standard deviation; how spread out the outcomes are. |

`MetricStats.spread` (`p90 - p10`) is a compact single number for "how
wide is the plausible range," useful for sorting or flagging metrics
that deserve more scrutiny before a stakeholder commits to a number.

## Metrics covered

`run_monte_carlo()` reports `KPI_METRICS`: completion rate, average
cycle time, average wait time, total cost, and average cost per case.

`run_monte_carlo_comparison()` reports `COMPARISON_METRICS`: each of
the above for both "before" and "after," plus total cost savings, ROI
percentage, cost savings per case, and payback in cases. ROI and
payback are computed only for runs where they are mathematically
defined (a "before" workflow with nonzero cost, and a redesign that
actually produces net per-case savings, respectively); a metric with
zero samples across all seeds is reported as "n/a" rather than a
misleading zero.

## Interpreting variability

The executive summary in `generate_monte_carlo_report()` and
`generate_monte_carlo_comparison_report()` translates the raw
statistics into plain language:

- If every simulated run produced positive cost savings, the summary
  says so explicitly -- a strong signal the redesign's advantage is
  robust to ordinary random variation, not an artifact of one lucky
  seed.
- If cost savings change sign across runs, the summary flags this as
  "sensitive to random variation," a much weaker basis for a rollout
  decision than a single positive-looking point estimate would suggest.
- Cost-per-case volatility is classified as stable, moderately
  variable, or highly variable based on the P10-P90 spread relative to
  the mean, giving a quick read on how tightly to trust the point
  estimate a single seeded run would have reported.

## Why this matters for a rollout decision

A single `compare-example` run with one seed can make a marginal
redesign look definitively good (or bad) purely by chance, especially
at moderate case volumes where a handful of AI errors or a lucky
branch-probability draw can swing cost per case by double digits of a
percent. Monte Carlo analysis turns "the ROI was +22%" into "the ROI
was +22% on average, ranging from +14% to +31% across 50 independent
runs" -- the second statement is what a stakeholder actually needs to
decide how much confidence to place in the number before committing
budget to a rollout.
