# Team Pools and Workforce Scheduling

`docs/capacity_modeling.md` models capacity as one actor with a flat
daily-hours limit -- a reasonable model for a single specialist role,
but not for how most real operations actually staff a stage: a team of
several interchangeable people (or AI agent instances), each with their
own cost, speed, reliability, and working schedule, where work is
routed to whichever team member is available soonest. `pool.py`
extends the actor model to exactly that shape.

## Workers and shifts

A `Worker` (`primitives/worker.py`) is one team member: a `worker_id`,
`hourly_cost`, `speed_multiplier`, `error_rate`, an `available` flag for
modeling attrition or planned absence, and an optional list of `Shift`s.

A `Shift` (`primitives/shift.py`) is a recurring working window: which
weekdays it covers (`datetime.weekday()` numbering, 0=Monday), a
`start_hour`/`end_hour`, and `overtime_hours` -- additional capacity
available on that shift before it is considered exhausted for the day.
A worker with no shifts follows the pool's default availability; a
worker with shifts is only schedulable during those windows, which is
how weekday-only, weekend-only, or split day/night coverage is modeled:

```python
from b2b_workflow_simulator.primitives.shift import Shift
from b2b_workflow_simulator.primitives.worker import Worker

weekday_agent = Worker(
    worker_id="agent-1",
    name="Agent - Priya",
    hourly_cost=35.0,
    shifts=[Shift(name="Day shift", days=frozenset({0, 1, 2, 3, 4}), start_hour=9, end_hour=17)],
)
weekend_oncall = Worker(
    worker_id="agent-2",
    name="Agent - Sam (weekend on-call)",
    hourly_cost=42.0,  # weekend premium
    shifts=[Shift(name="Weekend on-call", days=frozenset({5, 6}), start_hour=8, end_hour=20, overtime_hours=4)],
)
```

## ActorPool

`ActorPool` (`pool.py`) extends `Actor` to hold a list of `Worker`s. It
is registered and referenced exactly like any other actor:

```python
from b2b_workflow_simulator.pool import ActorPool

support_team = ActorPool(actor_id="support_team", name="Support Team", workers=[weekday_agent, weekend_oncall])
workflow.add_actor(support_team)
workflow.add_node(Node("resolve", "Resolve Ticket", actor_id="support_team", base_duration_minutes=20, is_terminal=True))
```

Both simulation engines (`simple` and `discrete`) detect an `ActorPool`
via `isinstance` and delegate scheduling to `PoolScheduler` instead of
the single-actor `ActorScheduler` -- no other change to how a workflow
is built or simulated is required.

## Least-loaded routing

`PoolScheduler.schedule()` evaluates every currently-available worker
in the pool (skipping any with `available=False`), computes each one's
earliest possible start time given their shift, remaining daily
capacity, and current queue, and routes the task to whichever worker
can start soonest. Ties break on total busy minutes so far (preferring
the less-loaded worker), then on `worker_id` for full determinism. This
is a pure, side-effect-free comparison across candidates -- only the
winning worker's state is actually updated -- so the routing decision
never depends on the order workers happen to be listed in the pool.

## Overtime

A worker's shift defines `regular_hours` (`end_hour - start_hour`) and
`hours_with_overtime` (`regular_hours + overtime_hours`). The scheduler
will use overtime capacity to fit a task that would not otherwise fit
in the day, but reports it: `PoolScheduledTask.used_overtime` is `True`
whenever the assigned task's completion pushes past `regular_hours` for
that worker's day, giving visibility into how much of a team's output
depends on paying for overtime rather than staying within standard
shift capacity.

## Utilization tracking

`KPIResult` reports three levels of granularity once a run routes any
work through a pool:

- `pool_utilization[pool_id]`: aggregate busy time across every worker
  in the pool, as a fraction of their combined capacity across their
  active days.
- `worker_utilization[pool_id][worker_id]`: the same calculation scoped
  to one worker, useful for spotting an individual who is
  disproportionately loaded even when the pool average looks healthy.
- Per-worker task events carry a `worker_id` in their `details`, so an
  event log can be filtered down to exactly one team member's work.

From the CLI:

```bash
b2b-simulator team-utilization sales-lead-qualification --arrival-interval 10
```

prints raw actor/pool/worker utilization for a bundled example (see
`docs/capacity_planning.md` for turning these numbers into staffing
recommendations).

## Unavailable workers

Setting `Worker.available = False` removes a worker from routing
entirely, without needing to remove them from the pool definition --
useful for modeling planned leave, attrition mid-simulation (rebuild
the workflow with the flag flipped for a "what if this person left"
scenario), or a worker who has not yet started. `PoolScheduler.schedule()`
raises a clear `ValueError` if every worker in a pool is unavailable at
once, since that represents a genuinely unstaffed team rather than a
routing decision.

## What this model does not do

- It does not model cross-training or skill differences beyond
  `speed_multiplier` and `error_rate` -- every worker in a pool is
  assumed capable of every task routed to that pool.
- It does not model workers moving between pools mid-simulation (a
  worker belongs to exactly the one `ActorPool` they were added to).
- Shift definitions are static for the whole simulated period; there is
  no support for a worker's schedule changing partway through a run.

These are reasonable areas for a future phase once multi-team,
multi-skill routing has a concrete business example driving its design.
