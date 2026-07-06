"""Tests for growth projection AI adoption seeding from org structure."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.growth import GrowthConfig, project_growth
from b2b_workflow_simulator.org_model import Department, Organization, Role


def _org_no_ai() -> Organization:
    org = Organization(org_id="o", name="No-AI Org")
    org.add_department(Department(dept_id="d1", name="D1"))
    for i in range(5):
        org.add_role(Role(role_id=f"r{i}", name=f"R{i}", actor_id=f"a{i}", department_id="d1"))
    return org


def _org_half_ai() -> Organization:
    org = Organization(org_id="o", name="Half-AI Org")
    org.add_department(Department(dept_id="d1", name="D1"))
    for i in range(5):
        org.add_role(Role(
            role_id=f"ai{i}", name=f"AI {i}", actor_id=f"a{i}",
            department_id="d1", is_ai_agent=True,
        ))
    for i in range(5):
        org.add_role(Role(role_id=f"h{i}", name=f"H{i}", actor_id=f"h{i}", department_id="d1"))
    return org


def _org_all_ai() -> Organization:
    org = Organization(org_id="o", name="All-AI Org")
    org.add_department(Department(dept_id="d1", name="D1"))
    for i in range(4):
        org.add_role(Role(
            role_id=f"ai{i}", name=f"AI {i}", actor_id=f"a{i}",
            department_id="d1", is_ai_agent=True,
        ))
    return org


# ---------------------------------------------------------------------------
# Org with no AI agents starts at 0.0
# ---------------------------------------------------------------------------


def test_no_ai_org_starts_at_zero_adoption():
    org = _org_no_ai()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.0)
    proj = project_growth(org, None, cfg)
    assert proj.points[0].ai_adoption_level == pytest.approx(0.0)
    for p in proj.points:
        assert p.ai_adoption_level == pytest.approx(0.0)


def test_no_ai_org_grows_with_increase_rate():
    org = _org_no_ai()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.10)
    proj = project_growth(org, None, cfg)
    assert proj.points[0].ai_adoption_level == pytest.approx(0.0)
    assert proj.points[1].ai_adoption_level == pytest.approx(0.10)
    # month 12: 0+0.1*11=1.1 → capped at 1.0
    assert proj.points[11].ai_adoption_level == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Org with some AI agents seeds from org fraction
# ---------------------------------------------------------------------------


def test_half_ai_org_starts_at_half_adoption():
    org = _org_half_ai()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.0)
    proj = project_growth(org, None, cfg)
    for p in proj.points:
        assert p.ai_adoption_level == pytest.approx(0.5)


def test_half_ai_org_with_increase_starts_above_zero():
    org = _org_half_ai()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.05)
    proj = project_growth(org, None, cfg)
    # Month 1 should be 0.5 + 0.05 * 0 = 0.5
    assert proj.points[0].ai_adoption_level == pytest.approx(0.5)
    # Month 2 should be 0.5 + 0.05 = 0.55
    assert proj.points[1].ai_adoption_level == pytest.approx(0.55)


def test_all_ai_org_starts_at_full_adoption():
    org = _org_all_ai()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.0)
    proj = project_growth(org, None, cfg)
    for p in proj.points:
        assert p.ai_adoption_level == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Explicit initial_ai_adoption override
# ---------------------------------------------------------------------------


def test_explicit_initial_adoption_overrides_org():
    org = _org_half_ai()  # would derive 0.5
    cfg = GrowthConfig(initial_ai_adoption=0.0, ai_adoption_increase_rate=0.0)
    proj = project_growth(org, None, cfg)
    for p in proj.points:
        assert p.ai_adoption_level == pytest.approx(0.0), (
            "Explicit initial_ai_adoption=0.0 should override the org's 50% AI fraction"
        )


def test_explicit_override_1_0():
    org = _org_no_ai()  # would derive 0.0
    cfg = GrowthConfig(initial_ai_adoption=0.8, ai_adoption_increase_rate=0.0)
    proj = project_growth(org, None, cfg)
    for p in proj.points:
        assert p.ai_adoption_level == pytest.approx(0.8)


def test_invalid_initial_adoption_raises():
    with pytest.raises(ValueError, match="initial_ai_adoption"):
        GrowthConfig(initial_ai_adoption=1.5)


def test_invalid_initial_adoption_negative_raises():
    with pytest.raises(ValueError, match="initial_ai_adoption"):
        GrowthConfig(initial_ai_adoption=-0.1)


# ---------------------------------------------------------------------------
# AI adoption influences cost reduction
# ---------------------------------------------------------------------------


def test_high_ai_org_has_lower_projected_cost():
    """Org with high AI adoption should project lower costs due to AI discount."""
    org_low = _org_no_ai()
    org_high = _org_all_ai()
    cfg = GrowthConfig(ai_adoption_increase_rate=0.0, base_cases_per_month=100)
    proj_low = project_growth(org_low, None, cfg)
    proj_high = project_growth(org_high, None, cfg)
    # High AI org should have lower cost in all months
    for i in range(12):
        assert proj_high.points[i].projected_cost <= proj_low.points[i].projected_cost, (
            f"Month {i + 1}: high-AI org should have lower projected cost"
        )


# ---------------------------------------------------------------------------
# Empty org (zero headcount) handled gracefully
# ---------------------------------------------------------------------------


def test_empty_org_zero_headcount_defaults_to_zero_adoption():
    org = Organization(org_id="empty", name="Empty Org")
    cfg = GrowthConfig(ai_adoption_increase_rate=0.0)
    proj = project_growth(org, None, cfg)
    assert proj.points[0].ai_adoption_level == pytest.approx(0.0)
