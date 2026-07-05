import pytest

from b2b_workflow_simulator.primitives.event import Event, EventType


def test_event_creates_with_required_fields():
    event = Event(
        event_type=EventType.TASK_STARTED,
        timestamp_minutes=12.0,
        case_id="case-1",
    )

    assert event.event_type == EventType.TASK_STARTED
    assert event.timestamp_minutes == 12.0
    assert event.case_id == "case-1"
    assert event.node_id == ""
    assert event.actor_id == ""
    assert event.details == {}


def test_event_accepts_optional_fields():
    event = Event(
        event_type=EventType.TASK_FAILED,
        timestamp_minutes=20.0,
        case_id="case-1",
        node_id="discovery_call",
        actor_id="ae",
        details={"reason": "actor_error"},
    )

    assert event.node_id == "discovery_call"
    assert event.actor_id == "ae"
    assert event.details == {"reason": "actor_error"}


def test_event_is_immutable():
    event = Event(event_type=EventType.CASE_STARTED, timestamp_minutes=0.0, case_id="case-1")

    with pytest.raises(AttributeError):
        event.case_id = "case-2"
