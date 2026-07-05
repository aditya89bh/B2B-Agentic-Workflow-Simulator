from b2b_workflow_simulator.capacity import MINUTES_PER_DAY, ActorScheduler


def test_first_task_starts_immediately_with_no_wait():
    scheduler = ActorScheduler()

    result = scheduler.schedule("rep", ready_time=10.0, duration=30.0, available_hours_per_day=8.0)

    assert result.start == 10.0
    assert result.wait_minutes == 0.0
    assert result.end == 40.0


def test_second_task_queues_behind_a_busy_actor():
    scheduler = ActorScheduler()
    scheduler.schedule("rep", ready_time=0.0, duration=30.0, available_hours_per_day=8.0)

    result = scheduler.schedule("rep", ready_time=10.0, duration=20.0, available_hours_per_day=8.0)

    assert result.start == 30.0
    assert result.wait_minutes == 20.0
    assert result.end == 50.0


def test_independent_actors_do_not_block_each_other():
    scheduler = ActorScheduler()
    scheduler.schedule("rep_a", ready_time=0.0, duration=60.0, available_hours_per_day=8.0)

    result = scheduler.schedule(
        "rep_b", ready_time=5.0, duration=10.0, available_hours_per_day=8.0
    )

    assert result.start == 5.0
    assert result.wait_minutes == 0.0


def test_task_exceeding_daily_capacity_rolls_to_next_day():
    scheduler = ActorScheduler()
    # 7 hours of work already booked today, leaving 1 hour of an 8-hour day.
    scheduler.schedule("rep", ready_time=0.0, duration=7 * 60.0, available_hours_per_day=8.0)

    result = scheduler.schedule(
        "rep", ready_time=7 * 60.0, duration=90.0, available_hours_per_day=8.0
    )

    assert result.start == MINUTES_PER_DAY
    assert result.wait_minutes > 0


def test_task_fitting_within_remaining_daily_capacity_does_not_roll_over():
    scheduler = ActorScheduler()
    scheduler.schedule("rep", ready_time=0.0, duration=7 * 60.0, available_hours_per_day=8.0)

    result = scheduler.schedule(
        "rep", ready_time=7 * 60.0, duration=30.0, available_hours_per_day=8.0
    )

    assert result.start == 7 * 60.0
    assert result.wait_minutes == 0.0


def test_utilization_reflects_busy_time_over_available_capacity():
    scheduler = ActorScheduler()
    scheduler.schedule("rep", ready_time=0.0, duration=4 * 60.0, available_hours_per_day=8.0)

    utilization = scheduler.utilization("rep", available_hours_per_day=8.0)

    assert utilization == 0.5


def test_utilization_is_zero_for_unknown_actor():
    scheduler = ActorScheduler()

    assert scheduler.utilization("nobody", available_hours_per_day=8.0) == 0.0


def test_utilization_accounts_for_multiple_active_days():
    scheduler = ActorScheduler()
    scheduler.schedule("rep", ready_time=0.0, duration=8 * 60.0, available_hours_per_day=8.0)
    # Pushes into a second day since the actor is fully booked on day one.
    scheduler.schedule("rep", ready_time=0.0, duration=4 * 60.0, available_hours_per_day=8.0)

    assert scheduler.days_active("rep") == 2
    utilization = scheduler.utilization("rep", available_hours_per_day=8.0)

    assert utilization == (8 * 60.0 + 4 * 60.0) / (8 * 60.0 * 2)


def test_busy_minutes_accumulates_across_calls():
    scheduler = ActorScheduler()
    scheduler.schedule("rep", ready_time=0.0, duration=15.0, available_hours_per_day=8.0)
    scheduler.schedule("rep", ready_time=15.0, duration=25.0, available_hours_per_day=8.0)

    assert scheduler.busy_minutes("rep") == 40.0


def test_peek_free_at_is_zero_for_unknown_actor():
    scheduler = ActorScheduler()

    assert scheduler.peek_free_at("nobody") == 0.0


def test_peek_free_at_reflects_last_scheduled_task_without_reserving():
    scheduler = ActorScheduler()
    scheduler.schedule("rep", ready_time=0.0, duration=30.0, available_hours_per_day=8.0)

    peeked = scheduler.peek_free_at("rep")

    assert peeked == 30.0
    # Peeking must not mutate state: a real schedule call still starts at 30.
    result = scheduler.schedule("rep", ready_time=0.0, duration=10.0, available_hours_per_day=8.0)
    assert result.start == 30.0


def test_known_actor_ids_lists_all_scheduled_actors():
    scheduler = ActorScheduler()
    scheduler.schedule("rep_a", ready_time=0.0, duration=10.0, available_hours_per_day=8.0)
    scheduler.schedule("rep_b", ready_time=0.0, duration=10.0, available_hours_per_day=8.0)

    assert set(scheduler.known_actor_ids()) == {"rep_a", "rep_b"}
