# Calibration Workflow

Before configuring a scenario for a client, gather real operational data to
replace the simulation's defaults.  The calibration questionnaire helps you
structure that data collection.

## Step-by-step calibration workflow

### Step 1: Generate the questionnaire

```bash
b2b-simulator calibration-template <scenario-slug> --output calibration.md
```

Example:

```bash
b2b-simulator calibration-template healthcare-prior-authorization --output pa_calibration.md
b2b-simulator calibration-template it-support-triage --format json --output it_calibration.json
```

The questionnaire has 8 sections:

| Section | What it measures |
|---|---|
| 1. Process Volume | Case volumes and arrival patterns |
| 2. Staffing and Cost | Fully-loaded hourly rates by role |
| 3. Cycle Time | Stage durations from real data |
| 4. Failure and Rework | Error rates and rework impact |
| 5. Escalation | Expected AI escalation rates |
| 6. Compliance | Regulatory constraints on automation |
| 7. AI Readiness | Data quality and existing AI maturity |
| 8. Implementation | One-time cost estimates and timeline |

### Step 2: Fill in with client data

Share the Markdown questionnaire with:
- Process owners (for stage durations and failure rates)
- Finance/HR (for hourly cost rates)
- IT/operations (for AI platform costs and integration estimates)

Key measurements to prioritize:

1. **Hourly cost per role** — most impactful on total cost delta
2. **Stage durations** — drives cycle-time improvement
3. **AI escalation rate** — the most uncertain assumption; use conservative profile

### Step 3: Translate answers to ScenarioConfig

Map questionnaire answers to config overrides:

| Questionnaire answer | Config field |
|---|---|
| Hourly cost per role | `ActorOverride.hourly_cost` |
| Stage duration (minutes) | `NodeOverride.base_duration_minutes` |
| Error/failure rate | `ActorOverride.error_rate` |
| AI escalation rate | `ActorOverride.escalation_rate` |
| Daily capacity (hours) | `ActorOverride.available_hours_per_day` |
| AI execution cost | `ActorOverride.cost_per_execution` |
| Implementation cost | `profile → implementation_cost` |
| Monthly case volume | `profile → num_cases` |

### Step 4: Review the config diff

Before running reports, check what changed:

```bash
b2b-simulator config-diff acme_config.json
```

The diff highlights:

- All changed parameter values
- High-risk changes (flagged with ⚠)
- Profile used

High-risk thresholds (triggers a warning):

| Change | Threshold |
|---|---|
| AI error rate reduction | > 50% |
| AI execution cost reduction | > 70% |
| Human hourly cost reduction | > 40% |
| Edge probability change | > ±0.30 |
| Node duration reduction | > 60% |

### Step 5: Run analysis and generate deliverables

```bash
# Validate
b2b-simulator validate-config acme_config.json

# One-page summary
b2b-simulator config-snapshot acme_config.json --html-output snapshot.html

# Full consultant packet
b2b-simulator config-packet acme_config.json --output-dir packet/

# Complete case study with diff
b2b-simulator config-case-study acme_config.json --output-dir case_study/
```

## Using assumption profiles with configs

Configs also pick up the scenario's assumption profiles for AI/human
multipliers.  Use `profile_name` in your config to select:

```json
{"profile_name": "conservative"}
```

Or pass `--assumptions` when running for additional multiplier control.

## Example: calibrating IT support triage

Imagine your client's L1 agents cost $22/hour (not the default $35), with a
slightly higher error rate due to high turnover.  Their L2 engineers are
senior staff at $75/hour.

```json
{
  "base_scenario_slug": "it-support-triage",
  "configured_slug": "it-support-client-xyz",
  "actor_overrides": [
    {"actor_id": "l1_agent", "hourly_cost": 22.0, "error_rate": 0.09},
    {"actor_id": "l2_engineer", "hourly_cost": 75.0}
  ],
  "profile_name": "conservative"
}
```

The conservative profile further doubles AI error rates to represent a
cautious estimate for the client's specific environment.

## Important reminder

Every output clearly states it is based on user-provided calibrated
assumptions.  Encourage clients to validate assumptions with actual
process data, not just informed estimates.
