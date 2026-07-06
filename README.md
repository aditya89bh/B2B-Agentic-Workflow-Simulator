# B2B Agentic Workflow Simulator

**Simulate AI transformation. Measure ROI. Generate consulting deliverables.**

A command-line digital twin that lets consultants, operations leaders, and product teams model a business workflow **before** and **after** introducing AI agents — and produce stakeholder-ready outputs without writing code.

> This is a directional simulation tool, not an operational monitoring system or certified financial model. All outputs are estimates based on user-provided assumptions.

---

## What is this?

Most AI transformation projects skip straight to building an agent and hoping it helps. This simulator inverts that: **model first, build second**.

You define a workflow as a graph of stages, actors, and handoffs, run it under both current (human-only) and redesigned (AI-assisted) configurations, and get a structured answer to: *does this pay off, where does it break, and what assumptions drive the result?*

**Who is it for?**
- Consultants preparing AI transformation business cases
- Operations leads evaluating whether to automate a process
- Finance/procurement teams estimating ROI before committing budget
- AI product teams stress-testing assumptions before building

**What problem does it solve?**
- Replaces spreadsheet ROI estimates with a reproducible, calibrated simulation
- Surfaces bottlenecks, escalation risks, and failure rates that spreadsheets miss
- Generates client-ready deliverables (snapshots, waterfalls, heatmaps, packets)
- Provides an 11-scenario industry library so you can start from a realistic baseline

---

## What can I run in 5 minutes?

```bash
pip install -e ".[dev]"

# Run a healthcare scenario
b2b-simulator executive-snapshot healthcare-prior-authorization --cases 300

# Generate a full consulting packet
b2b-simulator consultant-packet invoice-processing --cases 300 --implementation-cost 8000 --output-dir packet/

# Compare all 11 scenarios
b2b-simulator scenario-matrix

# Generate calibration questionnaire
b2b-simulator calibration-template it-support-triage --output calibration.md

# Customize for a specific client
b2b-simulator config-snapshot src/b2b_workflow_simulator/examples/data/configs/healthcare-prior-auth-small-plan.json
```

---

## Key capabilities

| Area | What it does |
|---|---|
| **Core simulation** | Before/after KPI comparison, ROI, payback period |
| **Scenario library** | 11 industry scenarios (healthcare, insurance, HR, procurement, legal, IT, finance, CS) |
| **Organizational model** | Departments, teams, budgets, shared resources, health score |
| **Visualization** | Mermaid flowcharts, ROI waterfall SVGs, bottleneck heatmaps |
| **Consulting outputs** | Executive snapshot, consultant packet, case study directory |
| **Scenario customization** | ScenarioConfig JSON files with actor/node/edge overrides |
| **Calibration** | 8-section questionnaire template for client data collection |
| **Scenario matrix** | Cross-scenario KPI comparison table for prioritization |
| **Assumption profiles** | Base, conservative, and aggressive profiles per scenario |

---

## Quickstart

```bash
git clone https://github.com/aditya89bh/B2B-Agentic-Workflow-Simulator
cd B2B-Agentic-Workflow-Simulator
pip install -e ".[dev]"

# Verify installation
b2b-simulator --version
b2b-simulator list-scenarios
```

---

## Scenario library (11 scenarios)

```bash
b2b-simulator list-scenarios
b2b-simulator list-scenarios --category healthcare
```

| Slug | Category | Description |
|---|---|---|
| `sales-lead-qualification` | Sales | Lead qualification pipeline |
| `invoice-processing` | Finance | Accounts payable workflow |
| `customer-support-ticket-resolution` | Customer Success | Multi-tier support triage |
| `healthcare-prior-authorization` | Healthcare | Insurance prior-auth review |
| `insurance-claims-intake` | Insurance | FNOL through adjudication |
| `hr-recruiting-screening` | HR | Candidate screening pipeline |
| `procurement-vendor-onboarding` | Procurement | Vendor compliance and activation |
| `legal-contract-review` | Legal | Contract review through execution |
| `it-support-triage` | IT | Helpdesk L1/L2/L3 resolution |
| `finance-month-end-close` | Finance | Month-end close process |
| `customer-onboarding-implementation` | Customer Success | B2B SaaS implementation |

---

## Scenario customization

Adapt any scenario to your client's specific parameters without editing Python:

```bash
# See what's available
b2b-simulator list-configs

# Validate a config
b2b-simulator validate-config path/to/config.json

# See what changed from base
b2b-simulator config-diff path/to/config.json

# Run client-specific analysis
b2b-simulator config-snapshot path/to/config.json
b2b-simulator config-case-study path/to/config.json --output-dir case_study/
```

Config format:

```json
{
  "base_scenario_slug": "it-support-triage",
  "configured_slug": "it-support-acme",
  "configured_name": "IT Support — ACME Corp",
  "client_name": "ACME Corporation",
  "profile_name": "base",
  "actor_overrides": [
    {"actor_id": "l1_agent", "hourly_cost": 25.0, "error_rate": 0.05}
  ],
  "node_overrides": [
    {"node_id": "incident_receipt", "base_duration_minutes": 8.0}
  ]
}
```

---

## Consultant packet export

One command generates a full stakeholder deliverable directory:

```bash
b2b-simulator consultant-packet invoice-processing \
  --cases 300 --implementation-cost 8000 --output-dir packet/
```

Contents: `executive_snapshot.txt`, `executive_snapshot.html`, `workflow_before.mmd`, `workflow_after.mmd`, `roi_waterfall.svg`, `bottleneck_heatmap.svg`, `kpi_summary.json`, `assumptions.json`, `recommendations.txt`, `README.md`.

---

## Case-study generation

```bash
# All scenarios, all profiles
b2b-simulator generate-case-studies --output-dir case_studies/

# One scenario
b2b-simulator generate-case-studies --scenario healthcare-prior-authorization --output-dir case_studies/
```

Each case study includes executive snapshots, Mermaid diagrams, ROI waterfall, bottleneck heatmap, KPI JSON, and full consultant packet subdirectories for base, conservative, and aggressive assumption profiles.

---

## Scenario matrix

```bash
b2b-simulator scenario-matrix
b2b-simulator scenario-matrix --profile conservative --format json --output matrix.json
```

Ranks all 11 scenarios by ROI, cost savings, cycle-time improvement, and risk level under one assumption profile.

---

## Calibration workflow

```bash
b2b-simulator calibration-template healthcare-prior-authorization --output calibration.md
```

Generates an 8-section questionnaire (volume, staffing costs, cycle times, failure rates, escalation, compliance, AI readiness, implementation cost) to gather real client data before running the simulation.

---

## Architecture overview

```
Phases 1–4:  Simulation engine, KPI, redesign/ROI, portfolio, sensitivity, Monte Carlo, capacity
Phase 5:     Governance/risk/compliance, AI adoption readiness, executive report
Phase 6:     Organization digital twin (departments, teams, budgets, health score, growth)
Phase 6.5:   Foundation hardening (collect_events mode, org-aware restructuring, CI)
Phase 7:     Visualization and consulting output layer
Phase 8:     Industry scenario library (11 scenarios)
Phase 9:     Scenario customization and calibration toolkit
Phase 10:    v1.0.0 release hardening
```

The full architecture is documented in `docs/architecture.md`.

---

## Example outputs

See `examples/outputs/` for deterministic generated outputs:

- `examples/outputs/final_release/` — v1.0.0 reference outputs
- `examples/outputs/invoice_processing_snapshot.txt`
- `examples/outputs/invoice_processing_roi_waterfall.svg`

Regenerate with:

```bash
b2b-simulator generate-example-gallery --output-dir examples/outputs
b2b-simulator generate-release-examples --output-dir examples/outputs/final_release
```

---

## Testing and validation

```bash
pytest                  # 1822+ tests, ~8s
ruff check .            # zero lint errors
python -m build         # sdist + wheel
b2b-simulator --version # b2b-workflow-simulator 1.0.0
```

CI runs on every push to `main` and every pull request, across Python 3.10, 3.11, and 3.12.

---

## Limitations

- All outputs are **directional estimates based on simulation assumptions**, not validated operational data.
- Stage durations, error rates, and costs default to industry approximations; calibrate with real data before presenting to stakeholders.
- The simulation does not model regulatory compliance enforcement, counterparty behavior, or multi-entity consolidation.
- AI performance is modeled as error rates and escalation rates; actual AI quality depends heavily on data, prompting, and context not captured here.
- Seasonality, learning curves, and organizational change management are not modeled.
- See `docs/limitations.md` for a complete list.

---

## Roadmap

- [x] Phase 1–4: Core simulation engine
- [x] Phase 5: Governance and risk layer
- [x] Phase 6: Organizational digital twin
- [x] Phase 7: Visualization and consulting outputs
- [x] Phase 8: Industry scenario library
- [x] Phase 9: Scenario customization and calibration
- [x] Phase 10: v1.0.0 release hardening
- [ ] Phase 11+: Web interface, multi-scenario optimization, additional industries

---

## Contributing

See `CONTRIBUTING.md` for local setup, commit conventions, and PR checklist.

Key rules:
- `pytest`, `ruff check .`, and `python -m build` must all pass before submitting a PR.
- No Co-authored-by trailers; author all commits with your own identity.
- Every behavioral change must have tests.

---

## License

MIT License. See `LICENSE` for full text.
