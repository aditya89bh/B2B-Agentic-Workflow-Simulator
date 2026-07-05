"""Simulation runner: executes a workflow definition over many simulated cases."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from b2b_workflow_simulator.capacity import ActorScheduler
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.event import Event, EventType
from b2b_workflow_simulator.primitives.task import Task
from b2b_workflow_simulator.workflow import Workflow


@dataclass
class SimulationResult:
    """Full output of a simulation run: the raw event log plus aggregated KPIs."""

    workflow_name: str
    events: list[Event] = field(default_factory=list)
    kpi: KPIResult = field(default_factory=lambda: KPIResult(workflow_name=""))


class SimulationRunner:
    """Executes a `Workflow` over a number of simulated cases.

    Each case (e.g. one sales lead) starts at the workflow's entry node and
    moves through the graph, node by node, until it reaches a terminal node
    (success) or a task fails (failure). At every node, the assigned
    actor's error rate and speed determine whether the task succeeds and
    how long/expensive it is. Branching nodes route cases stochastically
    according to edge probabilities, and node durations are sampled from
    each node's `DurationModel` to reflect realistic variance.

    By default, cases are treated as independent: actors are always
    immediately available, so there is no queueing. Passing
    `arrival_interval_minutes` to `run()` switches on capacity-aware
    scheduling: cases arrive at that fixed interval, actors are modeled as
    single-server queues with daily capacity limits (see `ActorScheduler`),
    and cases wait when their assigned actor is busy or out of capacity
    for the day.

    A seeded `random.Random` instance is used so runs are reproducible,
    which matters for fair before/after comparisons.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def run(
        self,
        workflow: Workflow,
        num_cases: int,
        arrival_interval_minutes: float | None = None,
    ) -> SimulationResult:
        """Simulate `num_cases` cases flowing through `workflow`.

        Args:
            workflow: A validated `Workflow` instance.
            num_cases: How many independent cases to simulate.
            arrival_interval_minutes: If provided, cases arrive this many
                minutes apart and compete for actor capacity, producing
                queueing and wait time. If omitted, actors are always
                immediately available (no capacity constraints).

        Returns:
            A `SimulationResult` containing the full event log and the
            aggregated `KPIResult`.
        """
        if num_cases <= 0:
            raise ValueError("num_cases must be a positive integer")
        if arrival_interval_minutes is not None and arrival_interval_minutes < 0:
            raise ValueError("arrival_interval_minutes cannot be negative")
        workflow.validate()

        events: list[Event] = []
        kpi = KPIResult(workflow_name=workflow.name)
        scheduler = ActorScheduler() if arrival_interval_minutes is not None else None

        for case_index in range(num_cases):
            case_id = f"case-{case_index + 1}"
            arrival_time = (
                case_index * arrival_interval_minutes if arrival_interval_minutes else 0.0
            )
            self._run_case(workflow, case_id, arrival_time, events, kpi, scheduler)

        kpi.total_cases = num_cases
        if scheduler is not None:
            self._record_actor_utilization(workflow, kpi, scheduler)

        return SimulationResult(workflow_name=workflow.name, events=events, kpi=kpi)

    def _run_case(
        self,
        workflow: Workflow,
        case_id: str,
        arrival_time: float,
        events: list[Event],
        kpi: KPIResult,
        scheduler: ActorScheduler | None,
    ) -> None:
        clock = arrival_time
        current_node_id = workflow.entry_node_id
        events.append(Event(EventType.CASE_STARTED, clock, case_id))

        while True:
            node = workflow.get_node(current_node_id)
            actor = workflow.get_actor(node.actor_id)
            task = Task(
                task_id=f"{case_id}:{node.node_id}",
                node_id=node.node_id,
                actor_id=actor.actor_id,
                case_id=case_id,
            )
            sampled_base = node.duration_model.sample(self._rng, node.base_duration_minutes)
            duration = sampled_base * actor.speed_multiplier
            cost = actor.cost_for_duration(duration)

            if scheduler is not None:
                scheduled = scheduler.schedule(
                    actor.actor_id, clock, duration, actor.available_hours_per_day
                )
                start, end, wait = scheduled.start, scheduled.end, scheduled.wait_minutes
                kpi.total_wait_minutes += wait
                kpi.actor_wait_minutes[actor.actor_id] = (
                    kpi.actor_wait_minutes.get(actor.actor_id, 0.0) + wait
                )
            else:
                start, end = clock, clock + duration

            kpi.node_visit_counts[node.node_id] = kpi.node_visit_counts.get(node.node_id, 0) + 1
            events.append(
                Event(EventType.TASK_STARTED, start, case_id, node.node_id, actor.actor_id)
            )

            if self._rng.random() < actor.error_rate:
                task.mark_failed(duration, cost, reason="actor_error")
                self._record_task_totals(kpi, node.node_id, duration, cost)
                kpi.node_failure_counts[node.node_id] = (
                    kpi.node_failure_counts.get(node.node_id, 0) + 1
                )
                events.append(
                    Event(
                        EventType.TASK_FAILED,
                        end,
                        case_id,
                        node.node_id,
                        actor.actor_id,
                        {"reason": "actor_error"},
                    )
                )
                events.append(Event(EventType.CASE_FAILED, end, case_id))
                kpi.failed_cases += 1
                kpi.total_duration_minutes += end - arrival_time
                return

            if isinstance(actor, AIAgentActor) and self._rng.random() < actor.escalation_rate:
                task.mark_escalated(duration, cost, reason="ai_escalation")
                kpi.total_escalations += 1
                events.append(
                    Event(EventType.TASK_ESCALATED, end, case_id, node.node_id, actor.actor_id)
                )
            else:
                task.mark_completed(duration, cost)
                events.append(
                    Event(EventType.TASK_COMPLETED, end, case_id, node.node_id, actor.actor_id)
                )

            self._record_task_totals(kpi, node.node_id, duration, cost)

            if node.is_terminal:
                events.append(Event(EventType.CASE_COMPLETED, end, case_id))
                kpi.completed_cases += 1
                kpi.total_duration_minutes += end - arrival_time
                return

            clock = end
            current_node_id = self._choose_next_node(workflow, node.node_id)

    def _choose_next_node(self, workflow: Workflow, node_id: str) -> str:
        edges = workflow.outgoing_edges(node_id)
        targets = [edge.target for edge in edges]
        weights = [edge.probability for edge in edges]
        return self._rng.choices(targets, weights=weights, k=1)[0]

    @staticmethod
    def _record_task_totals(kpi: KPIResult, node_id: str, duration: float, cost: float) -> None:
        kpi.total_cost += cost
        kpi.node_total_duration_minutes[node_id] = (
            kpi.node_total_duration_minutes.get(node_id, 0.0) + duration
        )

    @staticmethod
    def _record_actor_utilization(
        workflow: Workflow, kpi: KPIResult, scheduler: ActorScheduler
    ) -> None:
        for actor_id in scheduler.known_actor_ids():
            actor = workflow.get_actor(actor_id)
            kpi.actor_busy_minutes[actor_id] = scheduler.busy_minutes(actor_id)
            kpi.actor_utilization[actor_id] = scheduler.utilization(
                actor_id, actor.available_hours_per_day
            )


__all__ = ["SimulationRunner", "SimulationResult"]
