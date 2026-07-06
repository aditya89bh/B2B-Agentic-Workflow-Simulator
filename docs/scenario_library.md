# Scenario Library

The simulator ships with 11 simulation scenarios across 7 business categories.
Use `list-scenarios` to see all available options.

```bash
b2b-simulator list-scenarios
b2b-simulator list-scenarios --category healthcare
b2b-simulator list-scenarios --format json
```

## Scenarios by category

### Healthcare

| Slug | Description |
|---|---|
| `healthcare-prior-authorization` | Insurance prior-auth from clinical submission through payer decision |

### Insurance

| Slug | Description |
|---|---|
| `insurance-claims-intake` | Property/casualty claims from FNOL through initial adjudication |

### Human Resources

| Slug | Description |
|---|---|
| `hr-recruiting-screening` | Candidate screening from application through interview scheduling |

### Procurement

| Slug | Description |
|---|---|
| `procurement-vendor-onboarding` | Vendor onboarding through compliance, risk scoring, and activation |

### Legal

| Slug | Description |
|---|---|
| `legal-contract-review` | Contract review from receipt through AI redlining and execution |

### Information Technology

| Slug | Description |
|---|---|
| `it-support-triage` | Helpdesk incident from intake triage through L1/L2/L3 resolution |

### Finance

| Slug | Description |
|---|---|
| `invoice-processing` | Accounts payable from invoice intake through ERP entry and payment |
| `finance-month-end-close` | Month-end close from data collection through reconciliation and reporting |

### Customer Success / Sales

| Slug | Description |
|---|---|
| `customer-support-ticket-resolution` | Multi-tier support from ticket triage through resolution |
| `customer-onboarding-implementation` | B2B SaaS customer implementation from signed contract through go-live |
| `sales-lead-qualification` | Lead qualification from intake through discovery call to handoff |

## Running any scenario

Every scenario works with all the same CLI commands:

```bash
# KPI comparison
b2b-simulator run-example <slug> --cases 300

# Full ROI report
b2b-simulator compare-example <slug> --cases 300 --implementation-cost 15000

# One-page stakeholder snapshot
b2b-simulator executive-snapshot <slug> --cases 300 --implementation-cost 15000

# Full deliverable packet
b2b-simulator consultant-packet <slug> --cases 300 --output-dir packet/

# Visualize workflow
b2b-simulator visualize-workflow <slug> --format mermaid

# Bottleneck heatmap
b2b-simulator bottleneck-heatmap <slug> --cases 500

# ROI waterfall
b2b-simulator roi-waterfall <slug> --cases 300 --implementation-cost 15000
```

## Scenario comparison matrix

```bash
b2b-simulator scenario-matrix
b2b-simulator scenario-matrix --profile conservative
b2b-simulator scenario-matrix --format json --output matrix.json
```

## Generating full case studies

```bash
# All scenarios, all profiles
b2b-simulator generate-case-studies --output-dir case_studies

# One scenario, base profile only
b2b-simulator generate-case-studies --scenario it-support-triage --profiles base
```

## Important disclaimer

All scenarios are illustrative, not benchmark-validated industry truths.
Durations, error rates, and costs are reasonable approximations based on
publicly available process design patterns.

**You must calibrate these values with your own operational data before
presenting to stakeholders.**

See `docs/scenario_assumptions.md` for guidance on what to measure.
