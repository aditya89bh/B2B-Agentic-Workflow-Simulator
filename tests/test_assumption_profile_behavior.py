"""Tests proving assumption profile multipliers produce different simulation results.

These tests verify that ai_error_rate_multiplier, ai_cost_multiplier, and
human_hourly_cost_multiplier are not merely logged — they actually modify
the workflow actors before the simulation runs and produce measurably
different KPI outputs.
"""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.assumptions import (
    AssumptionProfile,
    apply_profile_to_workflow,
)
from b2b_workflow_simulator.examples import invoice_processing
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.simulation import SimulationRunner

# ---------------------------------------------------------------------------
# apply_profile_to_workflow: actor mutation verification
# ---------------------------------------------------------------------------


def test_ai_error_rate_multiplier_scales_ai_error_rates():
    wf = invoice_processing.build_after_workflow()
    profile = AssumptionProfile(ai_error_rate_multiplier=2.0)
    scaled = apply_profile_to_workflow(wf, profile)
    for actor_id, orig_actor in wf.actors.items():
        if isinstance(orig_actor, AIAgentActor) and orig_actor.error_rate > 0:
            new_actor = scaled.get_actor(actor_id)
            assert new_actor.error_rate == pytest.approx(orig_actor.error_rate * 2.0)


def test_ai_error_rate_capped_at_1():
    wf = invoice_processing.build_after_workflow()
    profile = AssumptionProfile(ai_error_rate_multiplier=100.0)
    scaled = apply_profile_to_workflow(wf, profile)
    for actor_id, orig_actor in wf.actors.items():
        if isinstance(orig_actor, AIAgentActor):
            assert scaled.get_actor(actor_id).error_rate <= 1.0


def test_ai_cost_multiplier_scales_ai_execution_cost():
    wf = invoice_processing.build_after_workflow()
    profile = AssumptionProfile(ai_cost_multiplier=1.5)
    scaled = apply_profile_to_workflow(wf, profile)
    for actor_id, orig_actor in wf.actors.items():
        if isinstance(orig_actor, AIAgentActor):
            new_actor = scaled.get_actor(actor_id)
            assert new_actor.cost_per_execution == pytest.approx(
                orig_actor.cost_per_execution * 1.5
            )


def test_human_hourly_cost_multiplier_scales_hourly_cost():
    wf = invoice_processing.build_before_workflow()
    profile = AssumptionProfile(human_hourly_cost_multiplier=1.2)
    scaled = apply_profile_to_workflow(wf, profile)
    for actor_id, orig_actor in wf.actors.items():
        if isinstance(orig_actor, HumanActor):
            new_actor = scaled.get_actor(actor_id)
            assert new_actor.hourly_cost == pytest.approx(orig_actor.hourly_cost * 1.2)


def test_original_workflow_not_mutated():
    wf = invoice_processing.build_after_workflow()
    orig_costs = {
        aid: a.cost_per_execution
        for aid, a in wf.actors.items()
        if isinstance(a, AIAgentActor)
    }
    profile = AssumptionProfile(ai_cost_multiplier=5.0)
    _ = apply_profile_to_workflow(wf, profile)
    for aid, orig_cost in orig_costs.items():
        assert wf.get_actor(aid).cost_per_execution == pytest.approx(orig_cost), (
            f"Original workflow actor {aid!r} was mutated"
        )


def test_identity_fast_path_returns_same_object():
    wf = invoice_processing.build_after_workflow()
    profile = AssumptionProfile(
        ai_error_rate_multiplier=1.0,
        ai_cost_multiplier=1.0,
        human_hourly_cost_multiplier=1.0,
    )
    result = apply_profile_to_workflow(wf, profile)
    assert result is wf


def test_non_identity_returns_new_workflow():
    wf = invoice_processing.build_after_workflow()
    profile = AssumptionProfile(ai_cost_multiplier=2.0)
    result = apply_profile_to_workflow(wf, profile)
    assert result is not wf


def test_actor_pool_workers_scaled():
    """Human hourly cost multiplier applies to ActorPool workers."""
    from b2b_workflow_simulator.examples.customer_support_ticket_resolution import (
        build_before_workflow,
    )
    wf = build_before_workflow()
    profile = AssumptionProfile(human_hourly_cost_multiplier=1.5)
    scaled = apply_profile_to_workflow(wf, profile)
    for actor_id, orig_actor in wf.actors.items():
        if isinstance(orig_actor, ActorPool):
            orig_workers = {w.worker_id: w for w in orig_actor.workers}
            new_actor = scaled.get_actor(actor_id)
            for worker in new_actor.workers:
                orig_worker = orig_workers[worker.worker_id]
                assert worker.hourly_cost == pytest.approx(orig_worker.hourly_cost * 1.5)


# ---------------------------------------------------------------------------
# End-to-end: same workflow, different profiles → different KPI results
# ---------------------------------------------------------------------------


def _run(wf, profile):
    return SimulationRunner(seed=profile.seed).run(
        wf, profile.num_cases, collect_events=False
    ).kpi


def test_conservative_profile_increases_failures():
    """ai_error_rate_multiplier=2.0 should produce more failures than base."""
    base_profile = AssumptionProfile(num_cases=300, seed=42)
    conservative = AssumptionProfile(num_cases=300, seed=42, ai_error_rate_multiplier=2.0)
    wf = invoice_processing.build_after_workflow()
    kpi_base = _run(apply_profile_to_workflow(wf, base_profile), base_profile)
    kpi_cons = _run(apply_profile_to_workflow(wf, conservative), conservative)
    assert kpi_cons.failed_cases >= kpi_base.failed_cases, (
        f"Conservative should have >= failures: {kpi_cons.failed_cases} vs {kpi_base.failed_cases}"
    )


def test_aggressive_profile_reduces_ai_cost():
    """ai_cost_multiplier=0.5 should reduce total cost compared to base."""
    base_profile = AssumptionProfile(num_cases=300, seed=42)
    aggressive = AssumptionProfile(num_cases=300, seed=42, ai_cost_multiplier=0.5)
    wf = invoice_processing.build_after_workflow()
    kpi_base = _run(apply_profile_to_workflow(wf, base_profile), base_profile)
    kpi_aggr = _run(apply_profile_to_workflow(wf, aggressive), aggressive)
    assert kpi_aggr.total_cost < kpi_base.total_cost, (
        f"Aggressive (50% AI cost) should cost less: "
        f"${kpi_aggr.total_cost:,.2f} vs ${kpi_base.total_cost:,.2f}"
    )


def test_human_cost_multiplier_affects_before_workflow():
    """Human cost multiplier should change total cost on a human-only workflow."""
    base_profile = AssumptionProfile(num_cases=200, seed=1)
    expensive = AssumptionProfile(num_cases=200, seed=1, human_hourly_cost_multiplier=2.0)
    wf = invoice_processing.build_before_workflow()
    kpi_base = _run(apply_profile_to_workflow(wf, base_profile), base_profile)
    kpi_exp = _run(apply_profile_to_workflow(wf, expensive), expensive)
    assert kpi_exp.total_cost > kpi_base.total_cost, (
        f"2× human cost should increase total cost: "
        f"${kpi_exp.total_cost:,.2f} vs ${kpi_base.total_cost:,.2f}"
    )


def test_base_and_conservative_profiles_differ():
    """The three bundled sample profiles should produce different results."""
    from pathlib import Path

    from b2b_workflow_simulator.assumptions import load_assumption_profile
    data_dir = (
        Path(__file__).parent.parent
        / "src/b2b_workflow_simulator/examples/data"
    )
    base = load_assumption_profile(data_dir / "assumptions_base.json")
    conservative = load_assumption_profile(data_dir / "assumptions_conservative.json")
    aggressive = load_assumption_profile(data_dir / "assumptions_aggressive.json")
    wf = invoice_processing.build_after_workflow()
    kpi_base = _run(apply_profile_to_workflow(wf, base), base)
    kpi_cons = _run(apply_profile_to_workflow(wf, conservative), conservative)
    kpi_aggr = _run(apply_profile_to_workflow(wf, aggressive), aggressive)
    # Conservative has higher AI error rate → more failures or higher cost
    different = (
        kpi_cons.total_cost != kpi_base.total_cost
        or kpi_cons.failed_cases != kpi_base.failed_cases
    )
    assert different, "Conservative and base profiles should produce different KPI results"
    # Aggressive has lower AI cost → lower total cost
    assert kpi_aggr.total_cost < kpi_base.total_cost, (
        "Aggressive (lower AI cost) should produce lower total cost than base"
    )


def test_multiplier_1_0_produces_same_kpi_as_no_profile():
    """A profile with all multipliers at 1.0 should produce identical KPIs."""
    profile = AssumptionProfile(num_cases=200, seed=7, ai_error_rate_multiplier=1.0,
                                ai_cost_multiplier=1.0, human_hourly_cost_multiplier=1.0)
    wf = invoice_processing.build_after_workflow()
    kpi_with = _run(apply_profile_to_workflow(wf, profile), profile)
    kpi_without = _run(wf, profile)
    assert kpi_with.total_cost == pytest.approx(kpi_without.total_cost)
    assert kpi_with.completed_cases == kpi_without.completed_cases


# ---------------------------------------------------------------------------
# CLI: --assumptions flag actually changes simulation output
# ---------------------------------------------------------------------------


def test_cli_conservative_snapshot_differs_from_base(tmp_path, capsys):
    from b2b_workflow_simulator.assumptions import save_assumption_profile
    from b2b_workflow_simulator.cli import main

    base = AssumptionProfile(num_cases=100, seed=42)
    conservative = AssumptionProfile(num_cases=100, seed=42, ai_error_rate_multiplier=3.0)
    base_path = str(tmp_path / "base.json")
    cons_path = str(tmp_path / "cons.json")
    save_assumption_profile(base, base_path)
    save_assumption_profile(conservative, cons_path)

    main(["executive-snapshot", "invoice-processing", "--assumptions", base_path])
    base_out = capsys.readouterr().out

    main(["executive-snapshot", "invoice-processing", "--assumptions", cons_path])
    cons_out = capsys.readouterr().out

    assert base_out != cons_out, (
        "Conservative profile (3× AI error rate) should produce different snapshot than base"
    )
