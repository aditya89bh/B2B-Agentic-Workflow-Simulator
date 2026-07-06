# Organization Model

Phase 6 introduces the organizational digital twin layer.  Where Phase 1–5
simulated individual workflows in isolation, `org_model` gives every workflow a
home inside a real organizational hierarchy: departments, teams, roles, and
reporting lines.

## Core concepts

| Class | Purpose |
|---|---|
| `Organization` | Top-level container; holds all departments, teams, roles, and workflow IDs |
| `Department` | A named business unit (e.g. "Finance"); owns teams and workflows |
| `Team` | A group within a department that executes specific workflows |
| `Role` | Links a workflow actor (`actor_id`) to a department/team position |
| `ReportingLine` | Directed manager → direct-report relationship between two roles |
| `OrgUnit` | Read-only tree node produced by `org.org_units()` for hierarchy traversal |

## Building an organization

```python
from b2b_workflow_simulator.org_model import (
    Department, Organization, ReportingLine, Role, Team,
)

org = Organization(org_id="acme", name="Acme Corp")

# 1. Add departments
sales = Department(dept_id="sales", name="Sales")
finance = Department(dept_id="finance", name="Finance")
org.add_department(sales).add_department(finance)

# 2. Add teams (each team must reference a known department)
sales_team = Team(team_id="sales-dev", name="Sales Dev Team", department_id="sales")
org.add_team(sales_team)
sales.add_team("sales-dev")

# 3. Add roles (reference a workflow actor_id)
rep = Role(role_id="rep", name="Account Executive",
           actor_id="sales-rep", department_id="sales", team_id="sales-dev")
manager = Role(role_id="vp", name="VP Sales",
               actor_id="vp-actor", department_id="sales",
               team_id="sales-dev", is_manager=True)
org.add_role(rep).add_role(manager)

# 4. Add reporting lines
org.add_reporting_line(ReportingLine(
    manager_role_id="vp", direct_report_role_id="rep"
))

# 5. Register workflow IDs that belong to this org
org.add_workflow_id("sales-lead-qualification")

# 6. Validate structure
org.validate()
```

## Querying the hierarchy

```python
# Teams in a department
teams = org.teams_for_department("sales")

# Roles in a team
roles = org.roles_for_team("sales-dev")

# Manager lookup
mgr = org.manager_of("rep")  # returns the Role for "vp"

# Direct reports
reports = org.direct_reports("vp")  # [Role("rep")]

# Headcount
print(org.total_headcount())       # total roles
print(org.department_headcount("sales"))
print(org.ai_agent_count())        # roles with is_ai_agent=True
print(org.manager_count())

# Span of control
spans = org.spans_of_control()     # {role_id: n_direct_reports}
```

## Hierarchy projection

`org.org_units()` returns a flat list of `OrgUnit` objects representing the
tree.  Each unit has a `unit_type` (`"organization"`, `"department"`, or
`"team"`), a `parent_id`, and a `children_ids` list.

```python
for unit in org.org_units():
    indent = "  " if unit.unit_type == "department" else "    "
    print(f"{indent}{unit.name} ({unit.unit_type})")
```

## Bundled example

`b2b_workflow_simulator.examples.saas_org.build_saas_org()` returns a
pre-built B2B SaaS company with six departments (Sales, Customer Success,
Finance, Legal, Operations, AI Transformation Office), six teams, 18 roles,
and the three standard workflow examples already wired in.
