import pytest

from b2b_workflow_simulator.primitives.shift import Shift
from b2b_workflow_simulator.primitives.worker import Worker


def test_worker_computes_cost_for_duration():
    worker = Worker(worker_id="w1", name="Priya", hourly_cost=60.0)

    assert worker.cost_for_duration(30.0) == pytest.approx(30.0)


def test_worker_rejects_empty_worker_id():
    with pytest.raises(ValueError, match="worker_id"):
        Worker(worker_id="", name="Priya")


def test_worker_rejects_negative_hourly_cost():
    with pytest.raises(ValueError, match="hourly_cost"):
        Worker(worker_id="w1", name="Priya", hourly_cost=-5.0)


def test_worker_rejects_invalid_error_rate():
    with pytest.raises(ValueError, match="error_rate"):
        Worker(worker_id="w1", name="Priya", error_rate=1.5)


def test_worker_with_no_shifts_is_always_scheduled():
    worker = Worker(worker_id="w1", name="Priya")

    assert worker.is_scheduled_on(0) is True
    assert worker.is_scheduled_on(6) is True


def test_worker_with_shifts_only_scheduled_on_matching_days():
    worker = Worker(
        worker_id="w1",
        name="Priya",
        shifts=[Shift(name="Weekday", days=frozenset({0, 1, 2, 3, 4}))],
    )

    assert worker.is_scheduled_on(2) is True
    assert worker.is_scheduled_on(5) is False


def test_worker_defaults_to_available():
    worker = Worker(worker_id="w1", name="Priya")

    assert worker.available is True
