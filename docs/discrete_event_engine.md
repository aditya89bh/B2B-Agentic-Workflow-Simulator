# Discrete-Event Simulation Engine

The default ("simple") engine processes cases one at a time, in arrival
order: it runs case 1 to completion (subject to queueing against
whatever actors are busy from earlier cases), then case 2, and so on.
For the FIFO, single-queue-per-actor processes this simulator targets,
that produces the same wait times and utilization as a fully
event-driven simulation in the vast majority of cases -- but "the vast
majority" is not "all," and `docs/capacity_modeling.md` called this out
explicitly as a limitation. The discrete-event engine closes that gap.

## Turning it on

Pass `engine="discrete"` to `SimulationRunner.run()`:

```python
result = SimulationRunner(seed=42).run(
    workflow,
    num_cases=500,
    arrival_interval_minutes=15.0,
    engine="discrete",
)
```

From the CLI:

```bash
b2b-simulator run-example sales-lead-qualification --engine discrete
b2b-simulator compare-example sales-lead-qualification --engine discrete --arrival-interval 15
```

`engine` defaults to `"simple"` everywhere, so every existing call site,
script, and CLI invocation keeps behaving exactly as before. The two
engines share the same scheduling helpers (`schedule_task_execution()`
in `simulation.py`), the same `ActorScheduler`/`PoolScheduler`, and
produce the same `SimulationResult` shape, so switching engines never
changes what a `KPIResult` or event log looks like -- only how
precisely queueing across many simultaneously in-flight cases is
resolved.

## How it works

`DiscreteEventEngine` (in `discrete_event.py`) maintains a single global
priority queue of pending events, ordered by `(timestamp, priority,
sequence_number)`:

1. **Arrival events**: one per case, generated up front from either
   `arrival_interval_minutes` (fixed spacing) or an `ArrivalModel` (see
   `docs/advanced_sensitivity.md`'s arrival section, or below).
2. **Task completion events**: pushed once a task's start time and
   duration are resolved, to fire when the task finishes.

Processing an arrival starts the case's first node; processing a task
completion records the outcome (success, failure, or escalation) and
either starts the next node or ends the case. Both paths call the same
`schedule_task_execution()` helper the simple engine uses, so an actor
or pool is asked for the earliest available slot exactly the same way
regardless of engine.

The priority tuple's second element deliberately breaks ties so that a
task completion is processed *before* an arrival scheduled for the same
timestamp -- freeing the resource before a new case can contend for it,
rather than leaving an artifact of processing order to chance. The
third element, a monotonically increasing sequence number, breaks any
remaining ties deterministically, so two events at the same timestamp
and priority are always processed in the order they were pushed.

## Why results can differ from the simple engine

The simple engine finalizes one case completely before starting the
next case's simulation, even though the *scheduling* of individual
tasks still respects actor availability. Under light load the two
engines produce identical results, because there is rarely more than
one case actually contending for an actor at once. Under heavy
contention -- many cases queued for the same actor, especially with an
`ArrivalModel` that produces bursts (batched or peak-hour arrivals) --
the discrete-event engine's true chronological interleaving can route
a specific task to a different point in the queue than the simple
engine's arrival-order processing would, producing small differences in
individual wait times (though aggregate KPIs typically converge at
realistic case volumes). Both are internally consistent and
deterministic for a given seed; neither is "more correct" for the FIFO
processes this simulator targets, but the discrete-event engine's model
is the more general one and is recommended whenever you are modeling
bursty or batched arrivals.

## Determinism

Both engines seed a single `random.Random` from the `SimulationRunner`'s
`seed`. The discrete-event engine draws from that RNG in the same
order the simple engine would for any single case (duration sampling,
error/escalation rolls, branch selection), so a workflow with no
contention produces byte-identical `KPIResult`s under both engines given
the same seed. Once contention changes processing order, the *sequence*
of RNG draws across cases can shift -- this is expected and is why the
two engines are not guaranteed to produce identical results under load,
only each internally reproducible.

## A worked example

```bash
b2b-simulator run-example sales-lead-qualification --cases 300 --engine discrete --seed 7
```

Run the same command with `--engine simple` and compare: under normal
example parameters the KPI tables will be very close, if not identical.
To see a case where they diverge, simulate a workflow with an
under-provisioned actor and bursty arrivals (an `ArrivalModel` with
`kind="batched"`) -- that is exactly the scenario the discrete-event
engine was built to model faithfully.
