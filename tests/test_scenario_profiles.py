"""Tests for scenario assumption profile JSON files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from b2b_workflow_simulator.assumptions import AssumptionProfile, load_assumption_profile
from b2b_workflow_simulator.scenarios import scenario_names

_DATA_DIR = Path(__file__).parent.parent / "src/b2b_workflow_simulator/examples/data/assumptions"
_PROFILE_NAMES = ("base", "conservative", "aggressive")


@pytest.mark.parametrize("slug", scenario_names())
@pytest.mark.parametrize("profile_name", _PROFILE_NAMES)
def test_profile_json_exists(slug, profile_name):
    path = _DATA_DIR / slug / f"{profile_name}.json"
    assert path.exists(), f"Missing: {path}"


@pytest.mark.parametrize("slug", scenario_names())
@pytest.mark.parametrize("profile_name", _PROFILE_NAMES)
def test_profile_json_is_valid_json(slug, profile_name):
    path = _DATA_DIR / slug / f"{profile_name}.json"
    data = json.loads(path.read_text())
    assert isinstance(data, dict)


@pytest.mark.parametrize("slug", scenario_names())
@pytest.mark.parametrize("profile_name", _PROFILE_NAMES)
def test_profile_loads_as_assumption_profile(slug, profile_name):
    path = _DATA_DIR / slug / f"{profile_name}.json"
    profile = load_assumption_profile(path)
    assert isinstance(profile, AssumptionProfile)
    assert profile.num_cases > 0


@pytest.mark.parametrize("slug", scenario_names())
def test_conservative_differs_from_base(slug):
    base = load_assumption_profile(_DATA_DIR / slug / "base.json")
    conservative = load_assumption_profile(_DATA_DIR / slug / "conservative.json")
    differs = (
        conservative.ai_error_rate_multiplier != base.ai_error_rate_multiplier
        or conservative.ai_cost_multiplier != base.ai_cost_multiplier
    )
    assert differs, f"{slug}: conservative.json should differ from base.json"


@pytest.mark.parametrize("slug", scenario_names())
def test_aggressive_differs_from_base(slug):
    base = load_assumption_profile(_DATA_DIR / slug / "base.json")
    aggressive = load_assumption_profile(_DATA_DIR / slug / "aggressive.json")
    differs = (
        aggressive.ai_cost_multiplier != base.ai_cost_multiplier
        or aggressive.human_hourly_cost_multiplier != base.human_hourly_cost_multiplier
    )
    assert differs, f"{slug}: aggressive.json should differ from base.json"


@pytest.mark.parametrize("slug", scenario_names())
def test_profile_slug_matches_description(slug):
    path = _DATA_DIR / slug / "base.json"
    profile = load_assumption_profile(path)
    assert slug in profile.description, (
        f"{slug}: base.json description should mention the scenario slug"
    )
