"""Tests for shared_resources: SharedResource, ResourceContention, SharedResourcePool."""

from __future__ import annotations

import pytest

from b2b_workflow_simulator.shared_resources import (
    AI_AGENT,
    EXTERNAL_VENDOR,
    FINANCE_APPROVER,
    LEGAL_REVIEWER,
    MANAGER,
    RESOURCE_TYPE_LABELS,
    RESOURCE_TYPES,
    SOFTWARE_TOOL,
    SPECIALIST,
    ResourceContention,
    SharedResource,
    SharedResourcePool,
)

# ---------------------------------------------------------------------------
# SharedResource
# ---------------------------------------------------------------------------


def test_shared_resource_fields():
    res = SharedResource(
        resource_id="legal",
        name="Legal Reviewer",
        resource_type=LEGAL_REVIEWER,
        capacity_minutes_per_day=240.0,
        cost_per_use=150.0,
        department_ids=["legal", "finance"],
    )
    assert res.resource_id == "legal"
    assert res.capacity_minutes_per_day == 240.0
    assert res.cost_per_use == 150.0
    assert "legal" in res.department_ids


def test_shared_resource_defaults():
    res = SharedResource(
        resource_id="tool",
        name="Tool",
        resource_type=SOFTWARE_TOOL,
        capacity_minutes_per_day=480.0,
    )
    assert res.cost_per_use == 0.0
    assert res.department_ids == []


# ---------------------------------------------------------------------------
# ResourceContention
# ---------------------------------------------------------------------------


def test_contention_is_bottleneck_false():
    c = ResourceContention(
        resource_id="r1", resource_name="R1",
        total_demand_minutes=100.0, available_capacity_minutes=200.0,
        contention_ratio=0.5, requesting_workflow_ids=["wf-1"],
    )
    assert not c.is_bottleneck


def test_contention_is_bottleneck_true():
    c = ResourceContention(
        resource_id="r1", resource_name="R1",
        total_demand_minutes=300.0, available_capacity_minutes=200.0,
        contention_ratio=1.5, requesting_workflow_ids=["wf-1"],
    )
    assert c.is_bottleneck


def test_contention_overload_risk_none():
    c = ResourceContention("r", "R", 50.0, 200.0, 0.25, [])
    assert c.overload_risk == "none"


def test_contention_overload_risk_moderate():
    c = ResourceContention("r", "R", 150.0, 200.0, 0.75, [])
    assert c.overload_risk == "moderate"


def test_contention_overload_risk_high():
    c = ResourceContention("r", "R", 190.0, 200.0, 0.95, [])
    assert c.overload_risk == "high"


def test_contention_overload_risk_critical():
    c = ResourceContention("r", "R", 250.0, 200.0, 1.25, [])
    assert c.overload_risk == "critical"


def test_contention_slack_positive():
    c = ResourceContention("r", "R", 100.0, 200.0, 0.5, [])
    assert c.slack_minutes == pytest.approx(100.0)


def test_contention_slack_negative_when_overloaded():
    c = ResourceContention("r", "R", 300.0, 200.0, 1.5, [])
    assert c.slack_minutes == pytest.approx(-100.0)


# ---------------------------------------------------------------------------
# SharedResourcePool
# ---------------------------------------------------------------------------


def _make_pool() -> SharedResourcePool:
    pool = SharedResourcePool(org_id="acme")
    pool.add_resource(SharedResource(
        resource_id="legal",
        name="Legal Reviewer",
        resource_type=LEGAL_REVIEWER,
        capacity_minutes_per_day=240.0,
    ))
    pool.add_resource(SharedResource(
        resource_id="finance",
        name="Finance Approver",
        resource_type=FINANCE_APPROVER,
        capacity_minutes_per_day=120.0,
    ))
    return pool


def test_pool_add_resource():
    pool = _make_pool()
    assert "legal" in pool.resources
    assert "finance" in pool.resources


def test_pool_record_usage():
    pool = _make_pool()
    pool.record_usage("legal", "wf-sales", "sales", 60.0)
    assert len(pool.usage_records) == 1


def test_pool_record_usage_unknown_resource_raises():
    pool = _make_pool()
    with pytest.raises(KeyError):
        pool.record_usage("unknown-res", "wf-1", "d1", 10.0)


def test_pool_record_usage_negative_raises():
    pool = _make_pool()
    with pytest.raises(ValueError, match="negative"):
        pool.record_usage("legal", "wf-1", "d1", -10.0)


def test_pool_compute_contention_no_usage():
    pool = _make_pool()
    c = pool.compute_contention("legal")
    assert c.contention_ratio == 0.0
    assert c.total_demand_minutes == 0.0


def test_pool_compute_contention_with_usage():
    pool = _make_pool()
    pool.record_usage("legal", "wf-1", "d1", 120.0)
    c = pool.compute_contention("legal")
    assert c.contention_ratio == pytest.approx(0.5)
    assert c.resource_name == "Legal Reviewer"


def test_pool_compute_contention_overloaded():
    pool = _make_pool()
    pool.record_usage("finance", "wf-1", "d1", 200.0)
    c = pool.compute_contention("finance")
    assert c.is_bottleneck


def test_pool_compute_contention_multi_day():
    pool = _make_pool()
    pool.record_usage("legal", "wf-1", "d1", 120.0)
    c = pool.compute_contention("legal", days=2)
    assert c.available_capacity_minutes == pytest.approx(480.0)
    assert c.contention_ratio == pytest.approx(120.0 / 480.0)


def test_pool_compute_contention_invalid_days_raises():
    pool = _make_pool()
    with pytest.raises(ValueError, match="days"):
        pool.compute_contention("legal", days=0)


def test_pool_compute_contention_unknown_resource_raises():
    pool = _make_pool()
    with pytest.raises(KeyError):
        pool.compute_contention("unknown-res")


def test_pool_all_contentions_sorted_by_ratio():
    pool = _make_pool()
    pool.record_usage("finance", "wf-1", "d1", 100.0)
    pool.record_usage("legal", "wf-2", "d2", 10.0)
    contentions = pool.all_contentions()
    assert len(contentions) == 2
    assert contentions[0].contention_ratio >= contentions[1].contention_ratio


def test_pool_bottleneck_resources_empty_when_none_overloaded():
    pool = _make_pool()
    pool.record_usage("legal", "wf-1", "d1", 50.0)
    assert pool.bottleneck_resources() == []


def test_pool_bottleneck_resources_found():
    pool = _make_pool()
    pool.record_usage("finance", "wf-1", "d1", 200.0)
    bottlenecks = pool.bottleneck_resources()
    assert any(b.resource_id == "finance" for b in bottlenecks)


def test_pool_at_risk_resources():
    pool = _make_pool()
    pool.record_usage("legal", "wf-1", "d1", 200.0)
    at_risk = pool.at_risk_resources()
    assert len(at_risk) > 0


def test_pool_utilization_by_resource():
    pool = _make_pool()
    pool.record_usage("legal", "wf-1", "d1", 120.0)
    utils = pool.utilization_by_resource()
    assert "legal" in utils
    assert utils["legal"] == pytest.approx(0.5)


def test_pool_requesting_workflow_ids():
    pool = _make_pool()
    pool.record_usage("legal", "wf-1", "d1", 60.0)
    pool.record_usage("legal", "wf-2", "d2", 60.0)
    c = pool.compute_contention("legal")
    assert set(c.requesting_workflow_ids) == {"wf-1", "wf-2"}


def test_resource_types_constant():
    all_types = (
        SPECIALIST, MANAGER, LEGAL_REVIEWER, FINANCE_APPROVER,
        AI_AGENT, SOFTWARE_TOOL, EXTERNAL_VENDOR,
    )
    for rt in all_types:
        assert rt in RESOURCE_TYPES


def test_resource_type_labels_complete():
    for rt in RESOURCE_TYPES:
        assert rt in RESOURCE_TYPE_LABELS


def test_pool_resource_accessor():
    pool = _make_pool()
    res = pool.resource("legal")
    assert res.name == "Legal Reviewer"


def test_pool_resource_unknown_raises():
    pool = _make_pool()
    with pytest.raises(KeyError):
        pool.resource("no-such")
