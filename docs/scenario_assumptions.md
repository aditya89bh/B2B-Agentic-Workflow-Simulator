# Scenario Assumptions Guide

Every scenario in this library makes explicit assumptions about process
durations, actor costs, AI error rates, and escalation rates.  These must be
validated with real operational data before use in stakeholder decisions.

## What to measure before using a scenario

### Process durations (base_duration_minutes)

The most important input.  Collect actual timing data for each stage:

- Time-motion studies or workflow analytics
- Ticketing system timestamps (JIRA, ServiceNow, Salesforce)
- Process mining tools (Celonis, Signavio)

### Human actor costs (hourly_cost)

Use fully-loaded cost (salary + benefits + overhead):

- HR: typically 1.3–1.5× base salary
- Contractors: bill rate directly
- Shared services: allocate based on capacity consumed

### AI error rates and escalation rates

These are the most uncertain inputs.  For initial pilots:

- Start with vendor-provided benchmarks (treat as optimistic)
- Use `conservative` profile (2× error rate) for board-level decisions
- Measure actual error and escalation rates after 30–60 days in production

### Implementation cost

Include:
- AI platform licensing or API costs (first year)
- Integration development (ERP, CRM, HRIS connectors)
- Training data collection and labeling
- Change management and training
- QA and testing

Do NOT include:
- Hardware infrastructure (usually negligible for SaaS AI)
- Ongoing per-execution costs (model these in `ai_cost_multiplier`)

## Assumption profile profiles

Three profiles ship with every scenario:

| Profile | AI error multiplier | AI cost multiplier | Use when |
|---|---|---|---|
| `base` | 1.0× | 1.0× | Initial exploration, technology demo |
| `conservative` | 2.0× | 1.5× | Board presentation, investment decision |
| `aggressive` | 0.5–0.7× | 0.5–0.7× | Technology maturity assessment, best case |

## Creating a custom profile

```bash
cat > my_profile.json << 'EOF'
{
  "num_cases": 500,
  "seed": 1,
  "implementation_cost": 20000.0,
  "ai_error_rate_multiplier": 1.8,
  "ai_cost_multiplier": 1.2,
  "human_hourly_cost_multiplier": 1.1,
  "description": "My calibrated profile based on Q3 pilot data"
}
EOF

b2b-simulator executive-snapshot invoice-processing --assumptions my_profile.json
```

## Important limitations across all scenarios

All scenarios share these modeling limitations:

1. **Fixed case structure:** every case follows the same workflow graph.
   Real processes have case-type routing not modeled here.

2. **Stationary assumptions:** error rates and durations don't change over
   time.  Real AI systems improve (or degrade) as data accumulates.

3. **No external dependencies:** counterparty behavior, regulatory delays,
   and system downtime are not modeled.

4. **Single-period analysis:** seasonality, ramp-up periods, and learning
   curves are not captured.

5. **No organizational change management:** adoption friction, training
   overhead, and resistance to change can significantly affect realized
   benefits.

The goal of these scenarios is to provide a structured, transparent framework
for directional analysis — not to replace operational measurement or
management consulting judgment.
