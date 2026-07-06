"""Tests for the collect_events parameter on SimulationRunner and DiscreteEventEngine."""

from __future__ import annotations

import sys

import pytest

from b2b_workflow_simulator.examples import (
    customer_support_ticket_resolution,
    invoice_processing,
    sales_lead_qualification,
)
from b2b_workflow_simulator.simulation import SimulationRunner


def _slq_before():
    return sales_lead_qualification.build_before_workflow()


def _inv_before():
    return invoice_processing.build_before_workflow()


# ---------------------------------------------------------------------------
# KPI parity: same results whether or not events are collected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wf_fn,num_cases,seed", [
    (_slq_before, 500, 42),
    (_inv_before, 300, 7),
])
def test_kpi_parity_simple_engine(wf_fn, num_cases, seed):
    wf = wf_fn()
    r_with = SimulationRunner(seed=seed).run(wf, num_cases, collect_events=True)
    r_without = SimulationRunner(seed=seed).run(wf, num_cases, collect_events=False)
    assert r_with.kpi.completed_cases == r_without.kpi.completed_cases
    assert r_with.kpi.failed_cases == r_without.kpi.failed_cases
    assert r_with.kpi.total_cost == pytest.approx(r_without.kpi.total_cost)
    assert r_with.kpi.total_duration_minutes == pytest.approx(r_without.kpi.total_duration_minutes)
    assert r_with.kpi.total_escalations == r_without.kpi.total_escalations
    assert r_with.kpi.node_visit_counts == r_without.kpi.node_visit_counts
    assert r_with.kpi.node_failure_counts == r_without.kpi.node_failure_counts


def test_kpi_parity_with_arrival_interval():
    wf = _slq_before()
    r_with = SimulationRunner(seed=1).run(
        wf, 200, arrival_interval_minutes=5.0, collect_events=True
    )
    r_without = SimulationRunner(seed=1).run(
        wf, 200, arrival_interval_minutes=5.0, collect_events=False
    )
    assert r_with.kpi.completed_cases == r_without.kpi.completed_cases
    assert r_with.kpi.total_wait_minutes == pytest.approx(r_without.kpi.total_wait_minutes)
    assert r_with.kpi.actor_utilization == r_without.kpi.actor_utilization


def test_kpi_parity_discrete_engine():
    wf = _slq_before()
    r_with = SimulationRunner(seed=3).run(wf, 200, engine="discrete", collect_events=True)
    r_without = SimulationRunner(seed=3).run(wf, 200, engine="discrete", collect_events=False)
    assert r_with.kpi.completed_cases == r_without.kpi.completed_cases
    assert r_with.kpi.failed_cases == r_without.kpi.failed_cases
    assert r_with.kpi.total_cost == pytest.approx(r_without.kpi.total_cost)


def test_kpi_parity_discrete_with_arrival_interval():
    wf = _inv_before()
    r_with = SimulationRunner(seed=5).run(
        wf, 150, arrival_interval_minutes=3.0, engine="discrete", collect_events=True
    )
    r_without = SimulationRunner(seed=5).run(
        wf, 150, arrival_interval_minutes=3.0, engine="discrete", collect_events=False
    )
    assert r_with.kpi.completed_cases == r_without.kpi.completed_cases
    assert r_with.kpi.total_wait_minutes == pytest.approx(r_without.kpi.total_wait_minutes)


# ---------------------------------------------------------------------------
# Event list is empty when collect_events=False
# ---------------------------------------------------------------------------


def test_events_empty_when_not_collected_simple():
    result = SimulationRunner(seed=1).run(_slq_before(), 100, collect_events=False)
    assert result.events == []


def test_events_empty_when_not_collected_discrete():
    result = SimulationRunner(seed=1).run(
        _slq_before(), 100, engine="discrete", collect_events=False
    )
    assert result.events == []


def test_events_populated_when_collected():
    result = SimulationRunner(seed=1).run(_slq_before(), 100, collect_events=True)
    assert len(result.events) > 0


# ---------------------------------------------------------------------------
# Backward compatibility: omitting collect_events defaults to True
# ---------------------------------------------------------------------------


def test_backward_compat_collect_events_defaults_to_true():
    result = SimulationRunner(seed=42).run(_slq_before(), 100)
    assert len(result.events) > 0


def test_backward_compat_discrete_defaults_to_true():
    result = SimulationRunner(seed=42).run(_slq_before(), 50, engine="discrete")
    assert len(result.events) > 0


# ---------------------------------------------------------------------------
# Memory efficiency at scale
# ---------------------------------------------------------------------------


def test_memory_efficiency_simple_engine():
    """collect_events=False uses substantially less memory than True."""
    wf = _slq_before()
    n = 5000

    r_with = SimulationRunner(seed=42).run(wf, n, collect_events=True)
    r_without = SimulationRunner(seed=42).run(wf, n, collect_events=False)

    mem_with = sys.getsizeof(r_with.events) + sum(sys.getsizeof(e) for e in r_with.events)
    mem_without = sys.getsizeof(r_without.events)

    assert mem_with > mem_without * 100, (
        f"Expected collect_events=True to use significantly more memory "
        f"({mem_with} bytes vs {mem_without} bytes)"
    )
    assert r_with.kpi.completed_cases == r_without.kpi.completed_cases


def test_memory_efficiency_discrete_engine():
    """Discrete engine with collect_events=False also avoids event allocation."""
    wf = _slq_before()
    n = 500
    r_with = SimulationRunner(seed=7).run(wf, n, engine="discrete", collect_events=True)
    r_without = SimulationRunner(seed=7).run(wf, n, engine="discrete", collect_events=False)
    assert len(r_with.events) > 0
    assert len(r_without.events) == 0


# ---------------------------------------------------------------------------
# All three bundled example workflows
# ---------------------------------------------------------------------------


def test_all_examples_kpi_parity():
    examples = [
        sales_lead_qualification.build_before_workflow,
        invoice_processing.build_before_workflow,
        customer_support_ticket_resolution.build_before_workflow,
    ]
    for wf_fn in examples:
        wf = wf_fn()
        r_with = SimulationRunner(seed=10).run(wf, 200, collect_events=True)
        r_without = SimulationRunner(seed=10).run(wf, 200, collect_events=False)
        assert r_with.kpi.completed_cases == r_without.kpi.completed_cases, wf.name
        assert r_with.kpi.total_cost == pytest.approx(r_without.kpi.total_cost), wf.name
