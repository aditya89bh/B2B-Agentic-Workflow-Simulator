from b2b_workflow_simulator.capacity import ActorScheduler
from b2b_workflow_simulator.multi_resource import schedule_multi_resource_execution
from b2b_workflow_simulator.pool import ActorPool, PoolScheduler
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.worker import Worker


def manager(**overrides):
    defaults = {"actor_id": "manager", "name": "Manager", "hourly_cost": 60.0}
    defaults.update(overrides)
    return HumanActor(**defaults)


def legal(**overrides):
    defaults = {"actor_id": "legal", "name": "Legal", "hourly_cost": 90.0}
    defaults.update(overrides)
    return HumanActor(**defaults)


def test_both_participants_start_together_when_both_are_free():
    scheduler = ActorScheduler()
    pool_scheduler = PoolScheduler()

    scheduled = schedule_multi_resource_execution(
        [manager(), legal()],
        30.0,
        ready_time=0.0,
        scheduler=scheduler,
        pool_scheduler=pool_scheduler,
    )

    assert scheduled.start == 0.0
    assert scheduled.coordination_delay_minutes == 0.0
    assert scheduled.participant_actor_ids == ("manager", "legal")


def test_synchronizes_start_to_the_busier_participant():
    scheduler = ActorScheduler()
    pool_scheduler = PoolScheduler()
    # Legal is busy until minute 45.
    scheduler.schedule("legal", ready_time=0.0, duration=45.0, available_hours_per_day=8.0)

    scheduled = schedule_multi_resource_execution(
        [manager(), legal()],
        30.0,
        ready_time=0.0,
        scheduler=scheduler,
        pool_scheduler=pool_scheduler,
    )

    assert scheduled.start == 45.0
    # Manager was free at 0, so waited the full 45 minutes to sync with Legal.
    assert scheduled.coordination_delay_minutes == 45.0


def test_manager_calendar_reflects_synchronized_start_not_original_free_time():
    scheduler = ActorScheduler()
    pool_scheduler = PoolScheduler()
    scheduler.schedule("legal", ready_time=0.0, duration=45.0, available_hours_per_day=8.0)

    schedule_multi_resource_execution(
        [manager(), legal()],
        30.0,
        ready_time=0.0,
        scheduler=scheduler,
        pool_scheduler=pool_scheduler,
    )

    # Manager's calendar should now show busy through the synchronized window,
    # not the original [0, 30) window it would have used alone.
    assert scheduler.peek_free_at("manager") == 75.0


def test_cost_sums_every_participant():
    scheduler = ActorScheduler()
    pool_scheduler = PoolScheduler()

    scheduled = schedule_multi_resource_execution(
        [manager(hourly_cost=60.0), legal(hourly_cost=90.0)],
        60.0,
        ready_time=0.0,
        scheduler=scheduler,
        pool_scheduler=pool_scheduler,
    )

    assert scheduled.cost == 60.0 + 90.0


def test_primary_actor_determines_error_and_escalation_semantics():
    scheduler = ActorScheduler()
    pool_scheduler = PoolScheduler()
    agent = AIAgentActor(
        actor_id="reviewer_bot",
        name="Reviewer Bot",
        error_rate=0.1,
        escalation_rate=0.2,
    )

    scheduled = schedule_multi_resource_execution(
        [agent, legal()], 30.0, ready_time=0.0, scheduler=scheduler, pool_scheduler=pool_scheduler
    )

    assert scheduled.error_rate == 0.1
    assert scheduled.escalation_rate == 0.2
    assert scheduled.checks_escalation is True


def test_pool_participant_is_synchronized_alongside_plain_actors():
    scheduler = ActorScheduler()
    pool_scheduler = PoolScheduler()
    pool = ActorPool(
        actor_id="legal_team",
        name="Legal Team",
        workers=[Worker(worker_id="l1", name="Legal One", hourly_cost=90.0)],
    )
    # The pool's only worker is busy until minute 50.
    pool_scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=50.0)

    scheduled = schedule_multi_resource_execution(
        [manager(), pool], 20.0, ready_time=0.0, scheduler=scheduler, pool_scheduler=pool_scheduler
    )

    assert scheduled.start == 50.0
    assert scheduled.worker_id is None  # pool is not the primary actor here


def test_pool_as_primary_actor_reports_worker_id():
    scheduler = ActorScheduler()
    pool_scheduler = PoolScheduler()
    pool = ActorPool(
        actor_id="legal_team",
        name="Legal Team",
        workers=[Worker(worker_id="l1", name="Legal One", hourly_cost=90.0, error_rate=0.05)],
    )

    scheduled = schedule_multi_resource_execution(
        [pool, manager()], 20.0, ready_time=0.0, scheduler=scheduler, pool_scheduler=pool_scheduler
    )

    assert scheduled.worker_id == "l1"
    assert scheduled.error_rate == 0.05


def test_no_wait_when_scheduler_is_none_and_no_pools_involved():
    pool_scheduler = PoolScheduler()

    scheduled = schedule_multi_resource_execution(
        [manager(), legal()], 30.0, ready_time=10.0, scheduler=None, pool_scheduler=pool_scheduler
    )

    assert scheduled.start == 10.0
    assert scheduled.wait_minutes == 0.0
    assert scheduled.coordination_delay_minutes == 0.0
