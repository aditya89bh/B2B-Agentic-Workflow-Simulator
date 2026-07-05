"""Workflow portfolio model: aggregate redesign value across multiple workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.redesign import RedesignDiff, compare_workflows

RANK_BY_OPTIONS = ("total_cost_savings", "roi_percentage", "cost_savings_per_case")


@dataclass
class PortfolioEntry:
    """One workflow's before/after comparison within a portfolio.

    Attributes:
        name: Short, human-readable identifier for this workflow (e.g.
            "sales-lead-qualification"). Used for ranking and reporting.
        before_kpi: The raw "before" simulation result, kept alongside the
            diff so totals (e.g. total wait minutes) can be aggregated
            without re-deriving them from per-case averages.
        after_kpi: The raw "after" simulation result.
        diff: The `RedesignDiff` produced by comparing `before_kpi` and
            `after_kpi`.
    """

    name: str
    before_kpi: KPIResult
    after_kpi: KPIResult
    diff: RedesignDiff

    def rank_value(self, by: str) -> float:
        """Return the numeric value used to rank this entry by `by`."""
        if by == "total_cost_savings":
            return self.diff.roi.total_cost_savings
        if by == "roi_percentage":
            return self.diff.roi.roi_percentage or 0.0
        if by == "cost_savings_per_case":
            return self.diff.roi.cost_savings_per_case
        raise ValueError(f"Unknown ranking metric: {by!r}. Expected one of {RANK_BY_OPTIONS}")


@dataclass
class PortfolioSummary:
    """Aggregate metrics across every workflow in a portfolio.

    Cost figures are summed directly across workflows on the assumption
    that each workflow's simulated case volume represents a comparable
    period of activity (for example, a typical month of leads, invoices,
    and support tickets). Under that assumption, `payback_in_periods` is
    a payback period expressed in that same unit of time.

    Attributes:
        workflow_count: Number of workflows included in the portfolio.
        total_before_cost: Sum of "before" total cost across all workflows.
        total_after_cost: Sum of "after" total cost across all workflows.
        total_cost_savings: `total_before_cost - total_after_cost`.
        portfolio_roi_percentage: Aggregate savings as a percentage of
            aggregate "before" cost, or None if that cost was zero.
        total_wait_minutes_saved: Sum of (before - after) total wait time
            across all workflows. Zero for workflows run without capacity
            constraints.
        total_implementation_cost: Sum of implementation costs supplied
            for workflows in the portfolio (workflows without a supplied
            cost contribute zero).
        payback_in_periods: `total_implementation_cost / total_cost_savings`,
            interpreted as a payback period in the same unit as the
            simulated case volume (e.g. months), or None if no
            implementation cost was supplied anywhere in the portfolio.
        payback_feasible: Whether the portfolio produces enough aggregate
            savings to eventually recover its total implementation cost.
    """

    workflow_count: int
    total_before_cost: float
    total_after_cost: float
    total_cost_savings: float
    portfolio_roi_percentage: float | None
    total_wait_minutes_saved: float
    total_implementation_cost: float
    payback_in_periods: float | None
    payback_feasible: bool


@dataclass
class WorkflowPortfolio:
    """A collection of before/after workflow comparisons evaluated together.

    A portfolio answers a different question than a single redesign diff:
    not "should we do this one redesign?" but "across everything we could
    redesign, where should we start?" Entries are added from already-run
    simulations (via `add_entry`), keeping this module decoupled from the
    simulation engine itself.
    """

    name: str
    entries: list[PortfolioEntry] = field(default_factory=list)

    def add_entry(
        self,
        name: str,
        before_kpi: KPIResult,
        after_kpi: KPIResult,
        implementation_cost: float | None = None,
    ) -> WorkflowPortfolio:
        """Compare `before_kpi` and `after_kpi` and add the result to the portfolio."""
        diff = compare_workflows(before_kpi, after_kpi, implementation_cost)
        self.entries.append(
            PortfolioEntry(name=name, before_kpi=before_kpi, after_kpi=after_kpi, diff=diff)
        )
        return self

    def ranked(self, by: str = "total_cost_savings") -> list[PortfolioEntry]:
        """Return entries sorted by `by`, highest value first."""
        return sorted(self.entries, key=lambda entry: entry.rank_value(by), reverse=True)

    def summary(self) -> PortfolioSummary:
        """Aggregate every entry in the portfolio into a `PortfolioSummary`."""
        total_before_cost = sum(entry.diff.total_cost.before for entry in self.entries)
        total_after_cost = sum(entry.diff.total_cost.after for entry in self.entries)
        total_cost_savings = total_before_cost - total_after_cost
        portfolio_roi_percentage = (
            (total_cost_savings / total_before_cost) * 100.0 if total_before_cost > 0 else None
        )
        total_wait_minutes_saved = sum(
            entry.before_kpi.total_wait_minutes - entry.after_kpi.total_wait_minutes
            for entry in self.entries
        )
        total_implementation_cost = sum(
            entry.diff.roi.implementation_cost or 0.0 for entry in self.entries
        )

        payback_in_periods: float | None = None
        payback_feasible = False
        if total_implementation_cost > 0 and total_cost_savings > 0:
            payback_in_periods = total_implementation_cost / total_cost_savings
            payback_feasible = True

        return PortfolioSummary(
            workflow_count=len(self.entries),
            total_before_cost=total_before_cost,
            total_after_cost=total_after_cost,
            total_cost_savings=total_cost_savings,
            portfolio_roi_percentage=portfolio_roi_percentage,
            total_wait_minutes_saved=total_wait_minutes_saved,
            total_implementation_cost=total_implementation_cost,
            payback_in_periods=payback_in_periods,
            payback_feasible=payback_feasible,
        )


__all__ = ["PortfolioEntry", "PortfolioSummary", "WorkflowPortfolio", "RANK_BY_OPTIONS"]
