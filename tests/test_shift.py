import pytest

from b2b_workflow_simulator.primitives.shift import ALL_DAYS, MONDAY_TO_FRIDAY, Shift


def test_shift_defaults_to_weekday_business_hours():
    shift = Shift(name="Day shift")

    assert shift.days == MONDAY_TO_FRIDAY
    assert shift.regular_hours == 8.0
    assert shift.hours_with_overtime == 8.0


def test_shift_computes_hours_with_overtime():
    shift = Shift(name="Day shift", start_hour=9.0, end_hour=17.0, overtime_hours=2.0)

    assert shift.regular_hours == 8.0
    assert shift.hours_with_overtime == 10.0


def test_shift_is_active_on_checks_configured_days():
    weekend_shift = Shift(
        name="Weekend on-call", days=frozenset({5, 6}), start_hour=10, end_hour=14
    )

    assert weekend_shift.is_active_on(5) is True
    assert weekend_shift.is_active_on(0) is False


def test_shift_rejects_empty_name():
    with pytest.raises(ValueError, match="name"):
        Shift(name="")


def test_shift_rejects_empty_days():
    with pytest.raises(ValueError, match="days"):
        Shift(name="Day shift", days=frozenset())


def test_shift_rejects_invalid_weekday():
    with pytest.raises(ValueError, match="days"):
        Shift(name="Day shift", days=frozenset({7}))


def test_shift_rejects_start_after_end():
    with pytest.raises(ValueError, match="start_hour"):
        Shift(name="Day shift", start_hour=17.0, end_hour=9.0)


def test_shift_rejects_negative_overtime():
    with pytest.raises(ValueError, match="overtime_hours"):
        Shift(name="Day shift", overtime_hours=-1.0)


def test_all_days_contains_every_weekday():
    assert ALL_DAYS == frozenset(range(7))
