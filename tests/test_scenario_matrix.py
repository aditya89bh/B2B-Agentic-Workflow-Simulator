"""Tests for the scenario_matrix module."""

from __future__ import annotations

import json

from b2b_workflow_simulator.scenario_matrix import (
    build_scenario_matrix,
    matrix_to_json,
    matrix_to_text,
)
from b2b_workflow_simulator.scenarios import scenario_names


def test_build_matrix_returns_all_scenarios():
    rows = build_scenario_matrix()
    assert len(rows) == len(scenario_names())


def test_build_matrix_sorted_by_savings():
    rows = build_scenario_matrix()
    savings = [r["total_cost_savings"] for r in rows]
    assert savings == sorted(savings, reverse=True)


def test_build_matrix_required_fields():
    rows = build_scenario_matrix()
    for row in rows:
        for field in ("slug", "name", "category", "profile",
                      "before_cost_per_case", "after_cost_per_case",
                      "total_cost_savings", "risk_level"):
            assert field in row, f"Missing field: {field}"


def test_build_matrix_profile_base():
    rows = build_scenario_matrix(profile_name="base")
    for row in rows:
        assert row["profile"] == "base"


def test_build_matrix_profile_conservative():
    rows = build_scenario_matrix(profile_name="conservative")
    for row in rows:
        assert row["profile"] == "conservative"


def test_build_matrix_subset():
    slugs = ["it-support-triage", "hr-recruiting-screening"]
    rows = build_scenario_matrix(scenario_slugs=slugs)
    assert len(rows) == 2
    row_slugs = {r["slug"] for r in rows}
    assert row_slugs == set(slugs)


def test_build_matrix_deterministic():
    rows1 = build_scenario_matrix()
    rows2 = build_scenario_matrix()
    assert [r["slug"] for r in rows1] == [r["slug"] for r in rows2]
    assert [r["total_cost_savings"] for r in rows1] == [r["total_cost_savings"] for r in rows2]


def test_matrix_to_text_contains_header():
    rows = build_scenario_matrix(scenario_slugs=["it-support-triage"])
    text = matrix_to_text(rows)
    assert "SCENARIO MATRIX" in text


def test_matrix_to_text_contains_scenario_names():
    rows = build_scenario_matrix(scenario_slugs=["it-support-triage", "hr-recruiting-screening"])
    text = matrix_to_text(rows)
    assert "IT Support" in text or "Triage" in text
    assert "HR" in text or "Recruiting" in text


def test_matrix_to_text_empty():
    text = matrix_to_text([])
    assert "No scenarios" in text


def test_matrix_to_json_valid():
    rows = build_scenario_matrix(scenario_slugs=["it-support-triage"])
    json_str = matrix_to_json(rows)
    data = json.loads(json_str)
    assert isinstance(data, list)
    assert len(data) == 1


def test_matrix_to_json_all_scenarios():
    rows = build_scenario_matrix()
    json_str = matrix_to_json(rows)
    data = json.loads(json_str)
    assert len(data) == len(scenario_names())


def test_risk_level_is_valid():
    rows = build_scenario_matrix(scenario_slugs=["healthcare-prior-authorization"])
    for row in rows:
        assert row["risk_level"] in ("Low", "Moderate", "High")
