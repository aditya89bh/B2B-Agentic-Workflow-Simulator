# Industry Case Studies

Each scenario in the library ships with three assumption profiles (base,
conservative, aggressive) and can generate a full case study directory.

## What a case study contains

```
case_studies/<scenario_slug>/
  README.md                          — overview, assumptions, and reproduction commands
  executive_snapshot_base.txt        — one-page summary (base profile)
  executive_snapshot_conservative.txt
  executive_snapshot_aggressive.txt
  roi_waterfall_base.svg             — ROI decomposition chart
  bottleneck_heatmap_base.svg        — node pressure heatmap
  workflow_before.mmd                — Mermaid flowchart (before)
  workflow_after.mmd                 — Mermaid flowchart (after)
  assumptions_base.json              — simulation parameters used
  assumptions_conservative.json
  assumptions_aggressive.json
  kpi_summary_base.json              — structured KPI output
  kpi_summary_conservative.json
  kpi_summary_aggressive.json
```

## Generating case studies

```bash
# All scenarios, all profiles
b2b-simulator generate-case-studies --output-dir case_studies

# One scenario
b2b-simulator generate-case-studies \
  --scenario healthcare-prior-authorization \
  --output-dir case_studies

# Specific profiles only
b2b-simulator generate-case-studies \
  --scenario invoice-processing \
  --profiles base,conservative \
  --output-dir case_studies
```

## Scenario-specific notes

### Healthcare Prior Authorization

- **Typical implementation cost:** $15,000–$25,000 for a mid-sized health plan
- **Key variable:** AI criteria-matching escalation rate (how often the AI defers to a medical director)
- **What to calibrate:** denial rates vary significantly by line of business

### Insurance Claims Intake

- **Typical implementation cost:** $18,000–$30,000
- **Key variable:** fraud detection accuracy (modeled as error/escalation rates)
- **What to calibrate:** CAT (catastrophe) surge multiplier for your geography

### HR Recruiting Screening

- **Typical implementation cost:** $8,000–$15,000 for ATS integration
- **Key variable:** AI resume screening acceptance rate vs. human baseline
- **Warning:** bias risk requires human oversight; this simulation does not model fairness

### Procurement Vendor Onboarding

- **Typical implementation cost:** $20,000–$35,000 including ERP integration
- **Key variable:** compliance screening escalation rate (sanctions list complexity)
- **What to calibrate:** vendor rejection rate at compliance stage for your industry

### Legal Contract Review

- **Typical implementation cost:** $25,000–$50,000 including training data
- **Key variable:** AI redlining quality on non-standard clauses
- **What to calibrate:** negotiation success rate and counterparty behavior

### IT Support Triage

- **Typical implementation cost:** $10,000–$20,000 (knowledge base + integration)
- **Key variable:** AI L1 auto-resolution rate (depends on KB coverage)
- **What to calibrate:** ticket complexity distribution for your environment

### Finance Month-End Close

- **Typical implementation cost:** $25,000–$45,000 (ERP integration, reconciliation rules)
- **Key variable:** AI reconciliation exception rate (depends on data quality)
- **What to calibrate:** number of accounts, entities, and reconciliation rules

### Customer Onboarding / Implementation

- **Typical implementation cost:** $15,000–$25,000
- **Key variable:** AI configuration accuracy rate
- **What to calibrate:** customer readiness score and integration complexity tier

## Using the conservative profile

The conservative profile doubles AI error rates and increases AI costs by 50%.
This represents a scenario where:
- AI systems are new and not yet production-calibrated
- Edge cases are common
- Trust in AI outputs is low and human review is extensive

Run the conservative profile with:
```bash
b2b-simulator executive-snapshot <slug> \
  --assumptions src/b2b_workflow_simulator/examples/data/assumptions/<slug>/conservative.json
```

Or reference the profile file in a `--assumptions` flag for any command.
