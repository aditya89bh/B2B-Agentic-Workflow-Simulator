"""Cross-workflow simulation: run multiple workflows against one organization.

Individual workflow simulations model one process at a time.
`CrossWorkflowSimulator` runs a configurable set of workflows that all
share the same organization and optionally a shared resource pool.

Key design decisions:

- Each workflow gets its own ``SimulationRunner`` (and therefore its own
  random stream) so results are individually reproducible.
- When a ``SharedResourcePool`` is supplied to ``CrossWorkflowSimulator``,
  each workflow's KPI actor busy-minutes are mapped to resource demand via
  the ``actor_ids`` field on each ``SharedResource``.  Usage is recorded
  via :meth:`~b2b_workflow_simulator.shared_resources.SharedResourcePool.record_usage_from_kpi`
  after each workflow run; contention ratios are then available on the pool.
- The ``CrossWorkflowResult`` exposes per-workflow ``SimulationResult``
  objects so all existing Phase 1-5 analysis functions work unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.org_model import Organization
from b2b_workflow_simulator.shared_resources import SharedResourcePool
from b2b_workflow_simulator.simulation import ENGINES, SimulationResult, SimulationRunner
from b2b_workflow_simulator.workflow import Workflow


def _actor_busy_minutes(workflow: Workflow, kpi: KPIResult) -> dict[str, float]:
    """Return per-actor busy minutes, falling back to node total durations.

    When the simulation ran without capacity-aware scheduling (no arrival
    interval), ``kpi.actor_busy_minutes`` is empty.  In that case, actor
    busy time is approximated by summing ``node_total_duration_minutes``
    across all nodes assigned to each actor.
    """
    if kpi.actor_busy_minutes:
        return kpi.actor_busy_minutes
    actor_minutes: dict[str, float] = {}
    for node_id, node in workflow.nodes.items():
        duration = kpi.node_total_duration_minutes.get(node_id, 0.0)
        actor_minutes[node.actor_id] = actor_minutes.get(node.actor_id, 0.0) + duration
    return actor_minutes


@dataclass
class WorkflowRunConfig:
    """Configuration for one workflow inside a cross-workflow run.

    Attributes:
        workflow: The validated workflow to simulate.
        num_cases: Number of cases to simulate.
        arrival_interval_minutes: Optional arrival interval; enables
            capacity-aware scheduling within this workflow.
        engine: ``"simple"`` or ``"discrete"`` (see
            :class:`~b2b_workflow_simulator.simulation.SimulationRunner`).
        dept_id: Optional department that owns this workflow; used when
            recording shared resource usage.
        seed: Optional random seed, independent of the org-level seed.
    """

    workflow: Workflow
    num_cases: int
    arrival_interval_minutes: float | None = None
    engine: str = "simple"
    dept_id: str | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.num_cases <= 0:
            raise ValueError("num_cases must be a positive integer")
        if self.engine not in ENGINES:
            raise ValueError(f"engine must be one of {ENGINES}, got {self.engine!r}")


@dataclass
class CrossWorkflowResult:
    """Combined output of a cross-workflow simulation run.

    Attributes:
        org_id: The organization the run was performed for.
        org_name: Human-readable organization name.
        results: Per-workflow ``SimulationResult`` objects keyed by
            ``workflow.workflow_id``.
    """

    org_id: str
    org_name: str
    results: dict[str, SimulationResult] = field(default_factory=dict)

    @property
    def workflow_ids(self) -> list[str]:
        """Workflow IDs included in this run."""
        return list(self.results)

    @property
    def total_cost(self) -> float:
        """Sum of ``kpi.total_cost`` across all workflows."""
        return sum(r.kpi.total_cost for r in self.results.values())

    @property
    def total_cases(self) -> int:
        """Sum of ``kpi.total_cases`` across all workflows."""
        return sum(r.kpi.total_cases for r in self.results.values())

    @property
    def total_completed(self) -> int:
        """Sum of ``kpi.completed_cases`` across all workflows."""
        return sum(r.kpi.completed_cases for r in self.results.values())

    @property
    def avg_completion_rate(self) -> float:
        """Macro-average completion rate across all workflows.

        Returns 0.0 if no workflows were run.
        """
        if not self.results:
            return 0.0
        return sum(r.kpi.completion_rate for r in self.results.values()) / len(self.results)

    @property
    def avg_cost_per_case(self) -> float:
        """Total cost divided by total cases."""
        if self.total_cases == 0:
            return 0.0
        return self.total_cost / self.total_cases

    def kpi_for(self, workflow_id: str) -> KPIResult:
        """Return the ``KPIResult`` for ``workflow_id``.

        Raises:
            KeyError: If the workflow was not part of this run.
        """
        return self.results[workflow_id].kpi

    def workflow_names(self) -> list[str]:
        """Return the human-readable names of all simulated workflows."""
        return [r.workflow_name for r in self.results.values()]


class CrossWorkflowSimulator:
    """Simulate multiple workflows that share one organizational context.

    Build the simulator, add workflow configurations, then call
    :meth:`run` to execute all workflows and receive a
    :class:`CrossWorkflowResult`.

    Example::

        sim = CrossWorkflowSimulator(org, seed=42)
        sim.add_workflow(WorkflowRunConfig(sales_wf, num_cases=200))
        sim.add_workflow(WorkflowRunConfig(invoice_wf, num_cases=150))
        result = sim.run()
    """

    def __init__(
        self,
        organization: Organization,
        seed: int | None = None,
        shared_resource_pool: SharedResourcePool | None = None,
    ) -> None:
        """
        Args:
            organization: The organizational context for the run.
            seed: Optional base seed.  When a ``WorkflowRunConfig`` does
                not specify its own seed, the simulator uses
                ``seed + index`` so each workflow still gets a distinct
                but reproducible random stream.
            shared_resource_pool: Optional pool of shared resources.  When
                provided, each workflow's KPI actor busy-minutes are mapped
                to resource demand via ``SharedResource.actor_ids`` and
                recorded into the pool after each simulation run.  Contention
                ratios are then available on the pool immediately after
                :meth:`run` returns.
        """
        self._org = organization
        self._seed = seed
        self._pool = shared_resource_pool
        self._configs: list[WorkflowRunConfig] = []

    def add_workflow(self, config: WorkflowRunConfig) -> CrossWorkflowSimulator:
        """Add a workflow to simulate and return self for chaining."""
        self._configs.append(config)
        return self

    def run(self) -> CrossWorkflowResult:
        """Execute all configured workflows and return the combined result.

        Each workflow is simulated independently.  When a
        ``shared_resource_pool`` was supplied at construction, actor busy
        minutes from each run's KPI are mapped to shared resources via
        :meth:`~b2b_workflow_simulator.shared_resources.SharedResourcePool.record_usage_from_kpi`.

        Returns:
            A :class:`CrossWorkflowResult` with one entry per workflow.
        """
        combined = CrossWorkflowResult(
            org_id=self._org.org_id,
            org_name=self._org.name,
        )
        for index, config in enumerate(self._configs):
            effective_seed = (
                config.seed
                if config.seed is not None
                else (self._seed + index if self._seed is not None else None)
            )
            runner = SimulationRunner(seed=effective_seed)
            result = runner.run(
                config.workflow,
                config.num_cases,
                arrival_interval_minutes=config.arrival_interval_minutes,
                engine=config.engine,
            )
            combined.results[config.workflow.workflow_id] = result
            if self._pool is not None:
                dept_id = config.dept_id or config.workflow.workflow_id
                self._pool.record_usage_from_kpi(
                    config.workflow.workflow_id,
                    dept_id,
                    _actor_busy_minutes(config.workflow, result.kpi),
                )
        return combined

    @property
    def organization(self) -> Organization:
        """The organization this simulator runs against."""
        return self._org

    @property
    def shared_resource_pool(self) -> SharedResourcePool | None:
        """The shared resource pool this simulator records usage into, or ``None``."""
        return self._pool

    @property
    def workflow_count(self) -> int:
        """Number of workflows configured."""
        return len(self._configs)


__all__ = [
    "CrossWorkflowResult",
    "CrossWorkflowSimulator",
    "WorkflowRunConfig",
]
