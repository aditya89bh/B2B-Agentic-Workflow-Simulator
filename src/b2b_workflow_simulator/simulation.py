"""Simulation runner: executes a workflow definition over many simulated cases."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

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
    according to edge probabilities.

    A seeded `random.Random` instance is used so runs are reproducible,
    which matters for fair before/after comparisons.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def run(self, workflow: Workflow, num_cases: int) -> SimulationResult:
        """Simulate `num_cases` cases flowing through `workflow`.

        Args:
            workflow: A validated `Workflow` instance.
            num_cases: How many independent cases to simulate.

        Returns:
            A `SimulationResult` containing the full event log and the
            aggregated `KPIResult`.
        """
        if num_cases <= 0:
            raise ValueError("num_cases must be a positive integer")
        workflow.validate()

        events: list[Event] = []
        kpi = KPIResult(workflow_name=workflow.name)

        for case_index in range(num_cases):
            case_id = f"case-{case_index + 1}"
            self._run_case(workflow, case_id, events, kpi)

        kpi.total_cases = num_cases
        return SimulationResult(workflow_name=workflow.name, events=events, kpi=kpi)

    def _run_case(
        self,
        workflow: Workflow,
        case_id: str,
        events: list[Event],
        kpi: KPIResult,
    ) -> None:
        timestamp = 0.0
        current_node_id = workflow.entry_node_id
        events.append(Event(EventType.CASE_STARTED, timestamp, case_id))

        while True:
            node = workflow.get_node(current_node_id)
            actor = workflow.get_actor(node.actor_id)
            task = Task(
                task_id=f"{case_id}:{node.node_id}",
                node_id=node.node_id,
                actor_id=actor.actor_id,
                case_id=case_id,
            )
            duration = node.base_duration_minutes * actor.speed_multiplier
            cost = actor.cost_for_duration(duration)

            events.append(
                Event(EventType.TASK_STARTED, timestamp, case_id, node.node_id, actor.actor_id)
            )

            kpi.node_visit_counts[node.node_id] = kpi.node_visit_counts.get(node.node_id, 0) + 1

            if self._rng.random() < actor.error_rate:
                task.mark_failed(duration, cost, reason="actor_error")
                timestamp += duration
                self._record_task_totals(kpi, node.node_id, duration, cost)
                kpi.node_failure_counts[node.node_id] = (
                    kpi.node_failure_counts.get(node.node_id, 0) + 1
                )
                events.append(
                    Event(
                        EventType.TASK_FAILED,
                        timestamp,
                        case_id,
                        node.node_id,
                        actor.actor_id,
                        {"reason": "actor_error"},
                    )
                )
                events.append(Event(EventType.CASE_FAILED, timestamp, case_id))
                kpi.failed_cases += 1
                kpi.total_duration_minutes += timestamp
                return

            if isinstance(actor, AIAgentActor) and self._rng.random() < actor.escalation_rate:
                task.mark_escalated(duration, cost, reason="ai_escalation")
                events.append(
                    Event(
                        EventType.TASK_ESCALATED,
                        timestamp + duration,
                        case_id,
                        node.node_id,
                        actor.actor_id,
                    )
                )
            else:
                task.mark_completed(duration, cost)
                events.append(
                    Event(
                        EventType.TASK_COMPLETED,
                        timestamp + duration,
                        case_id,
                        node.node_id,
                        actor.actor_id,
                    )
                )

            timestamp += duration
            self._record_task_totals(kpi, node.node_id, duration, cost)

            if node.is_terminal:
                events.append(Event(EventType.CASE_COMPLETED, timestamp, case_id))
                kpi.completed_cases += 1
                kpi.total_duration_minutes += timestamp
                return

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


__all__ = ["SimulationRunner", "SimulationResult"]
