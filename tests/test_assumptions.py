"""Tests for AssumptionProfile: load, save, validation, and CLI override."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from b2b_workflow_simulator.assumptions import (
    AssumptionProfile,
    load_assumption_profile,
    save_assumption_profile,
)

# ---------------------------------------------------------------------------
# Default construction
# ---------------------------------------------------------------------------


def test_default_profile_valid():
    p = AssumptionProfile()
    assert p.num_cases == 200
    assert p.seed == 42
    assert p.engine == "simple"
    assert p.currency_label == "$"


def test_profile_custom_fields():
    p = AssumptionProfile(
        num_cases=500, seed=7, arrival_interval_minutes=5.0,
        implementation_cost=10_000.0, engine="discrete",
        currency_label="€", description="Test profile",
    )
    assert p.num_cases == 500
    assert p.engine == "discrete"
    assert p.currency_label == "€"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_invalid_num_cases_raises():
    with pytest.raises(ValueError, match="num_cases"):
        AssumptionProfile(num_cases=0)


def test_invalid_engine_raises():
    with pytest.raises(ValueError, match="engine"):
        AssumptionProfile(engine="unknown")


def test_negative_arrival_interval_raises():
    with pytest.raises(ValueError, match="arrival_interval"):
        AssumptionProfile(arrival_interval_minutes=-1.0)


def test_negative_implementation_cost_raises():
    with pytest.raises(ValueError, match="implementation_cost"):
        AssumptionProfile(implementation_cost=-100.0)


def test_invalid_ai_error_rate_multiplier_raises():
    with pytest.raises(ValueError, match="ai_error_rate_multiplier"):
        AssumptionProfile(ai_error_rate_multiplier=0.0)


def test_invalid_ai_cost_multiplier_raises():
    with pytest.raises(ValueError, match="ai_cost_multiplier"):
        AssumptionProfile(ai_cost_multiplier=-1.0)


# ---------------------------------------------------------------------------
# Save and load
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip():
    p = AssumptionProfile(
        num_cases=300, seed=99, implementation_cost=8000.0,
        description="roundtrip test",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "profile.json"
        save_assumption_profile(p, path)
        loaded = load_assumption_profile(path)
    assert loaded.num_cases == 300
    assert loaded.seed == 99
    assert loaded.implementation_cost == 8000.0
    assert loaded.description == "roundtrip test"


def test_saved_file_is_valid_json():
    p = AssumptionProfile(num_cases=100)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"
        save_assumption_profile(p, path)
        data = json.loads(path.read_text())
    assert "num_cases" in data
    assert data["num_cases"] == 100


def test_load_unknown_keys_ignored():
    """Unknown keys in JSON are silently ignored for forward compatibility."""
    data = {"num_cases": 150, "seed": 1, "unknown_future_field": "ignored"}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "profile.json"
        path.write_text(json.dumps(data))
        loaded = load_assumption_profile(path)
    assert loaded.num_cases == 150


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_assumption_profile("/nonexistent/path/profile.json")


def test_load_invalid_json_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "bad.json"
        path.write_text("{not valid json")
        with pytest.raises((ValueError, json.JSONDecodeError)):
            load_assumption_profile(path)


def test_load_invalid_values_raises():
    data = {"num_cases": -5}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "bad.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            load_assumption_profile(path)


# ---------------------------------------------------------------------------
# Sample profiles
# ---------------------------------------------------------------------------


def test_sample_base_profile_loads():
    from pathlib import Path
    base_path = (
        Path(__file__).parent.parent
        / "src/b2b_workflow_simulator/examples/data/assumptions_base.json"
    )
    p = load_assumption_profile(base_path)
    assert p.num_cases > 0
    assert p.ai_error_rate_multiplier == 1.0


def test_sample_conservative_profile_has_higher_error_rate():
    from pathlib import Path
    base_path = (
        Path(__file__).parent.parent
        / "src/b2b_workflow_simulator/examples/data"
    )
    base = load_assumption_profile(base_path / "assumptions_base.json")
    conservative = load_assumption_profile(base_path / "assumptions_conservative.json")
    assert conservative.ai_error_rate_multiplier > base.ai_error_rate_multiplier


def test_sample_aggressive_profile_has_lower_ai_cost():
    from pathlib import Path
    base_path = (
        Path(__file__).parent.parent
        / "src/b2b_workflow_simulator/examples/data"
    )
    base = load_assumption_profile(base_path / "assumptions_base.json")
    aggressive = load_assumption_profile(base_path / "assumptions_aggressive.json")
    assert aggressive.ai_cost_multiplier < base.ai_cost_multiplier


# ---------------------------------------------------------------------------
# to_dict / from_dict
# ---------------------------------------------------------------------------


def test_to_dict_roundtrip():
    p = AssumptionProfile(num_cases=400, description="dict test")
    d = p.to_dict()
    p2 = AssumptionProfile.from_dict(d)
    assert p2.num_cases == 400
    assert p2.description == "dict test"
