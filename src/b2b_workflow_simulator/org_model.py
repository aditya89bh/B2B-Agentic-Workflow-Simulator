"""Organizational model: hierarchy, departments, teams, roles, and reporting lines.

The org model is the Phase 6 foundation that gives every workflow a home
inside a real organizational structure.  A `Workflow` already models
*what* work is done and *who* (actors) does each step; `Organization`
answers the broader questions: which department owns the workflow, which
team of people execute it, who manages whom, and how headcount is
distributed across the business.

This module is deliberately read-only after construction: you build an
`Organization` by calling `add_*` methods, then pass it to simulation or
analysis functions.  No mutation happens during a simulation run, which
makes the model safe to share across concurrent analyses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Role:
    """A named function that a person or AI agent fills in the organization.

    A `Role` is the join between an organizational position (e.g.
    "Sales Manager") and the simulation actor (`actor_id`) that fills it.
    It also records which department and team the role belongs to, and
    whether the role holder is a manager or an AI agent.

    Attributes:
        role_id: Unique identifier for this role.
        name: Human-readable role title.
        actor_id: The workflow actor (HumanActor or AIAgentActor) that
            fills this role.
        department_id: The department this role belongs to.
        team_id: The team this role belongs to, or ``None`` if the role
            is at department level.
        is_manager: Whether this role has direct reports.
        is_ai_agent: Whether the actor filling this role is an AI agent.
    """

    role_id: str
    name: str
    actor_id: str
    department_id: str
    team_id: str | None = None
    is_manager: bool = False
    is_ai_agent: bool = False


@dataclass
class ReportingLine:
    """A directed reporting relationship between two roles.

    Attributes:
        manager_role_id: The role of the manager.
        direct_report_role_id: The role that reports to the manager.
    """

    manager_role_id: str
    direct_report_role_id: str


@dataclass
class OrgUnit:
    """A lightweight node in the organizational hierarchy tree.

    `OrgUnit` objects are produced by `Organization.org_units()` and
    represent departments, teams, or the root organization as nodes in a
    traversable tree.  They are read-only projections -- mutating them
    does not affect the underlying `Organization`.

    Attributes:
        unit_id: Unique identifier matching the underlying entity's id.
        name: Human-readable name.
        unit_type: One of ``"organization"``, ``"department"``, or
            ``"team"``.
        parent_id: The ``unit_id`` of the parent unit, or ``None`` for
            the root.
        children_ids: ``unit_id`` values of direct children.
    """

    unit_id: str
    name: str
    unit_type: str
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)


@dataclass
class Team:
    """A named group of people within a department that executes workflows.

    Attributes:
        team_id: Unique identifier.
        name: Human-readable team name.
        department_id: The department this team belongs to.
        role_ids: Roles assigned to this team (populated via
            ``add_role``).
        workflow_ids: Workflows this team participates in (populated via
            ``add_workflow``).
    """

    team_id: str
    name: str
    department_id: str
    role_ids: list[str] = field(default_factory=list)
    workflow_ids: list[str] = field(default_factory=list)

    def add_role(self, role_id: str) -> Team:
        """Add a role to this team and return self for chaining."""
        if role_id not in self.role_ids:
            self.role_ids.append(role_id)
        return self

    def add_workflow(self, workflow_id: str) -> Team:
        """Associate a workflow with this team and return self for chaining."""
        if workflow_id not in self.workflow_ids:
            self.workflow_ids.append(workflow_id)
        return self


@dataclass
class Department:
    """An organizational department containing teams and owning workflows.

    Attributes:
        dept_id: Unique identifier.
        name: Human-readable department name.
        team_ids: Teams that belong to this department.
        workflow_ids: Workflows owned by this department.
    """

    dept_id: str
    name: str
    team_ids: list[str] = field(default_factory=list)
    workflow_ids: list[str] = field(default_factory=list)

    def add_team(self, team_id: str) -> Department:
        """Add a team to this department and return self for chaining."""
        if team_id not in self.team_ids:
            self.team_ids.append(team_id)
        return self

    def add_workflow(self, workflow_id: str) -> Department:
        """Associate a workflow with this department and return self."""
        if workflow_id not in self.workflow_ids:
            self.workflow_ids.append(workflow_id)
        return self


@dataclass
class Organization:
    """The top-level organizational container.

    An `Organization` holds departments, teams, roles, and reporting
    lines, and records which workflow IDs are in scope.  The model is
    purely structural -- it does not execute simulations itself.  Pass
    it to `CrossWorkflowSimulator`, `compute_org_health`, or the Phase 6
    CLI commands to drive analysis.

    Attributes:
        org_id: Stable, unique identifier.
        name: Human-readable organization name.
    """

    org_id: str
    name: str
    _departments: dict[str, Department] = field(default_factory=dict, repr=False)
    _teams: dict[str, Team] = field(default_factory=dict, repr=False)
    _roles: dict[str, Role] = field(default_factory=dict, repr=False)
    _reporting_lines: list[ReportingLine] = field(default_factory=list, repr=False)
    _workflow_ids: list[str] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------
    # Mutation helpers (fluent API, return self for chaining)
    # ------------------------------------------------------------------

    def add_department(self, dept: Department) -> Organization:
        """Register a department and return self."""
        self._departments[dept.dept_id] = dept
        return self

    def add_team(self, team: Team) -> Organization:
        """Register a team and return self."""
        self._teams[team.team_id] = team
        return self

    def add_role(self, role: Role) -> Organization:
        """Register a role and return self."""
        self._roles[role.role_id] = role
        return self

    def add_reporting_line(self, line: ReportingLine) -> Organization:
        """Register a reporting relationship and return self."""
        self._reporting_lines.append(line)
        return self

    def add_workflow_id(self, workflow_id: str) -> Organization:
        """Record a workflow as belonging to this organization."""
        if workflow_id not in self._workflow_ids:
            self._workflow_ids.append(workflow_id)
        return self

    # ------------------------------------------------------------------
    # Read-only property accessors
    # ------------------------------------------------------------------

    @property
    def departments(self) -> dict[str, Department]:
        return dict(self._departments)

    @property
    def teams(self) -> dict[str, Team]:
        return dict(self._teams)

    @property
    def roles(self) -> dict[str, Role]:
        return dict(self._roles)

    @property
    def reporting_lines(self) -> list[ReportingLine]:
        return list(self._reporting_lines)

    @property
    def workflow_ids(self) -> list[str]:
        return list(self._workflow_ids)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_department(self, dept_id: str) -> Department:
        """Return the department with ``dept_id``, raising ``KeyError`` if unknown."""
        return self._departments[dept_id]

    def get_team(self, team_id: str) -> Team:
        """Return the team with ``team_id``, raising ``KeyError`` if unknown."""
        return self._teams[team_id]

    def get_role(self, role_id: str) -> Role:
        """Return the role with ``role_id``, raising ``KeyError`` if unknown."""
        return self._roles[role_id]

    def teams_for_department(self, dept_id: str) -> list[Team]:
        """Return all teams that belong to the given department."""
        return [t for t in self._teams.values() if t.department_id == dept_id]

    def roles_for_team(self, team_id: str) -> list[Role]:
        """Return all roles assigned to the given team."""
        return [r for r in self._roles.values() if r.team_id == team_id]

    def roles_for_department(self, dept_id: str) -> list[Role]:
        """Return all roles in the given department (across all teams)."""
        return [r for r in self._roles.values() if r.department_id == dept_id]

    def direct_reports(self, role_id: str) -> list[Role]:
        """Return all roles that directly report to ``role_id``."""
        report_ids = {
            line.direct_report_role_id
            for line in self._reporting_lines
            if line.manager_role_id == role_id
        }
        return [self._roles[rid] for rid in report_ids if rid in self._roles]

    def manager_of(self, role_id: str) -> Role | None:
        """Return the role that ``role_id`` reports to, or ``None``."""
        for line in self._reporting_lines:
            if line.direct_report_role_id == role_id:
                mgr_id = line.manager_role_id
                return self._roles.get(mgr_id)
        return None

    def department_headcount(self, dept_id: str) -> int:
        """Count roles (people/agents) in the given department."""
        return sum(1 for r in self._roles.values() if r.department_id == dept_id)

    def total_headcount(self) -> int:
        """Total number of roles across the entire organization."""
        return len(self._roles)

    def ai_agent_count(self) -> int:
        """Total number of AI agent roles in the organization."""
        return sum(1 for r in self._roles.values() if r.is_ai_agent)

    def manager_count(self) -> int:
        """Total number of manager roles in the organization."""
        return sum(1 for r in self._roles.values() if r.is_manager)

    # ------------------------------------------------------------------
    # Hierarchy projection
    # ------------------------------------------------------------------

    def org_units(self) -> list[OrgUnit]:
        """Return a flat list of OrgUnit objects representing the hierarchy.

        The list always starts with a root unit for the organization
        itself, followed by department units (children of root), then
        team units (children of their department).
        """
        root = OrgUnit(
            unit_id=self.org_id,
            name=self.name,
            unit_type="organization",
            parent_id=None,
            children_ids=list(self._departments),
        )
        units: list[OrgUnit] = [root]
        for dept in self._departments.values():
            units.append(
                OrgUnit(
                    unit_id=dept.dept_id,
                    name=dept.name,
                    unit_type="department",
                    parent_id=self.org_id,
                    children_ids=list(dept.team_ids),
                )
            )
        for team in self._teams.values():
            units.append(
                OrgUnit(
                    unit_id=team.team_id,
                    name=team.name,
                    unit_type="team",
                    parent_id=team.department_id,
                    children_ids=[],
                )
            )
        return units

    def spans_of_control(self) -> dict[str, int]:
        """Return a mapping of manager role_id -> number of direct reports."""
        spans: dict[str, int] = {}
        for line in self._reporting_lines:
            spans[line.manager_role_id] = spans.get(line.manager_role_id, 0) + 1
        return spans

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Raise ``ValueError`` if the organization is structurally inconsistent.

        Checks performed:

        - Every team's ``department_id`` refers to a known department.
        - Every role's ``department_id`` refers to a known department.
        - Every role's ``team_id`` (when set) refers to a known team.
        - Every reporting line references known role IDs.
        """
        for team in self._teams.values():
            if team.department_id not in self._departments:
                raise ValueError(
                    f"team '{team.team_id}' references unknown department "
                    f"'{team.department_id}'"
                )
        for role in self._roles.values():
            if role.department_id not in self._departments:
                raise ValueError(
                    f"role '{role.role_id}' references unknown department "
                    f"'{role.department_id}'"
                )
            if role.team_id is not None and role.team_id not in self._teams:
                raise ValueError(
                    f"role '{role.role_id}' references unknown team '{role.team_id}'"
                )
        for line in self._reporting_lines:
            if line.manager_role_id not in self._roles:
                raise ValueError(
                    f"reporting line references unknown manager role "
                    f"'{line.manager_role_id}'"
                )
            if line.direct_report_role_id not in self._roles:
                raise ValueError(
                    f"reporting line references unknown direct report role "
                    f"'{line.direct_report_role_id}'"
                )


__all__ = [
    "Department",
    "Organization",
    "OrgUnit",
    "ReportingLine",
    "Role",
    "Team",
]
