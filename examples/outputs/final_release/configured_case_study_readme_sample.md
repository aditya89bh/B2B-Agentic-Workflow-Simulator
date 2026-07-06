# Configured Case Study: Healthcare Prior Auth — Small Regional Plan

**Client:** Acme Regional Health Plan
**Base scenario:** Healthcare Prior Authorization (`healthcare-prior-authorization`)
**Category:** Healthcare
**Profile:** base
**Created by:** consulting-team
**Config version:** 1.0

## Overview

Calibrated for a 200,000-member regional plan with lower labor costs and higher denial rates.

## Base scenario used

Healthcare Prior Authorization — Insurance prior-auth workflow from clinical submission through payer decision.
Target users: Health plan medical directors, utilization management teams, providers

## What was customized

- Actor overrides: 3 actor(s) modified
- Node overrides: 2 node(s) modified
- Edge overrides: 3 edge(s) modified

## Before vs after result summary (configured)

- Completion rate: 86.3% → 86.7%
- Avg cost per case: $84.95 → $30.07
- Total cost savings: $16,463.97
- Avg cycle time: 87.0 min → 24.0 min

## Key assumptions

- Profile: base
- Cases simulated: 300

## Notes

Clinical staff are generalists handling multiple administrative tasks; cycle times are longer than benchmark.

## What changed from the base scenario

See `config_diff.txt` for a full breakdown of overridden parameters.

## What must be validated with real data

- Small plan may have fewer peer-to-peer review cases than modeled.
- Staffing model assumes same-day processing; overnight batching not modeled.

## When not to rely on this output

- When input data quality is poor (garbage in, garbage out).
- Without having your process owner validate the stage durations and error rates.
- As a substitute for pilot measurement or process mining.
- When regulatory requirements are not yet fully understood.

## Files in this case study

| File | Description |
|---|---|
| `executive_snapshot.txt` | One-page stakeholder summary |
| `executive_snapshot.html` | Same summary as HTML |
| `workflow_before.mmd` | Mermaid flowchart (before, with overrides) |
| `workflow_after.mmd` | Mermaid flowchart (after, with overrides) |
| `roi_waterfall.svg` | ROI decomposition chart |
| `bottleneck_heatmap.svg` | Node pressure heatmap |
| `assumptions.json` | Assumption profile parameters |
| `config.json` | Full ScenarioConfig (all overrides) |
| `config_diff.txt` | What changed from the base scenario |
| `config_diff.json` | Same diff as machine-readable JSON |
| `kpi_summary.json` | Structured KPI output |
| `recommendations.txt` | Plain-text recommendations |

## Commands to reproduce

```bash
b2b-simulator run-config path/to/healthcare-prior-auth-small-plan.json
b2b-simulator config-snapshot path/to/healthcare-prior-auth-small-plan.json
b2b-simulator config-case-study path/to/healthcare-prior-auth-small-plan.json --output-dir case_study/
```

---

*This case study is based on user-provided calibrated assumptions.*
*All figures are directional estimates — validate with real operational data*
*before making investment decisions.*