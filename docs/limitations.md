# Limitations

> This tool produces directional estimates based on simulation assumptions.
> It is not an operational monitoring system, a certified financial model,
> or a substitute for real process data.

## Modeling limitations

**Workflow structure**
- Workflows are modeled as directed acyclic graphs; cyclical re-work loops are not supported.
- Every case follows the same graph; case-type routing (e.g. different paths by product line) is not modeled.
- Multi-entity consolidation is not modeled.

**Actor behavior**
- Human actors are modeled with fixed hourly cost, speed, and error rate; learning curves, fatigue, and skill variation are not captured.
- AI agent quality is modeled as error rate and escalation rate; actual AI performance depends on data quality, prompting, and context not modeled here.
- Counterparty behavior (e.g. vendor response times, negotiation outcomes) is not modeled.

**Capacity and scheduling**
- The simple engine approximates queueing; use `--engine discrete` for more accurate contention modeling.
- 24/7 operations require custom `available_hours_per_day` settings; defaults assume single-shift staffing.
- Seasonality, surge events, and demand variability beyond arrival intervals are not modeled.

**Cost modeling**
- AI per-execution costs do not include platform licensing, infrastructure, or change management overhead.
- Implementation cost is a one-time estimate; ongoing AI platform costs must be added separately.
- Currency is treated as a single unit; multi-currency workflows are not supported.

## Scenario limitations

Each scenario has specific limitations documented in:

- `ScenarioDefinition.limitations` (accessible via `get_scenario(slug).limitations`)
- `ScenarioConfig.limitations` (per configured variant)
- Case-study `README.md` files

The scenario library uses representative industry approximations, not benchmark-validated figures.
**Validate all stage durations, error rates, and costs against your real process data before presenting to stakeholders.**

## What this tool cannot do

- Monitor live operational systems
- Enforce compliance during execution (compliance checks are post-hoc analytical)
- Predict exact outcomes for a specific organization
- Account for organizational politics, change resistance, or adoption dynamics
- Replace a formal feasibility study or due-diligence process

## Statistical validity

The simulator uses Monte Carlo sampling with a fixed seed for reproducibility.
For robust uncertainty analysis, use `--engine discrete` and `monte-carlo-example` with multiple seeds.
Single-seed runs are directional; do not present confidence intervals from a single run.

## Roadmap items that address current limitations

- Web UI for interactive workflow authoring
- Multi-currency and time-zone-aware scheduling
- Cross-training and skill-based pool routing
- In-simulation policy/compliance/SLA enforcement
