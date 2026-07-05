"""KPI result object: the aggregated output of a simulation run."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KPIResult:
    """Aggregated key performance indicators for a completed simulation run.

    This is the primary artifact used to compare "before" and "after"
    workflow variants: run the simulator on both, then diff the
    `KPIResult` objects to talk about ROI, throughput, and failure impact
    in business terms rather than raw event logs.

    Attributes:
        workflow_name: Name of the workflow this result was computed for.
        total_cases: Number of cases (e.g. leads) simulated.
        completed_cases: Number of cases that reached a terminal node successfully.
        failed_cases: Number of cases that ended in failure.
        total_cost: Sum of cost across all tasks in all cases.
        total_duration_minutes: Sum of wall-clock duration across all cases.
        node_visit_counts: Number of times each node was executed, keyed by node_id.
        node_failure_counts: Number of failures observed at each node, keyed by node_id.
        node_total_duration_minutes: Total minutes spent at each node, keyed by node_id.
        total_wait_minutes: Sum of time cases spent queued for a busy or
            over-capacity actor, across all cases. Zero when the run was not
            capacity-aware (see `SimulationRunner`).
        total_escalations: Number of AI agent tasks that were escalated to
            a human rather than completed autonomously.
        actor_busy_minutes: Total execution time consumed by each actor,
            keyed by actor_id.
        actor_wait_minutes: Total time cases spent waiting for each actor,
            keyed by actor_id.
        actor_utilization: Fraction (0.0-1.0+) of each actor's available
            capacity that was consumed, keyed by actor_id.
        pool_utilization: Fraction (0.0-1.0+) of each `ActorPool`'s
            aggregate worker capacity that was consumed, keyed by
            pool actor_id. Populated whenever a node routes work through
            an `ActorPool` rather than a single actor.
        worker_utilization: Per-worker utilization within each pool,
            keyed first by pool actor_id and then by worker_id.
    """

    workflow_name: str
    total_cases: int = 0
    completed_cases: int = 0
    failed_cases: int = 0
    total_cost: float = 0.0
    total_duration_minutes: float = 0.0
    total_wait_minutes: float = 0.0
    total_escalations: int = 0
    node_visit_counts: dict[str, int] = field(default_factory=dict)
    node_failure_counts: dict[str, int] = field(default_factory=dict)
    node_total_duration_minutes: dict[str, float] = field(default_factory=dict)
    actor_busy_minutes: dict[str, float] = field(default_factory=dict)
    actor_wait_minutes: dict[str, float] = field(default_factory=dict)
    actor_utilization: dict[str, float] = field(default_factory=dict)
    pool_utilization: dict[str, float] = field(default_factory=dict)
    worker_utilization: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def completion_rate(self) -> float:
        """Fraction of cases that completed successfully."""
        if self.total_cases == 0:
            return 0.0
        return self.completed_cases / self.total_cases

    @property
    def failure_rate(self) -> float:
        """Fraction of cases that ended in failure."""
        if self.total_cases == 0:
            return 0.0
        return self.failed_cases / self.total_cases

    @property
    def avg_cost_per_case(self) -> float:
        """Average total cost per case, across all cases."""
        if self.total_cases == 0:
            return 0.0
        return self.total_cost / self.total_cases

    @property
    def avg_cycle_time_minutes(self) -> float:
        """Average end-to-end duration per case, across all cases."""
        if self.total_cases == 0:
            return 0.0
        return self.total_duration_minutes / self.total_cases

    @property
    def avg_wait_time_minutes(self) -> float:
        """Average time per case spent queued for a busy or over-capacity actor."""
        if self.total_cases == 0:
            return 0.0
        return self.total_wait_minutes / self.total_cases

    @property
    def escalation_rate(self) -> float:
        """Fraction of cases that included at least one AI-to-human escalation."""
        if self.total_cases == 0:
            return 0.0
        return self.total_escalations / self.total_cases

    def bottleneck_nodes(self, top_n: int = 3) -> list[tuple[str, float]]:
        """Return the `top_n` nodes with the highest total time spent.

        This is a simple heuristic for surfacing likely bottlenecks: nodes
        that consume the most aggregate duration across all cases are the
        best candidates for redesign or automation.
        """
        ranked = sorted(
            self.node_total_duration_minutes.items(), key=lambda item: item[1], reverse=True
        )
        return ranked[:top_n]
