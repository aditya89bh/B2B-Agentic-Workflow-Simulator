"""Tests for org_health: OrgHealthScore, HealthFactor, compute_org_health."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.budget import OPERATING, DepartmentBudget, OrgBudget
from b2b_workflow_simulator.examples import (
    invoice_processing,
    sales_lead_qualification,
)
from b2b_workflow_simulator.org_health import (
    AI_READINESS,
    BUDGET_PRESSURE,
    COMPLIANCE_RISK,
    HEALTH_FACTOR_LABELS,
    HEALTH_FACTORS,
    HealthFactor,
    OrgHealthScore,
    compute_org_health,
    generate_org_health_report,
)
from b2b_workflow_simulator.org_model import Department, Organization, Role, Team
from b2b_workflow_simulator.simulation import SimulationRunner


def _make_org() -> Organization:
    org = Organization(org_id="co", name="Test Co")
    org.add_department(Department(dept_id="d1", name="D1"))
    org.add_department(Department(dept_id="d2", name="D2"))
    org.add_team(Team(team_id="t1", name="T1", department_id="d1"))
    org.add_team(Team(team_id="t2", name="T2", department_id="d2"))
    org.add_role(Role(role_id="r1", name="R1", actor_id="a1", department_id="d1", team_id="t1"))
    org.add_role(Role(role_id="r2", name="R2", actor_id="a2", department_id="d2", team_id="t2",
                      is_ai_agent=True))
    org.add_workflow_id("wf-1")
    org.add_workflow_id("wf-2")
    return org


def _make_kpis() -> dict:
    runner = SimulationRunner(seed=42)
    r1 = runner.run(sales_lead_qualification.build_before_workflow(), 100)
    r2 = runner.run(invoice_processing.build_before_workflow(), 100)
    return {
        "wf-1": r1.kpi,
        "wf-2": r2.kpi,
    }


# ---------------------------------------------------------------------------
# HealthFactor
# ---------------------------------------------------------------------------


def test_health_factor_weighted_score():
    f = HealthFactor(factor_id="test", name="Test", score=80.0, weight=2.0, explanation="ok")
    assert f.weighted_score == pytest.approx(160.0)


# ---------------------------------------------------------------------------
# OrgHealthScore
# ---------------------------------------------------------------------------


def _make_health_score(scores: list[float]) -> OrgHealthScore:
    factors = [
        HealthFactor(
            factor_id=fid, name=HEALTH_FACTOR_LABELS[fid],
            score=s, weight=1.0, explanation="",
        )
        for fid, s in zip(HEALTH_FACTORS[: len(scores)], scores, strict=False)
    ]
    return OrgHealthScore(org_id="co", org_name="Test Co", factors=factors)


def test_overall_score_equals_mean_for_equal_weights():
    hs = _make_health_score([80.0, 90.0, 70.0])
    assert hs.overall_score == pytest.approx(80.0)


def test_overall_score_zero_for_empty_factors():
    hs = OrgHealthScore(org_id="co", org_name="Co", factors=[])
    assert hs.overall_score == 0.0


def test_grade_a():
    hs = _make_health_score([95.0])
    assert hs.grade == "A"


def test_grade_b():
    hs = _make_health_score([85.0])
    assert hs.grade == "B"


def test_grade_c():
    hs = _make_health_score([75.0])
    assert hs.grade == "C"


def test_grade_d():
    hs = _make_health_score([65.0])
    assert hs.grade == "D"


def test_grade_f():
    hs = _make_health_score([55.0])
    assert hs.grade == "F"


def test_top_risks_returns_lowest_scores():
    hs = _make_health_score([80.0, 40.0, 90.0, 20.0])
    risks = hs.top_risks(2)
    assert risks[0].score == 20.0
    assert risks[1].score == 40.0


def test_top_risks_count_clipped_to_available():
    hs = _make_health_score([70.0, 80.0])
    risks = hs.top_risks(10)
    assert len(risks) == 2


def test_factor_lookup_by_id():
    hs = _make_health_score([77.0])
    fid = list(HEALTH_FACTORS)[0]
    found = hs.factor(fid)
    assert found is not None
    assert found.factor_id == fid


def test_factor_lookup_unknown_returns_none():
    hs = _make_health_score([77.0])
    assert hs.factor("no-such-factor") is None


def test_summary_contains_org_name():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    assert "Test Co" in hs.summary


# ---------------------------------------------------------------------------
# compute_org_health
# ---------------------------------------------------------------------------


def test_compute_org_health_returns_8_factors():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    assert len(hs.factors) == 8


def test_compute_org_health_all_factor_ids_present():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    factor_ids = {f.factor_id for f in hs.factors}
    for fid in HEALTH_FACTORS:
        assert fid in factor_ids


def test_compute_org_health_overall_score_in_range():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    assert 0.0 <= hs.overall_score <= 100.0


def test_compute_org_health_with_budget():
    org = _make_org()
    kpis = _make_kpis()
    ob = OrgBudget(org_id="co")
    db = DepartmentBudget(dept_id="d1", annual_budget=100_000.0)
    db.allocate(OPERATING, 90_000.0)
    db.record_spend(OPERATING, 50_000.0)
    ob.add_dept_budget(db)
    hs = compute_org_health(org, ob, None, kpis)
    budget_factor = hs.factor(BUDGET_PRESSURE)
    assert budget_factor is not None
    assert budget_factor.score < 100.0


def test_compute_org_health_empty_kpis():
    org = _make_org()
    hs = compute_org_health(org, None, None, {})
    assert len(hs.factors) == 8
    assert hs.overall_score >= 0.0


def test_compute_org_health_high_failure_rate_lowers_compliance_risk():
    from b2b_workflow_simulator.kpi import KPIResult
    kpi = KPIResult(workflow_name="test", total_cases=100, failed_cases=50)
    org = _make_org()
    hs = compute_org_health(org, None, None, {"wf": kpi})
    compliance = hs.factor(COMPLIANCE_RISK)
    assert compliance is not None
    assert compliance.score < 50.0


def test_compute_org_health_ai_readiness_increases_with_ai_agents():
    from b2b_workflow_simulator.kpi import KPIResult
    org_many_ai = Organization(org_id="co", name="AI Co")
    org_many_ai.add_department(Department(dept_id="d1", name="D1"))
    for i in range(8):
        org_many_ai.add_role(Role(
            role_id=f"ai-{i}", name=f"AI {i}", actor_id=f"ai-a{i}",
            department_id="d1", is_ai_agent=True,
        ))
    for i in range(2):
        org_many_ai.add_role(Role(
            role_id=f"human-{i}", name=f"Human {i}", actor_id=f"ha{i}", department_id="d1",
        ))

    org_no_ai = Organization(org_id="co2", name="Human Co")
    org_no_ai.add_department(Department(dept_id="d1", name="D1"))
    for i in range(10):
        org_no_ai.add_role(Role(
            role_id=f"human-{i}", name=f"Human {i}", actor_id=f"ha{i}", department_id="d1",
        ))

    kpi = KPIResult(workflow_name="test", total_cases=100)
    hs_ai = compute_org_health(org_many_ai, None, None, {"wf": kpi})
    hs_human = compute_org_health(org_no_ai, None, None, {"wf": kpi})

    ai_ready_ai = hs_ai.factor(AI_READINESS)
    ai_ready_human = hs_human.factor(AI_READINESS)
    assert ai_ready_ai is not None
    assert ai_ready_human is not None
    assert ai_ready_ai.score > ai_ready_human.score


# ---------------------------------------------------------------------------
# generate_org_health_report
# ---------------------------------------------------------------------------


def test_generate_org_health_report_contains_org_name():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    report = generate_org_health_report(hs)
    assert "Test Co" in report


def test_generate_org_health_report_contains_grade():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    report = generate_org_health_report(hs)
    assert f"Grade: {hs.grade}" in report


def test_generate_org_health_report_contains_all_factor_names():
    org = _make_org()
    kpis = _make_kpis()
    hs = compute_org_health(org, None, None, kpis)
    report = generate_org_health_report(hs)
    for label in HEALTH_FACTOR_LABELS.values():
        assert label in report


def test_health_factor_labels_complete():
    for fid in HEALTH_FACTORS:
        assert fid in HEALTH_FACTOR_LABELS
