"""Tests for org_model: Organization, Department, Team, Role, ReportingLine, OrgUnit."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.org_model import (
    Department,
    Organization,
    ReportingLine,
    Role,
    Team,
)

# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------


def test_role_defaults():
    role = Role(role_id="r1", name="Analyst", actor_id="actor-1", department_id="dept-1")
    assert role.team_id is None
    assert not role.is_manager
    assert not role.is_ai_agent


def test_role_manager_flag():
    role = Role(
        role_id="mgr", name="Manager", actor_id="mgr-actor", department_id="dept-1",
        is_manager=True,
    )
    assert role.is_manager


def test_role_ai_agent_flag():
    role = Role(
        role_id="bot", name="AI Bot", actor_id="ai-1", department_id="dept-1",
        is_ai_agent=True,
    )
    assert role.is_ai_agent


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


def test_team_add_role_deduplicates():
    team = Team(team_id="t1", name="Team A", department_id="dept-1")
    team.add_role("r1")
    team.add_role("r1")
    assert team.role_ids.count("r1") == 1


def test_team_add_workflow_deduplicates():
    team = Team(team_id="t1", name="Team A", department_id="dept-1")
    team.add_workflow("wf-1")
    team.add_workflow("wf-1")
    assert team.workflow_ids.count("wf-1") == 1


def test_team_add_role_returns_self():
    team = Team(team_id="t1", name="Team A", department_id="dept-1")
    result = team.add_role("r1")
    assert result is team


def test_team_add_workflow_returns_self():
    team = Team(team_id="t1", name="Team A", department_id="dept-1")
    result = team.add_workflow("wf-1")
    assert result is team


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------


def test_department_add_team_deduplicates():
    dept = Department(dept_id="d1", name="Sales")
    dept.add_team("t1")
    dept.add_team("t1")
    assert dept.team_ids.count("t1") == 1


def test_department_add_workflow_deduplicates():
    dept = Department(dept_id="d1", name="Sales")
    dept.add_workflow("wf-1")
    dept.add_workflow("wf-1")
    assert dept.workflow_ids.count("wf-1") == 1


def test_department_add_team_returns_self():
    dept = Department(dept_id="d1", name="Sales")
    assert dept.add_team("t1") is dept


def test_department_add_workflow_returns_self():
    dept = Department(dept_id="d1", name="Sales")
    assert dept.add_workflow("wf-1") is dept


# ---------------------------------------------------------------------------
# Organization construction helpers
# ---------------------------------------------------------------------------


def _make_minimal_org() -> Organization:
    org = Organization(org_id="acme", name="Acme Corp")
    dept = Department(dept_id="sales", name="Sales")
    org.add_department(dept)
    team = Team(team_id="sales-team", name="Sales Team", department_id="sales")
    org.add_team(team)
    role = Role(
        role_id="rep", name="Sales Rep", actor_id="actor-1",
        department_id="sales", team_id="sales-team",
    )
    org.add_role(role)
    return org


def test_organization_add_department_accessible():
    org = _make_minimal_org()
    assert "sales" in org.departments
    assert org.get_department("sales").name == "Sales"


def test_organization_add_team_accessible():
    org = _make_minimal_org()
    assert "sales-team" in org.teams
    assert org.get_team("sales-team").name == "Sales Team"


def test_organization_add_role_accessible():
    org = _make_minimal_org()
    assert "rep" in org.roles
    assert org.get_role("rep").name == "Sales Rep"


def test_organization_get_unknown_department_raises():
    org = Organization(org_id="acme", name="Acme Corp")
    with pytest.raises(KeyError):
        org.get_department("unknown")


def test_organization_get_unknown_team_raises():
    org = Organization(org_id="acme", name="Acme Corp")
    with pytest.raises(KeyError):
        org.get_team("unknown")


def test_organization_get_unknown_role_raises():
    org = Organization(org_id="acme", name="Acme Corp")
    with pytest.raises(KeyError):
        org.get_role("unknown")


def test_organization_add_workflow_id_deduplicates():
    org = Organization(org_id="acme", name="Acme Corp")
    org.add_workflow_id("wf-1")
    org.add_workflow_id("wf-1")
    assert org.workflow_ids.count("wf-1") == 1


def test_organization_fluent_chaining():
    org = Organization(org_id="acme", name="Acme Corp")
    result = org.add_department(Department(dept_id="d1", name="D1"))
    assert result is org


# ---------------------------------------------------------------------------
# Hierarchy queries
# ---------------------------------------------------------------------------


def test_teams_for_department():
    org = _make_minimal_org()
    teams = org.teams_for_department("sales")
    assert len(teams) == 1
    assert teams[0].team_id == "sales-team"


def test_teams_for_unknown_department_returns_empty():
    org = _make_minimal_org()
    assert org.teams_for_department("unknown") == []


def test_roles_for_team():
    org = _make_minimal_org()
    roles = org.roles_for_team("sales-team")
    assert len(roles) == 1
    assert roles[0].role_id == "rep"


def test_roles_for_department():
    org = _make_minimal_org()
    roles = org.roles_for_department("sales")
    assert any(r.role_id == "rep" for r in roles)


def test_department_headcount():
    org = _make_minimal_org()
    assert org.department_headcount("sales") == 1


def test_total_headcount():
    org = _make_minimal_org()
    assert org.total_headcount() == 1


def test_ai_agent_count():
    org = Organization(org_id="o1", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))
    org.add_role(Role(
        role_id="ai-1", name="AI Bot", actor_id="a1", department_id="d1", is_ai_agent=True,
    ))
    org.add_role(Role(role_id="human-1", name="Human", actor_id="a2", department_id="d1"))
    assert org.ai_agent_count() == 1


def test_manager_count():
    org = Organization(org_id="o1", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))
    org.add_role(Role(role_id="m1", name="Mgr", actor_id="a1", department_id="d1", is_manager=True))
    org.add_role(Role(role_id="e1", name="Employee", actor_id="a2", department_id="d1"))
    assert org.manager_count() == 1


# ---------------------------------------------------------------------------
# Reporting lines
# ---------------------------------------------------------------------------


def _make_two_role_org() -> Organization:
    org = Organization(org_id="co", name="Company")
    org.add_department(Department(dept_id="eng", name="Engineering"))
    org.add_role(Role(
        role_id="vp", name="VP Eng", actor_id="a1", department_id="eng", is_manager=True,
    ))
    org.add_role(Role(role_id="eng", name="Engineer", actor_id="a2", department_id="eng"))
    org.add_reporting_line(ReportingLine(manager_role_id="vp", direct_report_role_id="eng"))
    return org


def test_direct_reports():
    org = _make_two_role_org()
    reports = org.direct_reports("vp")
    assert len(reports) == 1
    assert reports[0].role_id == "eng"


def test_manager_of():
    org = _make_two_role_org()
    mgr = org.manager_of("eng")
    assert mgr is not None
    assert mgr.role_id == "vp"


def test_manager_of_root_returns_none():
    org = _make_two_role_org()
    assert org.manager_of("vp") is None


def test_spans_of_control():
    org = _make_two_role_org()
    spans = org.spans_of_control()
    assert spans.get("vp") == 1


# ---------------------------------------------------------------------------
# OrgUnit / hierarchy projection
# ---------------------------------------------------------------------------


def test_org_units_includes_root():
    org = _make_minimal_org()
    units = org.org_units()
    root = next((u for u in units if u.unit_type == "organization"), None)
    assert root is not None
    assert root.unit_id == "acme"


def test_org_units_includes_department():
    org = _make_minimal_org()
    units = org.org_units()
    dept_unit = next((u for u in units if u.unit_type == "department"), None)
    assert dept_unit is not None
    assert dept_unit.unit_id == "sales"


def test_org_units_includes_team():
    org = _make_minimal_org()
    units = org.org_units()
    team_unit = next((u for u in units if u.unit_type == "team"), None)
    assert team_unit is not None
    assert team_unit.unit_id == "sales-team"


def test_org_unit_parent_chain():
    org = _make_minimal_org()
    units = {u.unit_id: u for u in org.org_units()}
    team_unit = units["sales-team"]
    dept_unit = units[team_unit.parent_id]
    assert dept_unit.unit_type == "department"
    root = units[dept_unit.parent_id]
    assert root.unit_type == "organization"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_passes_for_valid_org():
    org = _make_minimal_org()
    org.validate()


def test_validate_team_unknown_department_raises():
    org = Organization(org_id="o1", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))
    org._teams["t-bad"] = Team(team_id="t-bad", name="Bad", department_id="no-such-dept")
    with pytest.raises(ValueError, match="unknown department"):
        org.validate()


def test_validate_role_unknown_department_raises():
    org = Organization(org_id="o1", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))
    org._roles["r-bad"] = Role(
        role_id="r-bad", name="Bad", actor_id="a1", department_id="no-such-dept",
    )
    with pytest.raises(ValueError, match="unknown department"):
        org.validate()


def test_validate_role_unknown_team_raises():
    org = Organization(org_id="o1", name="O")
    org.add_department(Department(dept_id="d1", name="D1"))
    org._roles["r-bad"] = Role(
        role_id="r-bad", name="Bad", actor_id="a1",
        department_id="d1", team_id="no-such-team",
    )
    with pytest.raises(ValueError, match="unknown team"):
        org.validate()


def test_validate_reporting_line_unknown_manager_raises():
    org = _make_minimal_org()
    org.add_reporting_line(ReportingLine(manager_role_id="no-such", direct_report_role_id="rep"))
    with pytest.raises(ValueError, match="unknown manager role"):
        org.validate()


def test_validate_reporting_line_unknown_report_raises():
    org = _make_minimal_org()
    org.add_reporting_line(ReportingLine(manager_role_id="rep", direct_report_role_id="no-such"))
    with pytest.raises(ValueError, match="unknown direct report role"):
        org.validate()
