import csv
import io
import json

from b2b_workflow_simulator.export import (
    diff_to_csv,
    diff_to_dict,
    diff_to_json,
    events_to_json,
    kpi_to_dict,
    kpi_to_json,
)
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.primitives.event import Event, EventType
from b2b_workflow_simulator.redesign import compare_workflows


def make_before_kpi() -> KPIResult:
    return KPIResult(
        workflow_name="Before",
        total_cases=10,
        completed_cases=8,
        failed_cases=2,
        total_cost=800.0,
        total_duration_minutes=400.0,
        node_total_duration_minutes={"a": 300.0, "b": 100.0},
        actor_utilization={"rep": 0.5},
    )


def make_after_kpi() -> KPIResult:
    return KPIResult(
        workflow_name="After",
        total_cases=10,
        completed_cases=9,
        failed_cases=1,
        total_cost=300.0,
        total_duration_minutes=150.0,
        node_total_duration_minutes={"a": 100.0, "b": 50.0},
        actor_utilization={"agent": 0.3},
    )


def test_events_to_json_round_trips_core_fields():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(
            EventType.TASK_FAILED,
            10.0,
            "case-1",
            "intake",
            "sdr",
            {"reason": "actor_error"},
        ),
    ]

    payload = json.loads(events_to_json(events))

    assert payload[0]["event_type"] == "case_started"
    assert payload[0]["case_id"] == "case-1"
    assert payload[1]["event_type"] == "task_failed"
    assert payload[1]["node_id"] == "intake"
    assert payload[1]["details"] == {"reason": "actor_error"}


def test_kpi_to_dict_includes_raw_and_derived_fields():
    kpi = make_before_kpi()

    result = kpi_to_dict(kpi)

    assert result["total_cases"] == 10
    assert result["completion_rate"] == 0.8
    assert result["avg_cost_per_case"] == 80.0
    assert result["node_total_duration_minutes"] == {"a": 300.0, "b": 100.0}
    assert result["bottleneck_nodes"] == [("a", 300.0), ("b", 100.0)]


def test_kpi_to_json_is_valid_json():
    payload = json.loads(kpi_to_json(make_before_kpi()))

    assert payload["workflow_name"] == "Before"


def test_diff_to_dict_includes_metrics_and_roi():
    diff = compare_workflows(make_before_kpi(), make_after_kpi(), implementation_cost=100.0)

    result = diff_to_dict(diff)

    assert result["before_name"] == "Before"
    assert result["after_name"] == "After"
    assert len(result["metrics"]) == 7
    assert result["roi"]["implementation_cost"] == 100.0
    assert "before_bottlenecks" in result
    assert "after_utilization" in result


def test_diff_to_json_is_valid_json():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    payload = json.loads(diff_to_json(diff))

    assert payload["before_name"] == "Before"
    assert payload["metrics"][0]["label"] == "Completion rate"


def test_diff_to_csv_has_header_and_one_row_per_metric():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    csv_text = diff_to_csv(diff)
    rows = list(csv.reader(io.StringIO(csv_text)))

    assert rows[0] == ["metric", "before", "after", "delta", "percent_change"]
    assert len(rows) == 1 + len(diff.metrics)
    assert rows[1][0] == "Completion rate"


def test_diff_to_csv_leaves_percent_change_blank_when_none():
    before = make_before_kpi()
    before.total_wait_minutes = 0.0
    after = make_after_kpi()
    after.total_wait_minutes = 0.0

    diff = compare_workflows(before, after)
    csv_text = diff_to_csv(diff)
    rows = {row[0]: row for row in csv.reader(io.StringIO(csv_text))}

    assert rows["Wait time (minutes)"][4] == ""
