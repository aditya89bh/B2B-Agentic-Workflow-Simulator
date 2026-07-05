import pytest

from b2b_workflow_simulator.pool import ActorPool, PoolScheduler
from b2b_workflow_simulator.primitives.shift import Shift
from b2b_workflow_simulator.primitives.worker import Worker


def build_pool(**overrides) -> ActorPool:
    defaults = {
        "actor_id": "support-team",
        "name": "Support Team",
        "available_hours_per_day": 8.0,
        "workers": [
            Worker(worker_id="a", name="Agent A", hourly_cost=40.0),
            Worker(worker_id="b", name="Agent B", hourly_cost=40.0),
        ],
    }
    defaults.update(overrides)
    return ActorPool(**defaults)


def test_pool_rejects_empty_worker_list():
    with pytest.raises(ValueError, match="workers"):
        ActorPool(actor_id="team", name="Team", workers=[])


def test_pool_rejects_duplicate_worker_ids():
    with pytest.raises(ValueError, match="unique"):
        ActorPool(
            actor_id="team",
            name="Team",
            workers=[Worker(worker_id="a", name="A"), Worker(worker_id="a", name="A2")],
        )


def test_pool_get_worker_returns_matching_worker():
    pool = build_pool()

    assert pool.get_worker("a").name == "Agent A"


def test_pool_get_worker_raises_for_unknown_id():
    pool = build_pool()

    with pytest.raises(KeyError):
        pool.get_worker("nobody")


def test_scheduler_routes_first_task_to_any_idle_worker():
    pool = build_pool()
    scheduler = PoolScheduler()

    outcome = scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=30.0)

    assert outcome.worker_id in {"a", "b"}
    assert outcome.wait_minutes == 0.0
    assert outcome.start == 0.0


def test_scheduler_uses_least_loaded_routing():
    pool = build_pool()
    scheduler = PoolScheduler()

    first = scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=60.0)
    # A second task arriving immediately should go to the OTHER worker,
    # since the first worker is now busy until minute 60.
    second = scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=60.0)

    assert first.worker_id != second.worker_id
    assert second.wait_minutes == 0.0


def test_scheduler_queues_when_all_workers_are_busy():
    pool = build_pool()
    scheduler = PoolScheduler()

    scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=60.0)
    scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=60.0)
    third = scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=60.0)

    assert third.wait_minutes > 0.0


def test_scheduler_skips_unavailable_workers():
    pool = build_pool(
        workers=[
            Worker(worker_id="a", name="Agent A", available=False),
            Worker(worker_id="b", name="Agent B", available=True),
        ]
    )
    scheduler = PoolScheduler()

    outcome = scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=30.0)

    assert outcome.worker_id == "b"


def test_scheduler_raises_when_no_workers_are_available():
    pool = build_pool(
        workers=[Worker(worker_id="a", name="Agent A", available=False)]
    )
    scheduler = PoolScheduler()

    with pytest.raises(ValueError, match="available"):
        scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=30.0)


def test_scheduler_respects_worker_shift_hours():
    weekday_shift = Shift(name="Day", days=frozenset({0, 1, 2, 3, 4}), start_hour=9, end_hour=17)
    pool = build_pool(
        workers=[Worker(worker_id="a", name="Agent A", shifts=[weekday_shift])]
    )
    scheduler = PoolScheduler()

    # Day 0 (Monday) starts at minute 0; a task ready at minute 0 (midnight)
    # should be pushed to 9am (minute 540), when the shift opens.
    outcome = scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=30.0)

    assert outcome.start == 9 * 60.0


def test_scheduler_skips_non_shift_days():
    # Monday-only shift; a task ready on a Saturday (day index 5) should
    # roll forward to the next Monday.
    monday_only = Shift(name="Monday", days=frozenset({0}), start_hour=9, end_hour=17)
    pool = build_pool(workers=[Worker(worker_id="a", name="Agent A", shifts=[monday_only])])
    scheduler = PoolScheduler()

    saturday_minute = 5 * 24 * 60  # day index 5 == Saturday, epoch Monday=0
    outcome = scheduler.schedule(pool, ready_time=saturday_minute, sampled_base_duration=30.0)

    next_monday = 7 * 24 * 60 + 9 * 60
    assert outcome.start == next_monday


def test_scheduler_allows_overtime_beyond_regular_hours():
    shift = Shift(
        name="Day", days=frozenset({0, 1, 2, 3, 4}), start_hour=9, end_hour=17, overtime_hours=2.0
    )
    pool = build_pool(workers=[Worker(worker_id="a", name="Agent A", shifts=[shift])])
    scheduler = PoolScheduler()

    # Fill up all 8 regular hours (480 minutes) in one task.
    first = scheduler.schedule(pool, ready_time=9 * 60.0, sampled_base_duration=480.0)
    assert first.used_overtime is False

    # A second, short task should fit in the 2-hour overtime window rather
    # than rolling to the next day.
    second = scheduler.schedule(pool, ready_time=first.end, sampled_base_duration=60.0)

    assert second.start == first.end
    assert second.used_overtime is True


def test_scheduler_rolls_to_next_day_once_overtime_is_exhausted():
    shift = Shift(
        name="Day", days=frozenset({0, 1, 2, 3, 4}), start_hour=9, end_hour=17, overtime_hours=1.0
    )
    pool = build_pool(workers=[Worker(worker_id="a", name="Agent A", shifts=[shift])])
    scheduler = PoolScheduler()

    scheduler.schedule(pool, ready_time=9 * 60.0, sampled_base_duration=540.0)  # 9h, fills 8+1
    overflow = scheduler.schedule(pool, ready_time=9 * 60.0 + 540.0, sampled_base_duration=30.0)

    # Next day is Tuesday (day index 1), shift starts at 9am again.
    assert overflow.start == 24 * 60 + 9 * 60


def test_worker_utilization_reflects_busy_fraction():
    pool = build_pool()
    scheduler = PoolScheduler()

    scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=240.0)

    utilization = scheduler.worker_utilization(pool, "a")
    assert 0.0 <= utilization <= 1.0


def test_pool_utilization_aggregates_across_workers():
    pool = build_pool()
    scheduler = PoolScheduler()

    scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=60.0)
    scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=60.0)

    assert scheduler.pool_utilization(pool) > 0.0


def test_pool_utilization_is_zero_with_no_history():
    pool = build_pool()
    scheduler = PoolScheduler()

    assert scheduler.pool_utilization(pool) == 0.0


def test_known_worker_and_pool_ids():
    pool = build_pool()
    scheduler = PoolScheduler()
    scheduler.schedule(pool, ready_time=0.0, sampled_base_duration=30.0)

    assert scheduler.known_pool_ids() == ["support-team"]
    assert set(scheduler.known_worker_ids("support-team")).issubset({"a", "b"})
