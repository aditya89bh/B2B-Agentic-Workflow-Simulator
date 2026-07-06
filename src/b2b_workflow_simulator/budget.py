"""Budget model for organizational digital twin analysis.

Each department holds a set of budget allocations across standard
categories (operating costs, implementation investment, AI tooling,
hiring, and training).  Spend is recorded at the allocation level, and
each allocation tracks utilization and overrun.  The `OrgBudget`
container aggregates all department budgets and surfaces org-level
pressure signals that feed the health score and executive report.

All amounts are treated as the same currency unit used by workflow
actor costs -- typically USD.
"""

from __future__ import annotations

from dataclasses import dataclass, field

OPERATING = "operating"
IMPLEMENTATION = "implementation"
AI_TOOLING = "ai_tooling"
HIRING = "hiring"
TRAINING = "training"

BUDGET_CATEGORIES = (OPERATING, IMPLEMENTATION, AI_TOOLING, HIRING, TRAINING)

BUDGET_CATEGORY_LABELS: dict[str, str] = {
    OPERATING: "Operating",
    IMPLEMENTATION: "Implementation",
    AI_TOOLING: "AI Tooling",
    HIRING: "Hiring",
    TRAINING: "Training",
}


@dataclass
class BudgetAllocation:
    """A single budget line item within a department's budget.

    Attributes:
        category: One of the ``BUDGET_CATEGORIES`` constants.
        allocated: The amount allocated for this category.
        spent: Running total of recorded spend against this allocation.
    """

    category: str
    allocated: float
    spent: float = 0.0

    @property
    def remaining(self) -> float:
        """Amount remaining (may be negative if overrun)."""
        return self.allocated - self.spent

    @property
    def utilization(self) -> float:
        """Fraction of allocated budget consumed (0.0 = none, 1.0 = fully used)."""
        if self.allocated == 0:
            return 0.0
        return self.spent / self.allocated

    @property
    def is_overrun(self) -> bool:
        """``True`` when spend exceeds allocation."""
        return self.spent > self.allocated

    @property
    def overrun_amount(self) -> float:
        """Amount by which spend exceeds allocation; zero when within budget."""
        return max(0.0, self.spent - self.allocated)

    def record_spend(self, amount: float) -> None:
        """Record ``amount`` of spend against this allocation.

        Args:
            amount: Non-negative spend amount.

        Raises:
            ValueError: If ``amount`` is negative.
        """
        if amount < 0:
            raise ValueError(f"spend amount cannot be negative, got {amount}")
        self.spent += amount


@dataclass
class DepartmentBudget:
    """Budget container for a single department.

    Tracks individual allocations per category plus the department's
    overall annual budget envelope.

    Attributes:
        dept_id: The department this budget belongs to.
        annual_budget: Total annual budget available to this department.
    """

    dept_id: str
    annual_budget: float
    _allocations: dict[str, BudgetAllocation] = field(default_factory=dict, repr=False)

    def allocate(self, category: str, amount: float) -> DepartmentBudget:
        """Create or replace a budget allocation and return self.

        Args:
            category: A budget category (see ``BUDGET_CATEGORIES``).
            amount: Amount to allocate.

        Raises:
            ValueError: If ``amount`` is negative.
        """
        if amount < 0:
            raise ValueError(f"allocation amount cannot be negative, got {amount}")
        self._allocations[category] = BudgetAllocation(category=category, allocated=amount)
        return self

    def record_spend(self, category: str, amount: float) -> None:
        """Record spend against a category, creating a zero allocation first if needed.

        Args:
            category: Budget category to charge.
            amount: Non-negative spend amount.
        """
        if category not in self._allocations:
            self._allocations[category] = BudgetAllocation(category=category, allocated=0.0)
        self._allocations[category].record_spend(amount)

    def allocation(self, category: str) -> BudgetAllocation | None:
        """Return the allocation for ``category``, or ``None`` if not set."""
        return self._allocations.get(category)

    @property
    def allocations(self) -> dict[str, BudgetAllocation]:
        """All allocations keyed by category."""
        return dict(self._allocations)

    @property
    def total_allocated(self) -> float:
        """Sum of all category allocations."""
        return sum(a.allocated for a in self._allocations.values())

    @property
    def total_spent(self) -> float:
        """Sum of all category spend."""
        return sum(a.spent for a in self._allocations.values())

    @property
    def remaining_budget(self) -> float:
        """Annual budget minus total spend (may be negative)."""
        return self.annual_budget - self.total_spent

    @property
    def utilization(self) -> float:
        """Fraction of the annual budget that has been spent."""
        if self.annual_budget == 0:
            return 0.0
        return self.total_spent / self.annual_budget

    @property
    def has_overrun(self) -> bool:
        """``True`` when total spend exceeds the annual budget."""
        return self.total_spent > self.annual_budget

    @property
    def overrun_amount(self) -> float:
        """Amount by which total spend exceeds annual budget; zero when in range."""
        return max(0.0, self.total_spent - self.annual_budget)

    def overrun_categories(self) -> list[str]:
        """Return category names where spend exceeds allocation."""
        return [cat for cat, alloc in self._allocations.items() if alloc.is_overrun]


@dataclass
class OrgBudget:
    """Organization-level budget aggregator.

    Holds one `DepartmentBudget` per department and provides aggregate
    views over all departments.

    Attributes:
        org_id: The organization this budget belongs to.
    """

    org_id: str
    _dept_budgets: dict[str, DepartmentBudget] = field(default_factory=dict, repr=False)

    def add_dept_budget(self, budget: DepartmentBudget) -> OrgBudget:
        """Register a department budget and return self."""
        self._dept_budgets[budget.dept_id] = budget
        return self

    def dept_budget(self, dept_id: str) -> DepartmentBudget | None:
        """Return the budget for ``dept_id``, or ``None`` if not registered."""
        return self._dept_budgets.get(dept_id)

    @property
    def dept_budgets(self) -> dict[str, DepartmentBudget]:
        """All department budgets keyed by dept_id."""
        return dict(self._dept_budgets)

    @property
    def total_budget(self) -> float:
        """Sum of all department annual budgets."""
        return sum(b.annual_budget for b in self._dept_budgets.values())

    @property
    def total_spent(self) -> float:
        """Sum of all recorded spend across all departments."""
        return sum(b.total_spent for b in self._dept_budgets.values())

    @property
    def total_remaining(self) -> float:
        """Total budget minus total spend (may be negative)."""
        return self.total_budget - self.total_spent

    @property
    def overall_utilization(self) -> float:
        """Fraction of total budget spent."""
        if self.total_budget == 0:
            return 0.0
        return self.total_spent / self.total_budget

    def utilization_by_dept(self) -> dict[str, float]:
        """Return per-department utilization fractions keyed by dept_id."""
        return {dept_id: budget.utilization for dept_id, budget in self._dept_budgets.items()}

    def overrun_departments(self) -> list[str]:
        """Return dept_ids whose spend exceeds their annual budget."""
        return [dept_id for dept_id, b in self._dept_budgets.items() if b.has_overrun]

    def spend_by_category(self) -> dict[str, float]:
        """Aggregate spend per category across all departments."""
        totals: dict[str, float] = {}
        for budget in self._dept_budgets.values():
            for cat, alloc in budget.allocations.items():
                totals[cat] = totals.get(cat, 0.0) + alloc.spent
        return totals

    def budget_pressure_score(self) -> float:
        """Return a 0-100 pressure score (higher = more pressure).

        Combines overall utilization (80 points max) with overrun penalty
        (20 points max) to produce a single budget health signal for the
        org health engine.
        """
        util_score = min(80.0, self.overall_utilization * 80.0)
        n_depts = len(self._dept_budgets)
        if n_depts == 0:
            return 0.0
        overrun_fraction = len(self.overrun_departments()) / n_depts
        overrun_score = overrun_fraction * 20.0
        return util_score + overrun_score


__all__ = [
    "AI_TOOLING",
    "BUDGET_CATEGORIES",
    "BUDGET_CATEGORY_LABELS",
    "BudgetAllocation",
    "DepartmentBudget",
    "HIRING",
    "IMPLEMENTATION",
    "OPERATING",
    "OrgBudget",
    "TRAINING",
]
