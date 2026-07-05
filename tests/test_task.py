from b2b_workflow_simulator.primitives.task import Task, TaskStatus


def make_task() -> Task:
    return Task(task_id="case-1:intake", node_id="intake", actor_id="sdr", case_id="case-1")


def test_task_starts_pending():
    task = make_task()

    assert task.status == TaskStatus.PENDING
    assert task.duration_minutes == 0.0
    assert task.cost == 0.0


def test_task_mark_completed_sets_status_and_actuals():
    task = make_task()

    task.mark_completed(duration_minutes=12.5, cost=7.25)

    assert task.status == TaskStatus.COMPLETED
    assert task.duration_minutes == 12.5
    assert task.cost == 7.25


def test_task_mark_failed_records_reason():
    task = make_task()

    task.mark_failed(duration_minutes=5.0, cost=2.0, reason="missing_data")

    assert task.status == TaskStatus.FAILED
    assert task.metadata["failure_reason"] == "missing_data"


def test_task_mark_failed_without_reason_leaves_metadata_empty():
    task = make_task()

    task.mark_failed(duration_minutes=5.0, cost=2.0)

    assert "failure_reason" not in task.metadata


def test_task_mark_escalated_records_reason():
    task = make_task()

    task.mark_escalated(duration_minutes=3.0, cost=0.5, reason="low_confidence")

    assert task.status == TaskStatus.ESCALATED
    assert task.metadata["escalation_reason"] == "low_confidence"
