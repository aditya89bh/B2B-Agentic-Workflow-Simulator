"""Tests for the scenario registry."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.scenarios import (
    SCENARIO_CATEGORIES,
    ScenarioDefinition,
    get_scenario,
    list_scenarios,
    scenario_exists,
    scenario_names,
    scenarios_by_category,
)

_EXPECTED_SLUGS = {
    "sales-lead-qualification",
    "invoice-processing",
    "customer-support-ticket-resolution",
    "healthcare-prior-authorization",
    "insurance-claims-intake",
    "hr-recruiting-screening",
    "procurement-vendor-onboarding",
    "legal-contract-review",
    "it-support-triage",
    "finance-month-end-close",
    "customer-onboarding-implementation",
}


def test_registry_contains_all_expected_slugs():
    names = set(scenario_names())
    assert _EXPECTED_SLUGS == names


def test_list_scenarios_returns_all():
    assert len(list_scenarios()) == len(_EXPECTED_SLUGS)


def test_slugs_are_unique():
    names = scenario_names()
    assert len(names) == len(set(names))


@pytest.mark.parametrize("slug", sorted(_EXPECTED_SLUGS))
def test_get_scenario_returns_definition(slug):
    s = get_scenario(slug)
    assert isinstance(s, ScenarioDefinition)
    assert s.slug == slug


@pytest.mark.parametrize("slug", sorted(_EXPECTED_SLUGS))
def test_scenario_exists(slug):
    assert scenario_exists(slug)


def test_unknown_slug_raises_key_error():
    with pytest.raises(KeyError, match="no-such-scenario"):
        get_scenario("no-such-scenario")


def test_scenario_not_exists_returns_false():
    assert not scenario_exists("does-not-exist")


@pytest.mark.parametrize("slug", sorted(_EXPECTED_SLUGS))
def test_every_scenario_has_builders(slug):
    s = get_scenario(slug)
    assert callable(s.before_builder)
    assert callable(s.after_builder)


@pytest.mark.parametrize("slug", sorted(_EXPECTED_SLUGS))
def test_every_scenario_builds_valid_workflows(slug):
    s = get_scenario(slug)
    before = s.before_builder()
    after = s.after_builder()
    before.validate()
    after.validate()
    assert len(before.nodes) >= 5
    assert len(after.nodes) >= 5


@pytest.mark.parametrize("slug", sorted(_EXPECTED_SLUGS))
def test_every_scenario_has_assumption_profiles(slug):
    s = get_scenario(slug)
    assert s.default_assumption_profile is not None
    assert s.conservative_assumption_profile is not None
    assert s.aggressive_assumption_profile is not None


@pytest.mark.parametrize("slug", sorted(_EXPECTED_SLUGS))
def test_every_scenario_has_limitations(slug):
    s = get_scenario(slug)
    assert len(s.limitations) >= 1
    for lim in s.limitations:
        assert isinstance(lim, str) and len(lim) > 10


@pytest.mark.parametrize("slug", sorted(_EXPECTED_SLUGS))
def test_every_scenario_has_recommended_commands(slug):
    s = get_scenario(slug)
    assert len(s.recommended_commands) >= 1


def test_scenarios_by_category_healthcare():
    healthcare = scenarios_by_category("healthcare")
    assert len(healthcare) == 1
    assert healthcare[0].slug == "healthcare-prior-authorization"


def test_scenarios_by_category_finance():
    finance_scenarios = scenarios_by_category("finance")
    slugs = {s.slug for s in finance_scenarios}
    assert "invoice-processing" in slugs
    assert "finance-month-end-close" in slugs


def test_scenarios_by_unknown_category_empty():
    assert scenarios_by_category("nonexistent_category") == []


def test_all_category_constants_exist():
    for cat in SCENARIO_CATEGORIES:
        assert isinstance(cat, str)


def test_scenarios_sorted_by_category_then_name():
    scenarios = list_scenarios()
    pairs = [(s.category, s.name) for s in scenarios]
    assert pairs == sorted(pairs)
