# Scenario Customization

Phase 9 introduces a customization and calibration layer that lets you adapt
any registered scenario to your organization's specific parameters without
editing Python code.

## How it works

A **ScenarioConfig** is a JSON file that contains sparse overrides on top of a
registered base scenario.  You only specify what changes; everything else
inherits from the base scenario's defaults.

```
Base scenario: it-support-triage
    ↓ apply assumption profile (base/conservative/aggressive)
    ↓ apply actor overrides (hourly costs, error rates)
    ↓ apply node overrides (durations, actor reassignments)
    ↓ apply edge probability overrides
    → Configured workflow ready for simulation
```

The original scenario workflows are **never mutated**.  A fresh copy is created
for each configuration run.

## Quick start

### 1. Find a base scenario

```bash
b2b-simulator list-scenarios
b2b-simulator list-configs          # see bundled sample configs
```

### 2. View the config structure

```bash
b2b-simulator validate-config src/b2b_workflow_simulator/examples/data/configs/it-support-triage-managed-service.json
```

### 3. Generate a calibration questionnaire

```bash
b2b-simulator calibration-template it-support-triage --output calibration_questions.md
```

Fill in the questionnaire with your organization's data, then create a config:

### 4. Create your config file

```json
{
  "base_scenario_slug": "it-support-triage",
  "configured_slug": "it-support-acme",
  "configured_name": "IT Support — ACME Corp",
  "client_name": "ACME Corporation",
  "description": "Calibrated for ACME's 15-person helpdesk team.",
  "profile_name": "base",
  "actor_overrides": [
    {"actor_id": "l1_agent", "hourly_cost": 25.0, "error_rate": 0.05},
    {"actor_id": "l2_engineer", "hourly_cost": 55.0}
  ],
  "node_overrides": [
    {"node_id": "incident_receipt", "base_duration_minutes": 8.0},
    {"node_id": "l1_resolution", "base_duration_minutes": 22.0}
  ],
  "edge_overrides": [],
  "notes": "L1 agents are offshore; lower cost but slightly higher error rate.",
  "limitations": [
    "CAT events not modeled.",
    "Client-specific SLA penalties not included."
  ],
  "created_by": "consulting-team",
  "version": "1.0"
}
```

Save as `acme_it_support.json`.

### 5. Run and analyze

```bash
# Validate the config
b2b-simulator validate-config acme_it_support.json

# See what changed from base
b2b-simulator config-diff acme_it_support.json

# Run before/after KPI comparison
b2b-simulator run-config acme_it_support.json

# Full ROI report
b2b-simulator compare-config acme_it_support.json

# Executive snapshot
b2b-simulator config-snapshot acme_it_support.json

# Full consultant packet
b2b-simulator config-packet acme_it_support.json --output-dir acme_packet/

# Complete case study with config diff
b2b-simulator config-case-study acme_it_support.json --output-dir acme_case_study/
```

## ScenarioConfig reference

| Field | Type | Required | Description |
|---|---|---|---|
| `base_scenario_slug` | string | ✓ | Slug of a registered scenario |
| `configured_slug` | string | ✓ | Unique slug for this configuration |
| `configured_name` | string | ✓ | Display name |
| `client_name` | string | | Client / organization name |
| `description` | string | | One-sentence description |
| `profile_name` | string | | `"base"`, `"conservative"`, or `"aggressive"` |
| `actor_overrides` | list | | Actor parameter changes |
| `node_overrides` | list | | Node parameter changes |
| `edge_overrides` | list | | Edge probability changes |
| `workflow_metadata` | object | | Workflow name/description overrides |
| `notes` | string | | Free-text visible in reports |
| `limitations` | list | | Explicit limitations for this configuration |
| `created_by` | string | | Author identifier |
| `version` | string | | Config schema version |

## Override types

### ActorOverride

```json
{
  "actor_id": "l1_agent",
  "hourly_cost": 25.0,
  "error_rate": 0.05,
  "speed_multiplier": 1.0,
  "available_hours_per_day": 8.0
}
```

For AI agents: use `cost_per_execution`, `error_rate`, `escalation_rate`.

### NodeOverride

```json
{
  "node_id": "incident_receipt",
  "base_duration_minutes": 8.0,
  "actor_id": "new_actor_id"
}
```

### EdgeOverride

```json
{
  "source": "pa_intake",
  "target": "clinical_review",
  "probability": 0.88
}
```

**Important:** All outgoing edges from a source node must sum to 1.0 after overrides.

## Validation rules

- All actor/node/edge IDs must exist in the base scenario.
- Error rates must be 0–1.
- Costs and durations must be non-negative.
- Outgoing edge probabilities from any node must sum to 1.0.
- Configured workflows are validated before simulation.

## Disclaimer

All outputs from configured scenarios are based on user-provided assumptions.
They are directional estimates, not validated business cases.  Validate all
input values against real operational data before presenting to stakeholders.
