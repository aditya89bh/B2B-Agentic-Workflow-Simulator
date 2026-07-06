# B2B Agentic Workflow Simulator

**Simulate AI transformation. Measure ROI. Generate consulting deliverables.**

An organizational digital twin that lets consultants, operations leaders, and product teams model a business workflow **before** and **after** introducing AI agents — and produce stakeholder-ready outputs without writing code.

> **Important:** This is a directional simulation tool, not an operational monitoring system or certified financial model. All outputs are estimates based on user-provided assumptions.

---

## What can I run in 5 minutes?

```bash
pip install -e ".[dev]"

# Run a healthcare scenario
b2b-simulator executive-snapshot healthcare-prior-authorization --cases 300

# Generate a consultant packet
b2b-simulator consultant-packet invoice-processing --cases 300 --implementation-cost 8000 --output-dir packet/

# Compare all 11 scenarios side by side
b2b-simulator scenario-matrix

# Generate a calibration questionnaire
b2b-simulator calibration-template it-support-triage --output calibration.md
```

---

## Key capabilities

| Area | Description |
|---|---|
| Core simulation | Before/after KPI comparison, ROI, payback period |
| Scenario library | 11 industry scenarios across 7 business categories |
| Organizational model | Departments, teams, budgets, shared resources, health score |
| Visualization | Mermaid flowcharts, ROI waterfall SVGs, bottleneck heatmaps |
| Consulting outputs | Executive snapshot, consultant packet, case-study directory |
| Scenario customization | JSON-driven overrides for client-specific calibration |
| Scenario matrix | Cross-scenario prioritization ranking |

---

## 11 registered scenarios

Healthcare · Insurance · HR · Procurement · Legal · IT · Finance · Customer Success · Sales

```bash
b2b-simulator list-scenarios
```

---

## Start here

- [Quickstart](quickstart.md) — install and run in 5 minutes
- [Concepts](concepts.md) — understand the simulation model
- [Scenario Library](scenario_library.md) — all 11 industry scenarios
- [CLI Reference](cli_reference.md) — complete command reference
- [Limitations](limitations.md) — what this tool cannot do

---

## Validation status

- **1822+ tests** passing across Python 3.10, 3.11, 3.12
- **Zero lint errors** (`ruff check .`)
- **CI** on every push to `main`
- **Version:** 1.0.0
