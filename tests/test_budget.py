"""Tests for the budget module: BudgetAllocation, DepartmentBudget, OrgBudget."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.budget import (
    AI_TOOLING,
    BUDGET_CATEGORIES,
    BUDGET_CATEGORY_LABELS,
    HIRING,
    IMPLEMENTATION,
    OPERATING,
    TRAINING,
    BudgetAllocation,
    DepartmentBudget,
    OrgBudget,
)

# ---------------------------------------------------------------------------
# BudgetAllocation
# ---------------------------------------------------------------------------


def test_allocation_remaining_within_budget():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0, spent=400.0)
    assert alloc.remaining == pytest.approx(600.0)


def test_allocation_remaining_negative_when_overrun():
    alloc = BudgetAllocation(category=OPERATING, allocated=500.0, spent=600.0)
    assert alloc.remaining == pytest.approx(-100.0)


def test_allocation_utilization():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0, spent=750.0)
    assert alloc.utilization == pytest.approx(0.75)


def test_allocation_utilization_zero_allocated():
    alloc = BudgetAllocation(category=OPERATING, allocated=0.0, spent=0.0)
    assert alloc.utilization == 0.0


def test_allocation_is_overrun_false():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0, spent=999.0)
    assert not alloc.is_overrun


def test_allocation_is_overrun_true():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0, spent=1001.0)
    assert alloc.is_overrun


def test_allocation_overrun_amount_zero_when_not_overrun():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0, spent=500.0)
    assert alloc.overrun_amount == 0.0


def test_allocation_overrun_amount_positive_when_overrun():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0, spent=1200.0)
    assert alloc.overrun_amount == pytest.approx(200.0)


def test_allocation_record_spend_accumulates():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0)
    alloc.record_spend(300.0)
    alloc.record_spend(200.0)
    assert alloc.spent == pytest.approx(500.0)


def test_allocation_record_spend_negative_raises():
    alloc = BudgetAllocation(category=OPERATING, allocated=1000.0)
    with pytest.raises(ValueError, match="negative"):
        alloc.record_spend(-50.0)


# ---------------------------------------------------------------------------
# DepartmentBudget
# ---------------------------------------------------------------------------


def _make_dept_budget() -> DepartmentBudget:
    budget = DepartmentBudget(dept_id="sales", annual_budget=100_000.0)
    budget.allocate(OPERATING, 60_000.0)
    budget.allocate(HIRING, 25_000.0)
    budget.allocate(AI_TOOLING, 15_000.0)
    return budget


def test_dept_budget_total_allocated():
    budget = _make_dept_budget()
    assert budget.total_allocated == pytest.approx(100_000.0)


def test_dept_budget_allocate_negative_raises():
    budget = DepartmentBudget(dept_id="d1", annual_budget=50_000.0)
    with pytest.raises(ValueError, match="negative"):
        budget.allocate(OPERATING, -100.0)


def test_dept_budget_record_spend():
    budget = _make_dept_budget()
    budget.record_spend(OPERATING, 10_000.0)
    assert budget.total_spent == pytest.approx(10_000.0)


def test_dept_budget_record_spend_creates_allocation_if_missing():
    budget = DepartmentBudget(dept_id="d1", annual_budget=50_000.0)
    budget.record_spend(TRAINING, 500.0)
    assert budget.allocation(TRAINING) is not None
    assert budget.total_spent == pytest.approx(500.0)


def test_dept_budget_utilization():
    budget = _make_dept_budget()
    budget.record_spend(OPERATING, 50_000.0)
    assert budget.utilization == pytest.approx(0.5)


def test_dept_budget_remaining_budget():
    budget = _make_dept_budget()
    budget.record_spend(OPERATING, 20_000.0)
    assert budget.remaining_budget == pytest.approx(80_000.0)


def test_dept_budget_has_overrun_false():
    budget = _make_dept_budget()
    budget.record_spend(OPERATING, 50_000.0)
    assert not budget.has_overrun


def test_dept_budget_has_overrun_true():
    budget = DepartmentBudget(dept_id="d1", annual_budget=10_000.0)
    budget.allocate(OPERATING, 10_000.0)
    budget.record_spend(OPERATING, 12_000.0)
    assert budget.has_overrun


def test_dept_budget_overrun_amount():
    budget = DepartmentBudget(dept_id="d1", annual_budget=10_000.0)
    budget.allocate(OPERATING, 10_000.0)
    budget.record_spend(OPERATING, 11_500.0)
    assert budget.overrun_amount == pytest.approx(1_500.0)


def test_dept_budget_overrun_categories():
    budget = DepartmentBudget(dept_id="d1", annual_budget=10_000.0)
    budget.allocate(OPERATING, 5_000.0)
    budget.allocate(HIRING, 2_000.0)
    budget.record_spend(OPERATING, 6_000.0)
    overruns = budget.overrun_categories()
    assert OPERATING in overruns
    assert HIRING not in overruns


def test_dept_budget_allocations_returns_copy():
    budget = _make_dept_budget()
    allocs = budget.allocations
    allocs["fake-cat"] = None  # type: ignore[assignment]
    assert "fake-cat" not in budget.allocations


def test_dept_budget_allocation_returns_none_for_unknown():
    budget = DepartmentBudget(dept_id="d1", annual_budget=50_000.0)
    assert budget.allocation(TRAINING) is None


# ---------------------------------------------------------------------------
# OrgBudget
# ---------------------------------------------------------------------------


def _make_org_budget() -> OrgBudget:
    ob = OrgBudget(org_id="acme")
    sales_budget = DepartmentBudget(dept_id="sales", annual_budget=100_000.0)
    sales_budget.allocate(OPERATING, 80_000.0)
    sales_budget.record_spend(OPERATING, 40_000.0)
    cs_budget = DepartmentBudget(dept_id="cs", annual_budget=50_000.0)
    cs_budget.allocate(OPERATING, 50_000.0)
    cs_budget.record_spend(OPERATING, 10_000.0)
    ob.add_dept_budget(sales_budget)
    ob.add_dept_budget(cs_budget)
    return ob


def test_org_budget_total_budget():
    ob = _make_org_budget()
    assert ob.total_budget == pytest.approx(150_000.0)


def test_org_budget_total_spent():
    ob = _make_org_budget()
    assert ob.total_spent == pytest.approx(50_000.0)


def test_org_budget_total_remaining():
    ob = _make_org_budget()
    assert ob.total_remaining == pytest.approx(100_000.0)


def test_org_budget_overall_utilization():
    ob = _make_org_budget()
    assert ob.overall_utilization == pytest.approx(50_000.0 / 150_000.0)


def test_org_budget_utilization_by_dept():
    ob = _make_org_budget()
    utils = ob.utilization_by_dept()
    assert "sales" in utils
    assert "cs" in utils


def test_org_budget_no_overrun_departments():
    ob = _make_org_budget()
    assert ob.overrun_departments() == []


def test_org_budget_overrun_department_detected():
    ob = OrgBudget(org_id="acme")
    budget = DepartmentBudget(dept_id="d1", annual_budget=1_000.0)
    budget.allocate(OPERATING, 1_000.0)
    budget.record_spend(OPERATING, 1_500.0)
    ob.add_dept_budget(budget)
    assert "d1" in ob.overrun_departments()


def test_org_budget_dept_budget_returns_none_for_unknown():
    ob = OrgBudget(org_id="acme")
    assert ob.dept_budget("no-such") is None


def test_org_budget_spend_by_category():
    ob = _make_org_budget()
    spend = ob.spend_by_category()
    assert OPERATING in spend
    assert spend[OPERATING] == pytest.approx(50_000.0)


def test_org_budget_budget_pressure_score_zero_for_empty():
    ob = OrgBudget(org_id="acme")
    assert ob.budget_pressure_score() == 0.0


def test_org_budget_budget_pressure_score_increases_with_spend():
    ob = OrgBudget(org_id="acme")
    budget = DepartmentBudget(dept_id="d1", annual_budget=1_000.0)
    budget.allocate(OPERATING, 1_000.0)
    budget.record_spend(OPERATING, 900.0)
    ob.add_dept_budget(budget)
    score = ob.budget_pressure_score()
    assert 0.0 < score < 100.0


def test_budget_categories_constant():
    assert OPERATING in BUDGET_CATEGORIES
    assert IMPLEMENTATION in BUDGET_CATEGORIES
    assert AI_TOOLING in BUDGET_CATEGORIES
    assert HIRING in BUDGET_CATEGORIES
    assert TRAINING in BUDGET_CATEGORIES


def test_budget_category_labels_complete():
    for cat in BUDGET_CATEGORIES:
        assert cat in BUDGET_CATEGORY_LABELS
