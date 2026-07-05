# Capacity Planning

`docs/team_capacity.md` and `docs/capacity_modeling.md` show how to
*measure* utilization from a simulation run. `capacity_planning.py`
turns those numbers into a decision: is this role overloaded or
underutilized, how many workers would bring it to a healthy target, and
would a specific hire actually relieve the pressure it is meant to
relieve?

## Staffing recommendations

`analyze_capacity()` takes a `KPIResult` from a capacity-aware run and
returns a `CapacityPlan` with one `StaffingRecommendation` per actor or
pool that reported utilization:

```python
from b2b_workflow_simulator.capacity_planning import analyze_capacity, generate_capacity_report
from b2b_workflow_simulator.simulation import SimulationRunner

result = SimulationRunner(seed=1).run(workflow, num_cases=300, arrival_interval_minutes=10.0)
plan = analyze_capacity(result.kpi, target_utilization=0.75)
print(generate_capacity_report(plan))
```

From the CLI:

```bash
b2b-simulator capacity-analysis sales-lead-qualification --variant after --arrival-interval 10 --html-output capacity.html
```

`--variant` selects whether to analyze the "before" or "after" workflow
(default: `after`, since that is usually the one being staffed for a
rollout).

## How status is classified

Each resource is classified into exactly one status based on two
configurable thresholds (`overload_threshold`, default 90%, and
`underutilization_threshold`, default 40%):

- **Overloaded**: utilization at or above `overload_threshold`. The
  recommendation rounds *up* the headcount needed to bring utilization
  to `target_utilization` (default 75%), never under-provisioning an
  already-strained resource.
- **Underutilized**: utilization at or below `underutilization_threshold`.
  The recommendation rounds *down*, but never below one worker -- a
  role can be flagged as overstaffed, but never recommended out of
  existence entirely by this tool.
- **Balanced**: everything in between. No headcount change is
  recommended even if utilization is not exactly at the target, since
  a small deviation from target within the balanced band does not
  justify a staffing change on its own.

For a single `HumanActor` or `AIAgentActor` (not a pool), "current
headcount" is always 1; an overloaded single actor's recommendation is
effectively a suggestion to convert that role into an `ActorPool` with
more than one worker (see `docs/team_capacity.md`). For an `ActorPool`,
pass `pool_sizes={pool_id: count}` to `analyze_capacity()` so headcount
math starts from the real team size; if omitted, the count of workers
observed in `KPIResult.worker_utilization` is used instead.

## Hiring simulations

Rather than trusting a headcount formula in isolation, `simulate_hiring()`
actually re-runs the simulation with proposed new workers added to a
pool and compares the before/after impact directly:

```python
from b2b_workflow_simulator.capacity_planning import simulate_hiring, generate_hiring_report
from b2b_workflow_simulator.primitives.worker import Worker

extra_worker = Worker(worker_id="agent-new", name="New Hire", hourly_cost=38.0)
result = simulate_hiring(
    build_workflow,
    pool_actor_id="support_team",
    additional_workers=[extra_worker],
    num_cases=300,
    seed=1,
    arrival_interval_minutes=10.0,
)
print(generate_hiring_report(result))
```

`build_workflow` is called twice -- once as-is (the baseline) and once
with `additional_workers` appended to the named pool (the proposed
scenario) -- using the same seed and arrival pattern both times, so any
difference in the result is attributable to the hire and not to random
variation or a different case mix. The result reports utilization,
maximum queue depth, and average wait time on both sides, plus
convenience properties (`utilization_change`, `queue_depth_change`,
`wait_time_change_minutes`) for quickly checking whether the hire
actually helped.

## Worked example: is the redesigned team correctly staffed?

```bash
b2b-simulator capacity-analysis invoice-processing --variant after --cases 300 --arrival-interval 8
```

If the AI-augmented workflow's human AP Specialist role shows up
overloaded at realistic exception volumes, that is exactly the signal
that a rollout plan needs to budget for an additional specialist (or a
pool of them) before going live -- catching a staffing gap in
simulation is considerably cheaper than catching it after cases start
backing up in production.

## Worked example: would hiring one more agent actually help?

```python
from b2b_workflow_simulator.capacity_planning import simulate_hiring
from b2b_workflow_simulator.primitives.worker import Worker

result = simulate_hiring(
    build_understaffed_team_workflow,
    pool_actor_id="team",
    additional_workers=[Worker(worker_id="agent-4", name="Agent 4", hourly_cost=35.0)],
    num_cases=200,
    seed=1,
    arrival_interval_minutes=5.0,
)
print(f"Queue depth: {result.baseline_max_queue_depth} -> {result.proposed_max_queue_depth}")
print(f"Wait time: {result.baseline_avg_wait_minutes:.1f} -> {result.proposed_avg_wait_minutes:.1f} minutes")
```

Under light contention, adding one worker to an already-adequate team
barely moves the numbers -- a useful negative result, since it means
the budget is better spent elsewhere. Under heavy contention (a team
genuinely undersized for its arrival rate), the same hire produces a
large, visible drop in queue depth and wait time, which is the
quantified case for the hire that a plain utilization percentage alone
does not make as concretely.

## What this model does not do

- It does not optimize hiring across multiple pools simultaneously
  (each `simulate_hiring()` call evaluates one proposed change to one
  pool at a time; comparing several hiring scenarios means running the
  function once per scenario and comparing the results).
- It does not model ramp-up time for a new hire (a newly added `Worker`
  is scheduled at full `speed_multiplier`/`error_rate` from case one,
  rather than a training curve).
- It does not account for hiring cost or lead time in the
  recommendation itself -- `StaffingRecommendation` and
  `HiringSimulationResult` report the operational impact; combining
  that with a hiring budget and timeline is left to the caller.
