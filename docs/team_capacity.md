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

## Multi-resource tasks

Everything above still schedules one actor (or one pool) per task. Some
real tasks need more than one resource *at the same time*: a contract
needs a Manager and Legal to sign off together, an AI agent's draft needs
a Human Reviewer before it ships, a large payment needs Finance and
Procurement in the same review. `Node.additional_actor_ids` models exactly
this -- a tuple of extra actor (or pool) IDs that must all be
simultaneously available alongside the node's primary `actor_id`:

```python
workflow.add_actor(HumanActor(actor_id="manager", name="Manager", hourly_cost=60.0))
workflow.add_actor(HumanActor(actor_id="legal", name="Legal Counsel", hourly_cost=90.0))
workflow.add_node(
    Node(
        "contract_signoff",
        "Contract Sign-off",
        actor_id="manager",
        additional_actor_ids=("legal",),
        base_duration_minutes=30,
    )
)
```

`Node.is_multi_resource` is `True` whenever `additional_actor_ids` is
non-empty; `Node.required_actor_ids` returns every required actor ID,
primary first. Both simulation engines detect this and delegate to
`multi_resource.schedule_multi_resource_execution()` instead of the
single-actor/single-pool path, which finds the latest of every
participant's earliest availability (so no participant is double-booked),
reserves that joint start time on every participant's calendar, and sums
their individual costs. The primary actor (`actor_id`) determines the
task's visible duration, error rate, and escalation behavior, matching the
semantics of a single-actor node exactly when `additional_actor_ids` is
empty -- existing workflows are completely unaffected.

The extra wait this synchronization introduces beyond what the fastest
available participant would have experienced alone is tracked as
coordination delay: `KPIResult.total_coordination_delay_minutes` (summed
across every case), `KPIResult.node_coordination_delay_minutes` (broken
down by node, for identifying the most expensive steps to synchronize),
and `KPIResult.multi_resource_task_count` (how many task executions needed
more than one actor). A node with heavy coordination delay is a concrete,
quantified case for co-locating the two roles' calendars, adding an
on-call rotation, or reconsidering whether the sign-off genuinely needs
both participants present at once.

## What this model does not do

- It does not model cross-training or skill differences beyond
  `speed_multiplier` and `error_rate` -- every worker in a pool is
  assumed capable of every task routed to that pool.
- It does not model workers moving between pools mid-simulation (a
  worker belongs to exactly the one `ActorPool` they were added to).
- Shift definitions are static for the whole simulated period; there is
  no support for a worker's schedule changing partway through a run.
- Multi-resource tasks do not model partial participation or a
  participant leaving early -- every required actor is reserved for the
  full primary-actor duration, and a task cannot proceed with fewer than
  all of its required participants.

These are reasonable areas for a future phase once multi-team,
multi-skill routing has a concrete business example driving its design.
