# ScenarioConfig Schema Reference

A `ScenarioConfig` is a JSON file that customizes a registered scenario.  All
fields except `base_scenario_slug`, `configured_slug`, and `configured_name` are
optional.

## Top-level fields

```json
{
  "base_scenario_slug": "it-support-triage",
  "configured_slug": "it-support-acme",
  "configured_name": "IT Support — ACME",
  "client_name": "ACME Corporation",
  "description": "Calibrated for ACME's helpdesk team.",
  "profile_name": "base",
  "actor_overrides": [...],
  "node_overrides": [...],
  "edge_overrides": [...],
  "workflow_metadata": {...},
  "notes": "Free-text notes.",
  "limitations": ["Limitation 1.", "Limitation 2."],
  "created_by": "consultant-name",
  "version": "1.0"
}
```

| Field | Type | Default | Constraints |
|---|---|---|---|
| `base_scenario_slug` | string | required | Must be a registered scenario slug |
| `configured_slug` | string | required | Unique identifier for this config |
| `configured_name` | string | required | Display name |
| `client_name` | string | `""` | |
| `description` | string | `""` | |
| `profile_name` | string | `"base"` | One of: `base`, `conservative`, `aggressive` |
| `actor_overrides` | array | `[]` | See ActorOverride below |
| `node_overrides` | array | `[]` | See NodeOverride below |
| `edge_overrides` | array | `[]` | See EdgeOverride below |
| `workflow_metadata` | object | `null` | See WorkflowMetadataOverride below |
| `notes` | string | `""` | |
| `limitations` | array of strings | `[]` | |
| `created_by` | string | `""` | |
| `version` | string | `"1.0"` | |

## ActorOverride

Override one actor's parameters.  All fields except `actor_id` are optional.

```json
{
  "actor_id": "l1_agent",
  "name": "L1 Support Agent (Custom)",
  "hourly_cost": 25.0,
  "cost_per_execution": null,
  "speed_multiplier": 1.0,
  "error_rate": 0.06,
  "escalation_rate": null,
  "available_hours_per_day": 8.0
}
```

| Field | Applies to | Constraints |
|---|---|---|
| `actor_id` | all | Must exist in base scenario |
| `hourly_cost` | HumanActor | ≥ 0 |
| `cost_per_execution` | AIAgentActor | ≥ 0 |
| `speed_multiplier` | all | > 0 |
| `error_rate` | all | 0–1 |
| `escalation_rate` | AIAgentActor | 0–1 |
| `available_hours_per_day` | all | > 0 |

## NodeOverride

Override one workflow node's parameters.  All fields except `node_id` are optional.

```json
{
  "node_id": "l1_resolution",
  "name": "L1 Resolution (Custom)",
  "base_duration_minutes": 20.0,
  "actor_id": "l2_engineer",
  "is_terminal": null
}
```

| Field | Constraints |
|---|---|
| `node_id` | Must exist in base scenario |
| `base_duration_minutes` | ≥ 0 |
| `actor_id` | Must exist in base scenario when specified |

## EdgeOverride

Override one edge's probability.

```json
{
  "source": "pa_intake",
  "target": "clinical_review",
  "probability": 0.88
}
```

| Field | Constraints |
|---|---|
| `source` | Must be a node ID in base scenario |
| `target` | Must be a node ID in base scenario |
| `probability` | 0–1; all outgoing edges from `source` must sum to 1.0 |

**Note:** If you override one edge from a multi-branch node, you must also
override the other edges so they still sum to 1.0.

## WorkflowMetadataOverride

Override workflow display names.

```json
{
  "workflow_name_before": "Custom Before Name",
  "workflow_name_after": "Custom After Name",
  "description_before": "Custom before description.",
  "description_after": "Custom after description."
}
```

## Application order

Overrides are applied in this order:

1. Assumption profile multipliers (AI/human cost scaling)
2. Actor overrides (specific cost and rate changes)
3. Node overrides (duration and actor reassignment)
4. Edge probability overrides
5. Workflow metadata overrides

## Validation errors

The following will raise a `ConfigValidationError`:

- `base_scenario_slug` not in registry
- `profile_name` not one of `base`, `conservative`, `aggressive`
- Actor/node/edge ID not found in base scenario
- `error_rate` or `escalation_rate` outside 0–1
- Negative cost or duration
- Outgoing edges from any node do not sum to 1.0 after overrides
- Configured workflow fails `validate()`

## Sample configs location

Built-in sample configs are at:

```
src/b2b_workflow_simulator/examples/data/configs/
```

List them with:

```bash
b2b-simulator list-configs
b2b-simulator list-configs --format json
```
