"""SLA engine: service-level commitments checked against a simulation's event log.

Policies and compliance requirements are checked against a workflow's
*structure*. SLAs are different: they are checked against what actually
happened during a simulation run, because "did we respond in time?" is a
question about timing, not shape. This module defines three kinds of SLA
(completion, response, escalation), replays a `SimulationResult`'s event
log per case to see whether each one was met, and reports attainment,
breach counts, average breach duration, breach causes, and an optional
estimated financial penalty.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.primitives.event import Event, EventType
from b2b_workflow_simulator.simulation import SimulationResult


@dataclass(frozen=True)
class CompletionSLA:
    """The whole case must complete (successfully or not) within `deadline_minutes`."""

    name: str
    deadline_minutes: float
    penalty_per_minute: float | None = None
    description: str = ""


@dataclass(frozen=True)
class ResponseSLA:
    """The first execution of `node_id` must start within `deadline_minutes` of arrival."""

    name: str
    node_id: str
    deadline_minutes: float
    penalty_per_minute: float | None = None
    description: str = ""


@dataclass(frozen=True)
class EscalationSLA:
    """An escalation raised at `node_id` must be picked up within `deadline_minutes`."""

    name: str
    node_id: str
    deadline_minutes: float
    penalty_per_minute: float | None = None
    description: str = ""


SLA = CompletionSLA | ResponseSLA | EscalationSLA


@dataclass(frozen=True)
class SLABreach:
    """One case that missed one SLA rule."""

    rule_name: str
    rule_kind: str
    case_id: str
    node_id: str | None
    actual_minutes: float
    deadline_minutes: float
    breach_minutes: float
    penalty: float | None


@dataclass
class SLAReport:
    """The result of checking every SLA rule against every case in a simulation run."""

    workflow_name: str
    rules_checked: int
    cases_evaluated: int
    evaluations: int = 0
    breaches: list[SLABreach] = field(default_factory=list)

    @property
    def breach_count(self) -> int:
        return len(self.breaches)

    @property
    def attainment_rate(self) -> float:
        """Fraction of applicable (rule, case) checks that met their deadline."""
        if self.evaluations == 0:
            return 1.0
        return (self.evaluations - len(self.breaches)) / self.evaluations

    @property
    def average_breach_minutes(self) -> float:
        if not self.breaches:
            return 0.0
        return sum(breach.breach_minutes for breach in self.breaches) / len(self.breaches)

    @property
    def total_penalty(self) -> float:
        return sum(breach.penalty for breach in self.breaches if breach.penalty is not None)

    def breach_causes(self) -> dict[str, int]:
        """Number of breaches attributed to each SLA rule, by rule name."""
        counts: dict[str, int] = {}
        for breach in self.breaches:
            counts[breach.rule_name] = counts.get(breach.rule_name, 0) + 1
        return counts


def _group_events_by_case(events: list[Event]) -> dict[str, list[Event]]:
    grouped: dict[str, list[Event]] = {}
    for event in events:
        grouped.setdefault(event.case_id, []).append(event)
    for case_events in grouped.values():
        case_events.sort(key=lambda event: event.timestamp_minutes)
    return grouped


def _breach_or_none(
    rule_name: str,
    rule_kind: str,
    case_id: str,
    node_id: str | None,
    actual_minutes: float,
    deadline_minutes: float,
    penalty_per_minute: float | None,
) -> SLABreach | None:
    if actual_minutes <= deadline_minutes:
        return None
    breach_minutes = actual_minutes - deadline_minutes
    penalty = breach_minutes * penalty_per_minute if penalty_per_minute is not None else None
    return SLABreach(
        rule_name, rule_kind, case_id, node_id, actual_minutes, deadline_minutes,
        breach_minutes, penalty,
    )


def _check_completion_sla(
    case_id: str, case_events: list[Event], rule: CompletionSLA
) -> tuple[bool, SLABreach | None]:
    arrival = next(
        (e.timestamp_minutes for e in case_events if e.event_type == EventType.CASE_STARTED), None
    )
    terminal = next(
        (
            e.timestamp_minutes
            for e in case_events
            if e.event_type in (EventType.CASE_COMPLETED, EventType.CASE_FAILED)
        ),
        None,
    )
    if arrival is None or terminal is None:
        return False, None
    breach = _breach_or_none(
        rule.name, "completion", case_id, None, terminal - arrival, rule.deadline_minutes,
        rule.penalty_per_minute,
    )
    return True, breach


def _check_response_sla(
    case_id: str, case_events: list[Event], rule: ResponseSLA
) -> tuple[bool, SLABreach | None]:
    arrival = next(
        (e.timestamp_minutes for e in case_events if e.event_type == EventType.CASE_STARTED), None
    )
    task_start = next(
        (
            e.timestamp_minutes
            for e in case_events
            if e.event_type == EventType.TASK_STARTED and e.node_id == rule.node_id
        ),
        None,
    )
    if arrival is None or task_start is None:
        return False, None
    breach = _breach_or_none(
        rule.name, "response", case_id, rule.node_id, task_start - arrival, rule.deadline_minutes,
        rule.penalty_per_minute,
    )
    return True, breach


def _check_escalation_sla(
    case_id: str, case_events: list[Event], rule: EscalationSLA
) -> tuple[bool, SLABreach | None]:
    escalations = [
        e
        for e in case_events
        if e.event_type == EventType.TASK_ESCALATED and e.node_id == rule.node_id
    ]
    if not escalations:
        return False, None
    escalation_time = escalations[0].timestamp_minutes
    resolution_events = [
        e
        for e in case_events
        if e.timestamp_minutes > escalation_time
        and e.event_type
        in (EventType.TASK_STARTED, EventType.CASE_COMPLETED, EventType.CASE_FAILED)
    ]
    if not resolution_events:
        return False, None
    resolution_time = resolution_events[0].timestamp_minutes
    breach = _breach_or_none(
        rule.name,
        "escalation",
        case_id,
        rule.node_id,
        resolution_time - escalation_time,
        rule.deadline_minutes,
        rule.penalty_per_minute,
    )
    return True, breach


_CHECKERS = {
    CompletionSLA: _check_completion_sla,
    ResponseSLA: _check_response_sla,
    EscalationSLA: _check_escalation_sla,
}


def evaluate_sla(result: SimulationResult, slas: list[SLA]) -> SLAReport:
    """Replay `result.events` per case and check every SLA rule in `slas`."""
    cases = _group_events_by_case(result.events)
    breaches: list[SLABreach] = []
    evaluations = 0
    for rule in slas:
        checker = _CHECKERS[type(rule)]
        for case_id, case_events in cases.items():
            applicable, breach = checker(case_id, case_events, rule)
            if not applicable:
                continue
            evaluations += 1
            if breach is not None:
                breaches.append(breach)
    return SLAReport(
        workflow_name=result.workflow_name,
        rules_checked=len(slas),
        cases_evaluated=len(cases),
        evaluations=evaluations,
        breaches=breaches,
    )


__all__ = [
    "CompletionSLA",
    "ResponseSLA",
    "EscalationSLA",
    "SLA",
    "SLABreach",
    "SLAReport",
    "evaluate_sla",
]
