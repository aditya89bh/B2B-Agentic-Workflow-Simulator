import random

import pytest

from b2b_workflow_simulator.arrivals import MONDAY_TO_FRIDAY, ArrivalModel


def test_fixed_generates_evenly_spaced_arrivals():
    model = ArrivalModel(kind="fixed", interval_minutes=15.0)

    times = model.generate(5, random.Random(1))

    assert times == [0.0, 15.0, 30.0, 45.0, 60.0]


def test_fixed_requires_positive_interval():
    with pytest.raises(ValueError, match="interval_minutes"):
        ArrivalModel(kind="fixed", interval_minutes=0.0)


def test_uniform_generates_non_decreasing_arrivals_within_bounds():
    model = ArrivalModel(kind="uniform", min_interval_minutes=5.0, max_interval_minutes=15.0)

    times = model.generate(50, random.Random(1))

    assert times[0] == 0.0
    assert times == sorted(times)
    gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
    assert all(5.0 <= gap <= 15.0 for gap in gaps)


def test_uniform_is_deterministic_given_same_seed():
    model = ArrivalModel(kind="uniform", min_interval_minutes=5.0, max_interval_minutes=15.0)

    times_a = model.generate(20, random.Random(42))
    times_b = model.generate(20, random.Random(42))

    assert times_a == times_b


def test_uniform_rejects_min_greater_than_max():
    with pytest.raises(ValueError, match="min_interval_minutes"):
        ArrivalModel(kind="uniform", min_interval_minutes=20.0, max_interval_minutes=10.0)


def test_batched_groups_cases_at_the_same_timestamp():
    model = ArrivalModel(kind="batched", batch_size=3, batch_interval_minutes=60.0)

    times = model.generate(7, random.Random(1))

    assert times == [0.0, 0.0, 0.0, 60.0, 60.0, 60.0, 120.0]


def test_batched_rejects_zero_batch_size():
    with pytest.raises(ValueError, match="batch_size"):
        ArrivalModel(kind="batched", batch_size=0, batch_interval_minutes=60.0)


def test_business_hours_confines_arrivals_to_the_configured_window():
    model = ArrivalModel(
        kind="business_hours",
        interval_minutes=30.0,
        business_start_hour=9.0,
        business_end_hour=17.0,
        business_days=MONDAY_TO_FRIDAY,
    )

    times = model.generate(50, random.Random(1))

    for t in times:
        day_index = int(t // (24 * 60))
        time_of_day_hours = (t % (24 * 60)) / 60.0
        assert day_index % 7 in MONDAY_TO_FRIDAY
        assert 9.0 <= time_of_day_hours < 17.0


def test_business_hours_skips_weekends():
    model = ArrivalModel(
        kind="business_hours",
        interval_minutes=60.0,
        business_start_hour=9.0,
        business_end_hour=17.0,
        business_days=MONDAY_TO_FRIDAY,
    )

    # 8 arrivals/day * 5 days = 40 fit in one business week; force a rollover.
    times = model.generate(45, random.Random(1))
    days_seen = sorted({int(t // (24 * 60)) % 7 for t in times})

    assert set(days_seen).issubset(MONDAY_TO_FRIDAY)


def test_peak_hours_uses_tighter_spacing_during_the_peak_window():
    model = ArrivalModel(
        kind="peak_hours",
        interval_minutes=60.0,
        peak_interval_minutes=10.0,
        peak_start_hour=9.0,
        peak_end_hour=11.0,
    )

    times = model.generate(20, random.Random(1))
    gaps = [b - a for a, b in zip(times, times[1:], strict=False)]

    assert 10.0 in gaps
    assert 60.0 in gaps


def test_generate_rejects_non_positive_case_count():
    model = ArrivalModel(kind="fixed", interval_minutes=10.0)

    with pytest.raises(ValueError, match="num_cases"):
        model.generate(0, random.Random(1))


def test_business_hour_bounds_are_validated():
    with pytest.raises(ValueError, match="business_start_hour"):
        ArrivalModel(
            kind="business_hours",
            interval_minutes=10.0,
            business_start_hour=17.0,
            business_end_hour=9.0,
        )
