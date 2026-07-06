# CLI Reference

All commands are available via `b2b-simulator`.

```bash
b2b-simulator --version       # b2b-workflow-simulator 1.0.0
b2b-simulator --help          # list all commands
b2b-simulator <command> --help  # command-specific help
```

---

## Core simulation

### `run-example`
Run a bundled example and compare before/after KPIs.

```bash
b2b-simulator run-example invoice-processing --cases 300 --seed 42
b2b-simulator run-example it-support-triage --engine discrete
```

Key flags: `--cases`, `--seed`, `--engine {simple,discrete}`

### `compare-example`
Run both variants and print a full before/after ROI report.

```bash
b2b-simulator compare-example invoice-processing --cases 300 --implementation-cost 8000
b2b-simulator compare-example invoice-processing --assumptions path/to/profile.json
```

Key flags: `--cases`, `--seed`, `--implementation-cost`, `--arrival-interval`, `--engine`, `--assumptions`

### `export-example`
Export events, KPIs, and comparison to disk (JSON or CSV).

```bash
b2b-simulator export-example invoice-processing --cases 300 --output-dir exports/
b2b-simulator export-example invoice-processing --format csv --output-dir exports/
```

### `html-report-example`
Generate a static HTML redesign report.

```bash
b2b-simulator html-report-example invoice-processing --output report.html
```

---

## Portfolio and uncertainty

### `run-portfolio`
Run multiple examples and print a per-workflow KPI summary.

```bash
b2b-simulator run-portfolio sales-lead-qualification invoice-processing
```

### `compare-portfolio`
Run multiple examples and print a full portfolio ROI report.

```bash
b2b-simulator compare-portfolio sales-lead-qualification invoice-processing \
  --rank-by total_cost_savings --html-output portfolio.html
```

### `monte-carlo-example`
Run a Monte Carlo comparison across many seeds.

```bash
b2b-simulator monte-carlo-example invoice-processing --cases 200 --seeds 1,2,3,4,5,6,7,8,9,10
```

### `monte-carlo-portfolio`
Monte Carlo for multiple examples.

```bash
b2b-simulator monte-carlo-portfolio sales-lead-qualification invoice-processing
```

### `sensitivity-example`
Sweep one parameter and print a sensitivity table.

```bash
b2b-simulator sensitivity-example invoice-processing --parameter ai_error_rate \
  --values 0.0,0.05,0.10,0.20
```

### `sensitivity-grid-example`
Two-parameter sensitivity grid.

```bash
b2b-simulator sensitivity-grid-example invoice-processing \
  --x-parameter ai_error_rate --x-values 0.0,0.05,0.10 \
  --y-parameter ai_cost --y-values 0.5,1.0,1.5 --html-output grid.html
```

---

## Capacity and teams

### `capacity-analysis`
Run one variant and print a staffing recommendation report.

```bash
b2b-simulator capacity-analysis invoice-processing --arrival-interval 5 --html-output capacity.html
```

### `team-utilization`
Print raw actor/pool/worker utilization figures.

```bash
b2b-simulator team-utilization invoice-processing --variant after --arrival-interval 5
```

---

## Governance and risk

### `policy-analysis`
Evaluate governance policies and print violations.

```bash
b2b-simulator policy-analysis invoice-processing --html-output policy.html
```

### `compliance-analysis`
Evaluate compliance requirements.

```bash
b2b-simulator compliance-analysis invoice-processing
```

### `risk-analysis`
Print organizational risk assessment.

```bash
b2b-simulator risk-analysis invoice-processing --variant after --html-output risk.html
```

### `readiness-analysis`
AI adoption readiness assessment.

```bash
b2b-simulator readiness-analysis invoice-processing --html-output readiness.html
```

### `recommend-redesign`
Print actionable redesign recommendations.

```bash
b2b-simulator recommend-redesign invoice-processing
```

### `executive-report`
Full executive assessment (KPI + ROI + SLA + compliance + risk + recommendations).

```bash
b2b-simulator executive-report invoice-processing --cases 300 --html-output exec.html
```

---

## Organization

### `run-org`
Run the bundled B2B SaaS org simulation and print KPI summary.

```bash
b2b-simulator run-org --cases 200 --seed 42
```

### `org-health`
Compute and display the organizational health score.

```bash
b2b-simulator org-health --cases 200 --html-output health.html
```

### `org-budget-analysis`
Print budget utilization analysis.

```bash
b2b-simulator org-budget-analysis
```

### `org-resource-contention`
Print shared resource contention analysis (runs simulation first).

```bash
b2b-simulator org-resource-contention --cases 200 --days 22
```

### `org-growth-projection`
Project 12-month growth forecast.

```bash
b2b-simulator org-growth-projection --monthly-growth-rate 0.08 --base-cases 200
```

### `org-restructure-scenario`
Evaluate an organizational restructuring scenario.

```bash
b2b-simulator org-restructure-scenario create_ai_ops_team --cases 200
```

### `org-executive-report`
Full organizational executive report.

```bash
b2b-simulator org-executive-report --cases 200 --html-output org_exec.html
```

---

## Phase 7 outputs

### `visualize-workflow`
Render a workflow as Mermaid flowchart or plain text.

```bash
b2b-simulator visualize-workflow invoice-processing --format mermaid
b2b-simulator visualize-workflow invoice-processing --format text --output wf.txt
```

### `roi-waterfall`
Decomposed ROI waterfall chart.

```bash
b2b-simulator roi-waterfall invoice-processing --cases 300 --implementation-cost 8000
b2b-simulator roi-waterfall invoice-processing --format svg --output roi.svg
```

Supports `--assumptions` for profile-based simulation.

### `bottleneck-heatmap`
Node pressure heatmap.

```bash
b2b-simulator bottleneck-heatmap invoice-processing --cases 500 --arrival-interval 10
b2b-simulator bottleneck-heatmap invoice-processing --format svg --output heatmap.svg
```

### `executive-snapshot`
Concise one-page stakeholder summary.

```bash
b2b-simulator executive-snapshot invoice-processing --cases 300 --implementation-cost 8000
b2b-simulator executive-snapshot invoice-processing --html-output snapshot.html
b2b-simulator executive-snapshot invoice-processing --assumptions path/to/profile.json
```

### `consultant-packet`
Generate a full stakeholder deliverable directory.

```bash
b2b-simulator consultant-packet invoice-processing \
  --cases 300 --implementation-cost 8000 --output-dir packet/
```

### `generate-example-gallery`
Generate deterministic example outputs for all three original scenarios.

```bash
b2b-simulator generate-example-gallery --output-dir examples/outputs
```

---

## Phase 8 scenarios

### `list-scenarios`
List all 11 registered scenarios.

```bash
b2b-simulator list-scenarios
b2b-simulator list-scenarios --category healthcare
b2b-simulator list-scenarios --format json
```

### `generate-case-studies`
Generate full case study directories for all or one scenario.

```bash
b2b-simulator generate-case-studies --output-dir case_studies/
b2b-simulator generate-case-studies --scenario healthcare-prior-authorization \
  --profiles base,conservative --output-dir case_studies/
```

### `scenario-matrix`
Cross-scenario KPI comparison table.

```bash
b2b-simulator scenario-matrix
b2b-simulator scenario-matrix --profile conservative --format json --output matrix.json
```

---

## Phase 9 customization

### `list-configs`
List bundled sample scenario configurations.

```bash
b2b-simulator list-configs
b2b-simulator list-configs --format json
```

### `validate-config`
Validate a scenario configuration file.

```bash
b2b-simulator validate-config path/to/config.json
```
Exit code 0 = valid, 1 = invalid.

### `run-config`
Run configured before/after and print KPI table.

```bash
b2b-simulator run-config path/to/config.json
```

### `compare-config`
Run configured workflows and print full ROI report.

```bash
b2b-simulator compare-config path/to/config.json
```

### `config-snapshot`
Executive snapshot from a configured scenario.

```bash
b2b-simulator config-snapshot path/to/config.json --html-output snapshot.html
```

### `config-packet`
Consultant packet from a configured scenario.

```bash
b2b-simulator config-packet path/to/config.json --output-dir packet/
```

### `config-case-study`
Full configured case-study directory (includes config diff).

```bash
b2b-simulator config-case-study path/to/config.json --output-dir case_study/
```

### `config-diff`
Show what changed from the base scenario.

```bash
b2b-simulator config-diff path/to/config.json
b2b-simulator config-diff path/to/config.json --format json --output diff.json
```

### `calibration-template`
Generate a calibration questionnaire for a scenario.

```bash
b2b-simulator calibration-template healthcare-prior-authorization --output calibration.md
b2b-simulator calibration-template legal-contract-review --format json
```

---

## Release utilities

### `generate-release-examples`
Generate deterministic reference outputs for the v1.0.0 release.

```bash
b2b-simulator generate-release-examples --output-dir examples/outputs/final_release
```
