"""Export simulation artifacts (events, KPIs, redesign diffs) to JSON and CSV."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.primitives.event import Event
from b2b_workflow_simulator.redesign import MetricDelta, RedesignDiff


def _event_to_dict(event: Event) -> dict:
    return {
        "event_type": event.event_type.value,
        "timestamp_minutes": event.timestamp_minutes,
        "case_id": event.case_id,
        "node_id": event.node_id,
        "actor_id": event.actor_id,
        "details": dict(event.details),
    }


def events_to_json(events: list[Event], *, indent: int | None = 2) -> str:
    """Serialize a list of `Event` objects to a JSON array."""
    return json.dumps([_event_to_dict(event) for event in events], indent=indent)


def kpi_to_dict(kpi: KPIResult) -> dict:
    """Convert a `KPIResult` into a plain, JSON-serializable dictionary.

    Includes both the raw accumulated fields and the derived business
    metrics (completion rate, cost per case, etc.) so the exported file
    is self-contained and does not require re-deriving anything.
    """
    return {
        "workflow_name": kpi.workflow_name,
        "total_cases": kpi.total_cases,
        "completed_cases": kpi.completed_cases,
        "failed_cases": kpi.failed_cases,
        "completion_rate": kpi.completion_rate,
        "failure_rate": kpi.failure_rate,
        "total_cost": kpi.total_cost,
        "avg_cost_per_case": kpi.avg_cost_per_case,
        "total_duration_minutes": kpi.total_duration_minutes,
        "avg_cycle_time_minutes": kpi.avg_cycle_time_minutes,
        "total_wait_minutes": kpi.total_wait_minutes,
        "avg_wait_time_minutes": kpi.avg_wait_time_minutes,
        "total_escalations": kpi.total_escalations,
        "escalation_rate": kpi.escalation_rate,
        "node_visit_counts": dict(kpi.node_visit_counts),
        "node_failure_counts": dict(kpi.node_failure_counts),
        "node_total_duration_minutes": dict(kpi.node_total_duration_minutes),
        "actor_busy_minutes": dict(kpi.actor_busy_minutes),
        "actor_wait_minutes": dict(kpi.actor_wait_minutes),
        "actor_utilization": dict(kpi.actor_utilization),
        "bottleneck_nodes": kpi.bottleneck_nodes(),
    }


def kpi_to_json(kpi: KPIResult, *, indent: int | None = 2) -> str:
    """Serialize a `KPIResult` to a JSON object."""
    return json.dumps(kpi_to_dict(kpi), indent=indent)


def _metric_delta_to_dict(metric: MetricDelta) -> dict:
    return {
        "label": metric.label,
        "before": metric.before,
        "after": metric.after,
        "delta": metric.delta,
        "percent_change": metric.percent_change,
    }


def diff_to_dict(diff: RedesignDiff) -> dict:
    """Convert a `RedesignDiff` into a plain, JSON-serializable dictionary."""
    return {
        "before_name": diff.before_name,
        "after_name": diff.after_name,
        "metrics": [_metric_delta_to_dict(metric) for metric in diff.metrics],
        "roi": asdict(diff.roi),
        "before_bottlenecks": diff.before_bottlenecks,
        "after_bottlenecks": diff.after_bottlenecks,
        "before_utilization": diff.before_utilization,
        "after_utilization": diff.after_utilization,
    }


def diff_to_json(diff: RedesignDiff, *, indent: int | None = 2) -> str:
    """Serialize a `RedesignDiff` to a JSON object."""
    return json.dumps(diff_to_dict(diff), indent=indent)


def diff_to_csv(diff: RedesignDiff) -> str:
    """Serialize a `RedesignDiff`'s headline metrics to a CSV string.

    One row per metric, with before/after/delta/percent_change columns.
    This is intentionally limited to the headline metrics (not bottlenecks
    or utilization) to keep the format simple and spreadsheet-friendly.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "before", "after", "delta", "percent_change"])
    for metric in diff.metrics:
        percent_change = "" if metric.percent_change is None else metric.percent_change
        writer.writerow([metric.label, metric.before, metric.after, metric.delta, percent_change])
    return buffer.getvalue()


__all__ = [
    "events_to_json",
    "kpi_to_dict",
    "kpi_to_json",
    "diff_to_dict",
    "diff_to_json",
    "diff_to_csv",
]
