# Shared Resources

`shared_resources.py` models resources that are shared across multiple workflows
and departments — legal reviewers, finance approvers, AI platforms, software
tools, and external vendors.  When demand from several workflows exceeds a
resource's daily capacity, contention emerges and `overload_risk` surfaces it.

## Resource types

| Constant | Label |
|---|---|
| `SPECIALIST` | Specialist |
| `MANAGER` | Manager |
| `LEGAL_REVIEWER` | Legal Reviewer |
| `FINANCE_APPROVER` | Finance Approver |
| `AI_AGENT` | AI Agent |
| `SOFTWARE_TOOL` | Software Tool |
| `EXTERNAL_VENDOR` | External Vendor |

## Building a shared resource pool

```python
from b2b_workflow_simulator.shared_resources import (
    LEGAL_REVIEWER, SOFTWARE_TOOL,
    SharedResource, SharedResourcePool,
)

pool = SharedResourcePool(org_id="acme")
pool.add_resource(SharedResource(
    resource_id="legal",
    name="Senior Legal Counsel",
    resource_type=LEGAL_REVIEWER,
    capacity_minutes_per_day=240.0,   # 4 hours/day available
    cost_per_use=150.0,
    department_ids=["legal", "sales", "finance"],
))
pool.add_resource(SharedResource(
    resource_id="crm",
    name="CRM System",
    resource_type=SOFTWARE_TOOL,
    capacity_minutes_per_day=2880.0,
))
```

## Recording usage and computing contention

```python
# Simulate demand from each workflow
pool.record_usage("legal", "invoice-processing",        "finance", 120.0)
pool.record_usage("legal", "sales-lead-qualification",  "sales",   90.0)

# Contention for a single resource
c = pool.compute_contention("legal")
print(f"Contention ratio: {c.contention_ratio:.2f}")
print(f"Overload risk:    {c.overload_risk}")  # "none" / "moderate" / "high" / "critical"
print(f"Is bottleneck:    {c.is_bottleneck}")  # True when ratio > 1.0
print(f"Slack minutes:    {c.slack_minutes:.0f}")

# All resources sorted by contention
for contention in pool.all_contentions():
    print(f"{contention.resource_name}: {contention.contention_ratio:.2f}")

# Only bottleneck resources
bottlenecks = pool.bottleneck_resources()
```

## Overload risk thresholds

| Risk level | Contention ratio |
|---|---|
| `"none"` | < 0.70 |
| `"moderate"` | 0.70 – 0.89 |
| `"high"` | 0.90 – 0.99 |
| `"critical"` | ≥ 1.00 (demand exceeds capacity) |

## Bundled example

`b2b_workflow_simulator.examples.saas_org.build_saas_shared_resources()` returns
a `SharedResourcePool` with eight pre-configured resources for the B2B SaaS
example company.  Use `pool.record_usage(...)` after running simulations to load
it with demand data.
