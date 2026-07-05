# Capacity Modeling

By default, the simulator treats every case as independent: an actor is
always immediately available, so ten cases can all start at node "A" at
the same instant with no contention. That is a reasonable simplification
for understanding a single case's cost and duration, but it hides a
question every real operations leader cares about: *what happens when
demand exceeds capacity?*

Capacity-aware simulation answers that question by modeling actors as
finite, shared resources.

## Turning it on

Pass `arrival_interval_minutes` to `SimulationRunner.run()`:

```python
result = SimulationRunner(seed=42).run(
    workflow,
    num_cases=500,
    arrival_interval_minutes=15.0,  # a new case arrives every 15 minutes
)
```

From the CLI:

```bash
b2b-simulator compare-example sales-lead-qualification --arrival-interval 15
```

When `arrival_interval_minutes` is omitted (the default), capacity
constraints are disabled entirely and results match the simple,
independent-case model described in `docs/architecture.md`.

## How actors are modeled

Each actor (`HumanActor` or `AIAgentActor`) has an `available_hours_per_day`
field -- 8 hours by default for humans, 24 for AI agents, both
overridable per actor. The `ActorScheduler` (in `capacity.py`) tracks,
for each actor:

- `free_at`: the next time this actor is free to start new work.
- How many minutes of work it has already been assigned on the current
  calendar day.

When a task needs an actor, the scheduler computes a start time that
respects two constraints:

1. **Single-server queueing**: the task cannot start before the actor
   finishes whatever it is currently assigned (`free_at`).
2. **Daily capacity**: if starting the task would push the actor past
   `available_hours_per_day` for the current day, the task is pushed to
   the start of the next day instead.

The difference between when a case was ready for an actor and when the
actor actually started the work is **wait time**. This is tracked
separately from **execution time** (the actual duration of the task)
throughout the simulation:

- `KPIResult.total_wait_minutes` / `avg_wait_time_minutes`: aggregate and
  per-case wait time across the whole run.
- `KPIResult.actor_wait_minutes`: wait time attributable to each actor,
  useful for pinpointing exactly which role is the constraint.
- `KPIResult.node_total_duration_minutes`: unaffected by wait time --
  this is pure execution time, so bottleneck analysis is not skewed by
  queueing effects.

## Utilization

`KPIResult.actor_utilization` reports, for each actor that did any work,
the fraction of its available capacity that was consumed:

```
utilization = total busy minutes / (available_hours_per_day * 60 * days_active)
```

`days_active` is the number of distinct calendar days that actor was
assigned any work during the run, so utilization reflects actual load
relative to actual capacity rather than an arbitrary time window.

As a rule of thumb:

- Below ~60%: the actor has slack; queueing should be minimal.
- 60-85%: healthy utilization for most business processes.
- Above ~90%: the actor is at high risk of becoming a bottleneck under
  any additional variability (see `docs/redesign_analysis.md` for how
  this shows up as a flagged risk in the ROI report).

## A worked example

```bash
b2b-simulator compare-example sales-lead-qualification --cases 200 --arrival-interval 15
```

At a 15-minute arrival interval, 200 leads arrive over roughly 50 hours
of simulated time. If the "before" workflow's Account Executive can only
process a discovery call every 30 minutes, the queue grows steadily
across the run, and both `avg_wait_time_minutes` and the AE's
`actor_utilization` will reflect that overload -- exactly the kind of
signal that tells you *before* a rollout that a redesign needs more
capacity on that role, not just a faster process.

## What this model does not do

- It does not run a fully general discrete-event simulation across
  cases; cases are processed in arrival order rather than interleaved by
  a global event queue. For the FIFO, single-queue-per-actor processes
  this simulator targets, that distinction rarely changes the results,
  but it means true multi-actor race conditions are not modeled.
- It does not model partial-day carryover of a single task (a task
  either fits in the remaining daily capacity or is pushed to the next
  day in full).
- It does not model shift schedules, holidays, or part-time actors --
  `available_hours_per_day` is a flat daily figure.

These are reasonable areas for a future phase once the current model has
been validated against more workflows.
