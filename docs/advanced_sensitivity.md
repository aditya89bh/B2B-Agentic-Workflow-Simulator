# Advanced (Multi-Parameter) Sensitivity Analysis

`docs/sensitivity_analysis.md` covers `run_sensitivity_sweep()`: varying
one assumption at a time. That answers "how much can this one number
move before the redesign stops paying off?" -- a fair question when
assumptions move independently. In practice they often don't: an AI
vendor's per-call price and its error rate both drift as the vendor
matures; a busier sales quarter changes both lead arrival rate and the
pressure to cut implementation budget. `sensitivity_grid.py` answers the
joint question: "across a *combination* of two assumptions moving
together, where does this redesign remain safe?"

## The grid engine

`run_sensitivity_grid()` re-simulates a before/after workflow pair once
per `(x, y)` combination in a two-dimensional grid, holding the random
seed fixed so only the swept parameters drive outcome differences:

```python
from b2b_workflow_simulator.examples.invoice_processing import (
    build_after_workflow,
    build_before_workflow,
)
from b2b_workflow_simulator.sensitivity_grid import (
    generate_sensitivity_grid_report,
    run_sensitivity_grid,
)

result = run_sensitivity_grid(
    build_before_workflow,
    build_after_workflow,
    x_parameter="ai_error_rate",
    x_values=[0.0, 0.05, 0.1, 0.2, 0.3],
    y_parameter="ai_cost_per_execution",
    y_values=[0.0, 5.0, 10.0, 20.0],
    num_cases=300,
    seed=7,
)
print(generate_sensitivity_grid_report(result))
```

`x_parameter` and `y_parameter` accept the same `PARAMETERS` values as
the single-parameter sweep (`ai_error_rate`, `ai_cost_per_execution`,
`human_hourly_cost`, `arrival_interval`, `implementation_cost`) and must
differ from each other. Every other sweep semantic carries over
unchanged: `build_before`/`build_after` are zero-argument `Workflow`
factories, and `implementation_cost` (on either axis) only changes the
ROI calculation, not the simulation itself.

## Reading the ROI matrix

```
============================================================
MULTI-PARAMETER SENSITIVITY ANALYSIS
============================================================

Grid: ai_error_rate (columns) x ai_cost_per_execution (rows)
ROI %, 5 x 4 = 20 combinations simulated

ROI MATRIX
------------------------------------------------------------
ai_cost_per_execution / ai_error_rate        0       0.05 ...
--------------------------------------------------------------
0                                        +85.8%     +81.2% ...
5                                        +22.8%     +19.4% ...
10                                       -40.2%     -43.1% ...
20                                      -166.2%    -169.8% ...

OPERATING REGIONS
------------------------------------------------------------
Safe operating region:     8/20 combinations (40%)
Negative ROI region:       12/20 combinations (60%)
Unstable region:           0/20 combinations (0%)
```

Each cell is the ROI percentage of the `RedesignDiff` simulated at that
`(x, y)` combination. Reading down a column shows how sensitive ROI is
to the y-axis parameter at a fixed x value; reading across a row shows
the reverse -- together they show whether the redesign's viability
depends more on one assumption than the other, which is often the more
actionable finding than either single-parameter sweep alone.

## Operating regions

Every grid cell is classified into exactly one of three regions via
`SensitivityGridResult.classify_region(x, y)`:

- **Safe**: ROI is positive (or, when ROI is undefined because the
  "before" cost was zero, cost savings are positive) and the redesign's
  completion rate stays operationally sound.
- **Negative**: ROI (or cost savings) is zero or negative, but the
  process still completes cases at an acceptable rate -- a *financial*
  problem, not an *operational* one.
- **Unstable**: completion rate after the redesign falls below
  `UNSTABLE_COMPLETION_RATE_THRESHOLD` (50% by default), meaning the
  process is breaking down operationally regardless of what the ROI
  number says. A financially attractive but operationally unstable
  combination is the trap a single-metric ROI view can hide entirely --
  this is the primary reason to run a two-dimensional sweep instead of
  trusting a single-parameter one in isolation.

`safe_region_points()`, `negative_region_points()`, and
`unstable_region_points()` return the matching `GridPoint`s directly,
and `region_map()` returns the full grid of classifications (rows:
`y_values`, columns: `x_values`) for building custom visualizations.

## Worked example: AI cost and error rate moving together

```bash
b2b-simulator sensitivity-grid-example invoice-processing \
  --x-parameter ai_error_rate --x-values 0,0.05,0.1,0.2,0.3 \
  --y-parameter ai_cost_per_execution --y-values 0,5,10,20 \
  --html-output sensitivity-grid.html
```

This is the realistic version of "how expensive can the AI get?" and
"how wrong can the AI be?" from the single-parameter sensitivity guide:
vendor pricing and model accuracy typically move together as a vendor's
offering evolves, and a grid shows the region where both can drift
without the redesign losing money *or* breaking down operationally, in
one view instead of two separate sweeps that don't capture their
interaction.

## Worked example: staffing versus AI adoption

```bash
b2b-simulator sensitivity-grid-example sales-lead-qualification \
  --x-parameter arrival_interval --x-values 5,10,15,20,30 \
  --y-parameter implementation_cost --y-values 0,5000,10000,20000
```

As lead volume grows (shorter arrival interval) the AI-augmented
workflow's cost advantage compounds, while a larger implementation
budget takes longer to pay back regardless of volume. The resulting
grid shows the safe combinations of "how much lead volume do we need"
and "how much can we spend building this" before recommending a
rollout budget to a stakeholder.
