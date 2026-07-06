"""Tests for the growth projection engine."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.growth import (
    GrowthConfig,
    generate_growth_report,
    project_growth,
)
from b2b_workflow_simulator.org_model import Department, Organization


def _make_org() -> Organization:
    org = Organization(org_id="co", name="Test Co")
    org.add_department(Department(dept_id="d1", name="D1"))
    return org


# ---------------------------------------------------------------------------
# GrowthConfig validation
# ---------------------------------------------------------------------------


def test_growth_config_defaults():
    cfg = GrowthConfig()
    assert len(cfg.seasonal_multipliers) == 12
    assert cfg.monthly_growth_rate == 0.05


def test_growth_config_invalid_seasonal_multipliers_raises():
    with pytest.raises(ValueError, match="12"):
        GrowthConfig(seasonal_multipliers=[1.0] * 11)


def test_growth_config_invalid_base_cases_raises():
    with pytest.raises(ValueError, match="positive"):
        GrowthConfig(base_cases_per_month=0)


def test_growth_config_invalid_base_headcount_raises():
    with pytest.raises(ValueError, match="positive"):
        GrowthConfig(base_headcount=0)


# ---------------------------------------------------------------------------
# project_growth — output structure
# ---------------------------------------------------------------------------


def test_project_growth_produces_12_points():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    assert len(projection.points) == 12


def test_project_growth_month_indexes_1_to_12():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    assert [p.month for p in projection.points] == list(range(1, 13))


def test_project_growth_cases_increase_with_positive_growth():
    org = _make_org()
    cfg = GrowthConfig(monthly_growth_rate=0.10, base_cases_per_month=100)
    projection = project_growth(org, None, cfg)
    assert projection.points[-1].projected_cases > projection.points[0].projected_cases


def test_project_growth_zero_growth_stable_cases():
    org = _make_org()
    cfg = GrowthConfig(monthly_growth_rate=0.0, base_cases_per_month=100)
    projection = project_growth(org, None, cfg)
    for p in projection.points:
        assert p.projected_cases == 100


def test_project_growth_headcount_increases():
    org = _make_org()
    cfg = GrowthConfig(headcount_growth_rate=0.05, base_headcount=10)
    projection = project_growth(org, None, cfg)
    assert projection.points[-1].projected_headcount > projection.points[0].projected_headcount


def test_project_growth_ai_adoption_increases():
    org = _make_org()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.05)
    projection = project_growth(org, None, cfg)
    assert projection.points[-1].ai_adoption_level > projection.points[0].ai_adoption_level


def test_project_growth_ai_adoption_capped_at_1():
    org = _make_org()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.20)
    projection = project_growth(org, None, cfg)
    for p in projection.points:
        assert p.ai_adoption_level <= 1.0


def test_project_growth_org_id_set():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    assert projection.org_id == "co"
    assert projection.org_name == "Test Co"


# ---------------------------------------------------------------------------
# GrowthProjection accessors
# ---------------------------------------------------------------------------


def test_projection_at_month_valid():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    p = projection.at_month(1)
    assert p.month == 1


def test_projection_at_month_out_of_range_raises():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    with pytest.raises(ValueError):
        projection.at_month(13)


def test_projection_three_month():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    assert len(projection.three_month()) == 3


def test_projection_six_month():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    assert len(projection.six_month()) == 6


def test_projection_twelve_month():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    assert len(projection.twelve_month()) == 12


def test_projection_no_breaking_points_low_growth():
    org = _make_org()
    cfg = GrowthConfig(monthly_growth_rate=0.01, base_cases_per_month=10, base_headcount=100)
    projection = project_growth(org, None, cfg)
    assert projection.first_breaking_point() is None


def test_projection_breaking_point_detected():
    org = _make_org()
    cfg = GrowthConfig(
        monthly_growth_rate=0.50,
        base_cases_per_month=500,
        base_headcount=2,
        actor_capacity_per_head=10.0,
        simulation_days_per_month=22,
    )
    projection = project_growth(org, None, cfg)
    bps = projection.breaking_points()
    assert len(bps) > 0
    for bp in bps:
        assert bp.breaking_point_reason is not None


def test_projection_peak_utilization_month():
    org = _make_org()
    cfg = GrowthConfig(monthly_growth_rate=0.10)
    projection = project_growth(org, None, cfg)
    peak = projection.peak_utilization_month()
    max_util = max(p.capacity_utilization for p in projection.points)
    assert peak.capacity_utilization == max_util


# ---------------------------------------------------------------------------
# generate_growth_report
# ---------------------------------------------------------------------------


def test_generate_growth_report_contains_org_name():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    report = generate_growth_report(projection)
    assert "Test Co" in report


def test_generate_growth_report_contains_12_rows():
    org = _make_org()
    projection = project_growth(org, None, GrowthConfig())
    report = generate_growth_report(projection)
    assert report.count("\n") >= 12


def test_generate_growth_report_no_breaking_points_message():
    org = _make_org()
    cfg = GrowthConfig(monthly_growth_rate=0.0, base_cases_per_month=5, base_headcount=100)
    projection = project_growth(org, None, cfg)
    assert projection.first_breaking_point() is None
    report = generate_growth_report(projection)
    assert "No breaking points detected" in report


def test_generate_growth_report_breaking_point_mentioned():
    org = _make_org()
    cfg = GrowthConfig(
        monthly_growth_rate=0.50,
        base_cases_per_month=500,
        base_headcount=2,
        actor_capacity_per_head=10.0,
    )
    projection = project_growth(org, None, cfg)
    if projection.breaking_points():
        report = generate_growth_report(projection)
        assert "First breaking point" in report
