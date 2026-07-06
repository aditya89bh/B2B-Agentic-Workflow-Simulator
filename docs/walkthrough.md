# Complete Walkthrough

This walkthrough demonstrates a complete consulting engagement simulation using the healthcare prior authorization scenario.

## 1. Install

```bash
pip install -e ".[dev]"
b2b-simulator --version  # b2b-workflow-simulator 1.0.0
```

## 2. Explore available scenarios

```bash
b2b-simulator list-scenarios
b2b-simulator list-scenarios --category healthcare
```

## 3. Run the baseline comparison

```bash
b2b-simulator run-example healthcare-prior-authorization --cases 300
```

Expected output: a before/after KPI table showing completion rate, cost per case, and cycle time.

## 4. Generate an executive snapshot

```bash
b2b-simulator executive-snapshot healthcare-prior-authorization \
  --cases 300 --implementation-cost 18000 --html-output snapshot.html
```

The snapshot answers: *Should we proceed with this automation?* in one page.

## 5. Generate a consultant packet

```bash
b2b-simulator consultant-packet healthcare-prior-authorization \
  --cases 300 --implementation-cost 18000 --output-dir pa_packet/

ls pa_packet/
```

You'll see: `README.md`, `executive_snapshot.txt`, `executive_snapshot.html`, `workflow_before.mmd`, `workflow_after.mmd`, `roi_waterfall.svg`, `bottleneck_heatmap.svg`, `kpi_summary.json`, `assumptions.json`, `recommendations.txt`.

## 6. Compare all scenarios

```bash
b2b-simulator scenario-matrix --profile conservative
```

This ranks all 11 scenarios by projected ROI under conservative assumptions — useful for prioritizing which transformation to pursue first.

## 7. Generate a calibration questionnaire

```bash
b2b-simulator calibration-template healthcare-prior-authorization \
  --output pa_calibration.md
```

Share this with your client's clinical operations team to collect real stage durations, staff costs, and denial rates.

## 8. Validate the sample config

```bash
b2b-simulator validate-config \
  src/b2b_workflow_simulator/examples/data/configs/healthcare-prior-auth-small-plan.json
```

Expected: `Valid: healthcare-prior-auth-small-plan`

## 9. Run the configured (client-calibrated) scenario

```bash
b2b-simulator run-config \
  src/b2b_workflow_simulator/examples/data/configs/healthcare-prior-auth-small-plan.json
```

Notice how the KPIs differ from the base scenario — the small regional plan has lower labor costs and slightly different process paths.

## 10. Generate the configured case study

```bash
b2b-simulator config-case-study \
  src/b2b_workflow_simulator/examples/data/configs/healthcare-prior-auth-small-plan.json \
  --output-dir pa_configured_case_study/

ls pa_configured_case_study/
```

In addition to all the standard case-study files, you'll see:
- `config.json` — the full override configuration
- `config_diff.txt` — exactly what changed from the base scenario
- `config_diff.json` — machine-readable diff

## 11. Interpret the outputs

**What to present to a client:**

1. `executive_snapshot.html` — opening slide for the discussion
2. `roi_waterfall.svg` — shows *where* the savings come from
3. `bottleneck_heatmap.svg` — shows *what* to target for automation
4. `workflow_before.mmd` + `workflow_after.mmd` — visualize the process change

**What to say about limitations:**

> "All figures are directional estimates based on the assumptions in `config.json`.
> The clinical review escalation rate and AI criteria-matching error rate are the most
> sensitive inputs — we've used a conservative profile (2× AI error rate) for this
> version.  Before presenting to the board, validate these rates against your last
> three months of prior-auth decisions."

## Reminder

This tool produces simulation estimates, not operational measurements.  See `docs/limitations.md` for a complete list of what the simulation cannot model.
