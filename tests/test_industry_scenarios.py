"""Tests for the 8 new industry workflow scenario modules."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.simulation import SimulationRunner


def _get_modules():
    from b2b_workflow_simulator.examples import (
        customer_onboarding_implementation,
        finance_month_end_close,
        healthcare_prior_authorization,
        hr_recruiting_screening,
        insurance_claims_intake,
        it_support_triage,
        legal_contract_review,
        procurement_vendor_onboarding,
    )
    return [
        ("healthcare-prior-authorization", healthcare_prior_authorization),
        ("insurance-claims-intake", insurance_claims_intake),
        ("hr-recruiting-screening", hr_recruiting_screening),
        ("procurement-vendor-onboarding", procurement_vendor_onboarding),
        ("legal-contract-review", legal_contract_review),
        ("it-support-triage", it_support_triage),
        ("finance-month-end-close", finance_month_end_close),
        ("customer-onboarding-implementation", customer_onboarding_implementation),
    ]


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_before_workflow_validates(slug, mod):
    wf = mod.build_before_workflow()
    wf.validate()
    assert wf.workflow_id == f"{slug}-before"


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_after_workflow_validates(slug, mod):
    wf = mod.build_after_workflow()
    wf.validate()
    assert wf.workflow_id == f"{slug}-after"


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_before_workflow_has_at_least_5_nodes(slug, mod):
    wf = mod.build_before_workflow()
    assert len(wf.nodes) >= 5, f"{slug}: expected >=5 nodes, got {len(wf.nodes)}"


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_after_workflow_has_at_least_5_nodes(slug, mod):
    wf = mod.build_after_workflow()
    assert len(wf.nodes) >= 5


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_after_workflow_uses_ai_actors(slug, mod):
    wf = mod.build_after_workflow()
    ai_actors = [a for a in wf.actors.values() if isinstance(a, AIAgentActor)]
    assert len(ai_actors) >= 1, f"{slug}: after workflow must have at least one AI actor"


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_before_workflow_has_terminal_paths(slug, mod):
    wf = mod.build_before_workflow()
    terminal_nodes = [n for n in wf.nodes.values() if n.is_terminal]
    assert len(terminal_nodes) >= 1


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_after_workflow_has_terminal_paths(slug, mod):
    wf = mod.build_after_workflow()
    terminal_nodes = [n for n in wf.nodes.values() if n.is_terminal]
    assert len(terminal_nodes) >= 1


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_before_after_produce_different_kpis(slug, mod):
    before_wf = mod.build_before_workflow()
    after_wf = mod.build_after_workflow()
    runner = SimulationRunner(seed=42)
    before_r = runner.run(before_wf, 100, collect_events=False)
    after_r = SimulationRunner(seed=42).run(after_wf, 100, collect_events=False)
    assert before_r.kpi.total_cost != after_r.kpi.total_cost or \
           before_r.kpi.avg_cycle_time_minutes != after_r.kpi.avg_cycle_time_minutes, (
        f"{slug}: before and after should produce different KPIs"
    )


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_default_conservative_aggressive_assumptions_differ(slug, mod):
    base = mod.default_assumptions()
    conservative = mod.conservative_assumptions()
    aggressive = mod.aggressive_assumptions()
    assert (
        conservative.ai_error_rate_multiplier != base.ai_error_rate_multiplier
        or conservative.ai_cost_multiplier != base.ai_cost_multiplier
    ), f"{slug}: conservative should differ from base"
    assert (
        aggressive.ai_cost_multiplier != base.ai_cost_multiplier
        or aggressive.human_hourly_cost_multiplier != base.human_hourly_cost_multiplier
    ), f"{slug}: aggressive should differ from base"


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_scenario_notes_has_required_keys(slug, mod):
    notes = mod.scenario_notes()
    assert "limitations" in notes
    assert "commands" in notes
    assert len(notes["limitations"]) >= 2
    assert len(notes["commands"]) >= 1


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_assumption_profiles_have_valid_num_cases(slug, mod):
    profiles = [
        mod.default_assumptions(), mod.conservative_assumptions(), mod.aggressive_assumptions()
    ]
    for prof in profiles:
        assert prof.num_cases > 0


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_assumption_profiles_have_implementation_cost(slug, mod):
    base = mod.default_assumptions()
    assert base.implementation_cost is not None and base.implementation_cost > 0


@pytest.mark.parametrize("slug,mod", _get_modules())
def test_conservative_profile_kpis_differ_from_base(slug, mod):
    from b2b_workflow_simulator.assumptions import apply_profile_to_workflow
    base = mod.default_assumptions()
    conservative = mod.conservative_assumptions()
    after_wf = mod.build_after_workflow()
    r_base = SimulationRunner(seed=base.seed).run(
        apply_profile_to_workflow(after_wf, base), base.num_cases, collect_events=False
    )
    after_wf2 = mod.build_after_workflow()
    r_cons = SimulationRunner(seed=conservative.seed).run(
        apply_profile_to_workflow(after_wf2, conservative),
        conservative.num_cases,
        collect_events=False,
    )
    assert r_base.kpi.total_cost != r_cons.kpi.total_cost or \
           r_base.kpi.completed_cases != r_cons.kpi.completed_cases, (
        f"{slug}: conservative should produce different KPIs than base"
    )
