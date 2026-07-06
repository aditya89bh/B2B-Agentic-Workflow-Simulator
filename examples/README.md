# Examples

This directory contains generated sample outputs for the B2B Agentic Workflow Simulator.

## Directory structure

```
examples/
├── README.md                           — this file
└── outputs/
    ├── final_release/                  — v1.0.0 reference outputs (regenerate with generate-release-examples)
    │   ├── healthcare_executive_snapshot.txt
    │   ├── healthcare_workflow_before.mmd
    │   ├── healthcare_workflow_after.mmd
    │   ├── healthcare_roi_waterfall.svg
    │   ├── healthcare_bottleneck_heatmap.svg
    │   ├── scenario_matrix_base.json
    │   ├── scenario_matrix_conservative.json
    │   ├── calibration_healthcare.md
    │   ├── config_diff_healthcare_small_plan.txt
    │   └── configured_case_study_readme_sample.md
    ├── sales_lead_snapshot.txt         — Phase 7 gallery output
    ├── invoice_processing_snapshot.txt
    ├── customer_support_snapshot.txt
    ├── invoice_processing_roi_waterfall.svg
    └── invoice_processing_bottleneck_heatmap.svg
```

## Regenerate outputs

```bash
# Regenerate Phase 7 gallery outputs
b2b-simulator generate-example-gallery --output-dir examples/outputs

# Regenerate v1.0.0 release reference outputs
b2b-simulator generate-release-examples --output-dir examples/outputs/final_release
```

## Original bundled examples

Three scenarios shipped with Phase 1-3:

- `sales-lead-qualification` — outbound sales lead qualification pipeline
- `invoice-processing` — accounts payable workflow
- `customer-support-ticket-resolution` — multi-tier helpdesk support

## Industry scenarios (Phase 8)

Eight new industry scenarios added in Phase 8:

- `healthcare-prior-authorization` — insurance prior-auth clinical review
- `insurance-claims-intake` — property/casualty FNOL through adjudication
- `hr-recruiting-screening` — candidate screening pipeline
- `procurement-vendor-onboarding` — vendor compliance and activation
- `legal-contract-review` — contract review through execution
- `it-support-triage` — L1/L2/L3 helpdesk resolution
- `finance-month-end-close` — monthly financial close
- `customer-onboarding-implementation` — B2B SaaS implementation

Run any scenario: `b2b-simulator run-example <slug> --cases 300`

## Assumption profiles

Three profiles per scenario are stored in:
`src/b2b_workflow_simulator/examples/data/assumptions/<slug>/`

- `base.json` — standard assumptions
- `conservative.json` — higher AI error rates, higher AI costs
- `aggressive.json` — lower AI costs, lower human costs

Use them: `b2b-simulator executive-snapshot <slug> --assumptions path/to/profile.json`

## Sample configs (Phase 9)

Six calibrated client configuration files are in:
`src/b2b_workflow_simulator/examples/data/configs/`

- `healthcare-prior-auth-small-plan.json`
- `insurance-claims-high-volume-carrier.json`
- `hr-recruiting-startup.json`
- `procurement-vendor-onboarding-enterprise.json`
- `legal-contract-review-midmarket.json`
- `it-support-triage-managed-service.json`

Validate a config: `b2b-simulator validate-config path/to/config.json`

## Disclaimer

All generated outputs are based on simulation assumptions, not real operational data.
They are provided as reference examples only.  See `docs/limitations.md`.
