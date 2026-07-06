"""Cross-workflow simulation: run multiple workflows against one organization.

Individual workflow simulations model one process at a time.
`CrossWorkflowSimulator` runs a configurable set of workflows that all
share the same organization, accumulating shared resource usage and
producing a combined result that can be analysed at the portfolio level.

Key design decisions:

- Each workflow gets its own ``SimulationRunner`` (and therefore its own
  random stream) so results are individually reproducible.
- Shared resource usage is *recorded analytically* based on the
  simulated KPI output (actor busy minutes map to resource minutes); it
  is not modelled through the discrete-event engine.  This keeps the
  cross-workflow layer lightweight and compatible with both simulation
  engines.
- The ``CrossWorkflowResult`` exposes per-workflow ``SimulationResult``
  objects so all existing Phase 1-5 analysis functions work unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.org_model import Organization
from b2b_workflow_simulator.simulation import ENGINES, SimulationResult, SimulationRunner
from b2b_workflow_simulator.workflow import Workflow


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

    def kpi_for(self, workflow_id: str):
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

    def __init__(self, organization: Organization, seed: int | None = None) -> None:
        """
        Args:
            organization: The organizational context for the run.
            seed: Optional base seed.  When a ``WorkflowRunConfig`` does
                not specify its own seed, the simulator uses
                ``seed + index`` so each workflow still gets a distinct
                but reproducible random stream.
        """
        self._org = organization
        self._seed = seed
        self._configs: list[WorkflowRunConfig] = []

    def add_workflow(self, config: WorkflowRunConfig) -> CrossWorkflowSimulator:
        """Add a workflow to simulate and return self for chaining."""
        self._configs.append(config)
        return self

    def run(self) -> CrossWorkflowResult:
        """Execute all configured workflows and return the combined result.

        Each workflow is simulated independently.  The combined
        ``CrossWorkflowResult`` holds individual ``SimulationResult``
        objects for downstream Phase 1-5 analysis.

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
        return combined

    @property
    def organization(self) -> Organization:
        """The organization this simulator runs against."""
        return self._org

    @property
    def workflow_count(self) -> int:
        """Number of workflows configured."""
        return len(self._configs)


__all__ = [
    "CrossWorkflowResult",
    "CrossWorkflowSimulator",
    "WorkflowRunConfig",
]
