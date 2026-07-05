# Portfolio Analysis

A single `RedesignDiff` answers "should we do this one redesign?" A
`WorkflowPortfolio` answers a different question: given several
candidate redesigns, which one should we do first, and how much value
does the whole program add together? This document explains the
portfolio model, how aggregation and ranking work, and how to read the
portfolio report.

## Building a portfolio

A portfolio is a named collection of `PortfolioEntry` objects, each
built from a before/after `KPIResult` pair (exactly the same inputs
`compare_workflows()` takes):

```python
from b2b_workflow_simulator.portfolio import WorkflowPortfolio

portfolio = WorkflowPortfolio(name="2026 AI Transformation Program")
portfolio.add_entry(
    "sales-lead-qualification", before_kpi, after_kpi, implementation_cost=5000.0
)
portfolio.add_entry(
    "invoice-processing", before_kpi_2, after_kpi_2, implementation_cost=8000.0
)
```

`add_entry()` internally calls `compare_workflows()`, so a
`WorkflowPortfolio` never depends on the simulation engine directly --
it only aggregates results that were already produced. This mirrors how
`redesign.py` is decoupled from `simulation.py`.

## Ranking workflows

```python
for entry in portfolio.ranked(by="total_cost_savings"):
    print(entry.name, entry.diff.roi.total_cost_savings)
```

`ranked(by=...)` sorts entries highest-value-first by one of three
metrics:

| `by` | What it measures |
|---|---|
| `total_cost_savings` (default) | Absolute dollar savings for the simulated case volume. Favors high-volume processes even if the percentage improvement is modest. |
| `roi_percentage` | Savings as a percentage of "before" cost. Favors processes that are proportionally cheaper after the redesign, regardless of scale. |
| `cost_savings_per_case` | Dollar savings per case. The most portable metric across workflows simulated at different volumes. |

There is no single "correct" ranking -- a transformation program with
limited implementation budget might prioritize `roi_percentage` or
`cost_savings_per_case` to find the most efficient use of that budget,
while a program optimizing for total dollar impact would use
`total_cost_savings`.

## Aggregate summary

`portfolio.summary()` returns a `PortfolioSummary`:

- `total_before_cost` / `total_after_cost` / `total_cost_savings`: raw
  sums across every entry's simulated cost, not averages of averages.
- `portfolio_roi_percentage`: aggregate savings as a percentage of
  aggregate "before" cost.
- `total_wait_minutes_saved`: sum of (before - after) total wait
  minutes across every entry. Zero for workflows simulated without
  `arrival_interval_minutes`.
- `total_implementation_cost`: sum of the implementation costs supplied
  when each entry was added (entries without a supplied cost contribute
  zero).
- `payback_in_periods` / `payback_feasible`: see below.

### Interpreting the aggregate payback period

Each workflow in a portfolio is usually simulated at a volume that
represents *some* period of real-world activity -- for example, "the
number of invoices we process in a typical month." If every workflow in
the portfolio was simulated at its own typical-month volume,
`total_implementation_cost / total_cost_savings` is a payback period in
that same unit (months, in this example): how long it takes the
combined program to pay for itself if every redesign is rolled out at
once.

This is an assumption the portfolio model does not enforce -- it is up
to you to simulate each workflow at a case volume that means something
consistent across the whole portfolio. If your workflows are simulated
at unrelated, incomparable volumes (e.g. one at "cases per day" and
another at "cases per year"), the aggregate payback figure will not be
meaningful, even though the per-workflow payback figures inside each
entry's `RedesignDiff` still are.

## Reading the portfolio report

`generate_portfolio_report(portfolio, rank_by="total_cost_savings")` in
`report.py` renders five sections:

1. **Executive summary** -- workflow count, aggregate cost change,
   aggregate wait-time change, and combined payback if implementation
   costs were supplied.
2. **Workflow ranking** -- a table of every workflow, ranked by
   `rank_by`, with cost savings and ROI percentage.
3. **Aggregate ROI & payback** -- the raw `PortfolioSummary` numbers.
4. **Risks** -- every non-trivial risk from each entry's underlying
   `RedesignDiff` (see `docs/redesign_analysis.md`), tagged with which
   workflow it came from.
5. **Recommended rollout order** -- the same ranking as section 2,
   phrased as a sequence: do the highest-value redesign first, since it
   both proves the model works and generates savings fastest to fund
   the rest of the program.

## Worked example

```bash
b2b-simulator compare-portfolio sales-lead-qualification invoice-processing customer-support-ticket-resolution \
    --cases 300 --implementation-cost 6000 --rank-by roi_percentage
```

This simulates all three bundled examples at 300 cases each, applies a
$6,000 implementation cost to every one, ranks them by ROI percentage,
and prints the full portfolio report. Add `--html-output report.html`
to also write a shareable static HTML version. To build a portfolio
from your own workflows in Python, simulate each pair yourself and call
`portfolio.add_entry()` directly, as shown above.
