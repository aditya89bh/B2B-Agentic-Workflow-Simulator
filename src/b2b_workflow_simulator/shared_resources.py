"""Shared resource model: contention, utilization, and bottleneck detection.

Some resources -- legal reviewers, finance approvers, specialist
consultants, AI platforms, software tools, and external vendors -- are
shared across multiple workflows and departments.  When demand from
several sources exceeds a resource's daily capacity, contention emerges:
cases queue, cycle times stretch, and teams blame each other for delays.

This module models that contention analytically rather than through a
discrete-event simulation: record how many minutes each workflow demands
from each shared resource per day, compare total demand to available
capacity, and surface the resources whose contention ratio exceeds 1.0
(overloaded) or approaches it (at-risk).

Usage pattern::

    pool = SharedResourcePool(org_id="acme")
    pool.add_resource(SharedResource(
        resource_id="legal", name="Legal Reviewer",
        resource_type=LEGAL_REVIEWER,
        capacity_minutes_per_day=240.0, cost_per_use=50.0,
        department_ids=["legal", "sales"],
    ))
    pool.record_usage("legal", "invoice-processing", "finance", 120.0)
    pool.record_usage("legal", "sales-lead-qualification", "sales", 90.0)
    contention = pool.compute_contention("legal")
    print(contention.overload_risk)  # "none" / "moderate" / "high" / "critical"
"""

from __future__ import annotations

from dataclasses import dataclass, field

SPECIALIST = "specialist"
MANAGER = "manager"
LEGAL_REVIEWER = "legal_reviewer"
FINANCE_APPROVER = "finance_approver"
AI_AGENT = "ai_agent"
SOFTWARE_TOOL = "software_tool"
EXTERNAL_VENDOR = "external_vendor"

RESOURCE_TYPES = (
    SPECIALIST,
    MANAGER,
    LEGAL_REVIEWER,
    FINANCE_APPROVER,
    AI_AGENT,
    SOFTWARE_TOOL,
    EXTERNAL_VENDOR,
)

RESOURCE_TYPE_LABELS: dict[str, str] = {
    SPECIALIST: "Specialist",
    MANAGER: "Manager",
    LEGAL_REVIEWER: "Legal Reviewer",
    FINANCE_APPROVER: "Finance Approver",
    AI_AGENT: "AI Agent",
    SOFTWARE_TOOL: "Software Tool",
    EXTERNAL_VENDOR: "External Vendor",
}

_MODERATE_THRESHOLD = 0.7
_HIGH_THRESHOLD = 0.9
_CRITICAL_THRESHOLD = 1.0


@dataclass
class SharedResource:
    """A resource that is shared across multiple workflows or departments.

    Attributes:
        resource_id: Unique identifier.
        name: Human-readable name (e.g. "Senior Legal Counsel").
        resource_type: One of the ``RESOURCE_TYPES`` constants.
        capacity_minutes_per_day: Maximum minutes this resource can work
            in a single day.
        cost_per_use: Incremental cost each time the resource is invoked.
        department_ids: Departments that may claim this resource.  Used as
            metadata only; does not filter contention calculations.
        actor_ids: Workflow actor IDs (from ``Workflow.actors``) whose
            simulation busy-minutes contribute to this resource's demand.
            Used by :meth:`SharedResourcePool.record_usage_from_kpi` to
            automatically derive usage from simulation output.
    """

    resource_id: str
    name: str
    resource_type: str
    capacity_minutes_per_day: float
    cost_per_use: float = 0.0
    department_ids: list[str] = field(default_factory=list)
    actor_ids: list[str] = field(default_factory=list)


@dataclass
class ResourceUsageRecord:
    """One instance of a workflow claiming time from a shared resource.

    Attributes:
        resource_id: The shared resource that was used.
        workflow_id: The workflow that consumed the resource.
        dept_id: The department the workflow belongs to.
        usage_minutes: Minutes of resource time consumed.
    """

    resource_id: str
    workflow_id: str
    dept_id: str
    usage_minutes: float


@dataclass
class ResourceContention:
    """Contention analysis for a single shared resource over a reference period.

    Attributes:
        resource_id: The resource being analyzed.
        resource_name: Human-readable name for display.
        total_demand_minutes: Sum of all recorded usage in the period.
        available_capacity_minutes: Total capacity in the period
            (``capacity_minutes_per_day * days``).
        contention_ratio: ``total_demand_minutes / available_capacity_minutes``.
            Values above 1.0 mean the resource is overloaded.
        requesting_workflow_ids: Distinct workflow IDs that used the
            resource in this period.
    """

    resource_id: str
    resource_name: str
    total_demand_minutes: float
    available_capacity_minutes: float
    contention_ratio: float
    requesting_workflow_ids: list[str]

    @property
    def is_bottleneck(self) -> bool:
        """``True`` when demand exceeds capacity (contention_ratio > 1.0)."""
        return self.contention_ratio > _CRITICAL_THRESHOLD

    @property
    def overload_risk(self) -> str:
        """Qualitative overload risk level.

        Returns one of ``"none"``, ``"moderate"``, ``"high"``, or
        ``"critical"``.
        """
        if self.contention_ratio >= _CRITICAL_THRESHOLD:
            return "critical"
        if self.contention_ratio >= _HIGH_THRESHOLD:
            return "high"
        if self.contention_ratio >= _MODERATE_THRESHOLD:
            return "moderate"
        return "none"

    @property
    def slack_minutes(self) -> float:
        """Unused capacity in the period; negative when overloaded."""
        return self.available_capacity_minutes - self.total_demand_minutes


@dataclass
class SharedResourcePool:
    """Container for all shared resources in an organization.

    Build the pool by calling ``add_resource``, then record demand from
    each workflow via ``record_usage``.  The contention methods then
    aggregate demand vs. capacity to surface bottlenecks.

    Attributes:
        org_id: The organization this pool belongs to.
    """

    org_id: str
    _resources: dict[str, SharedResource] = field(default_factory=dict, repr=False)
    _usage_records: list[ResourceUsageRecord] = field(default_factory=list, repr=False)

    def add_resource(self, resource: SharedResource) -> SharedResourcePool:
        """Register a shared resource and return self."""
        self._resources[resource.resource_id] = resource
        return self

    def record_usage(
        self,
        resource_id: str,
        workflow_id: str,
        dept_id: str,
        usage_minutes: float,
    ) -> None:
        """Record a usage event for a shared resource.

        Args:
            resource_id: The resource consumed.
            workflow_id: The workflow that consumed it.
            dept_id: The department the workflow belongs to.
            usage_minutes: Minutes consumed.

        Raises:
            KeyError: If ``resource_id`` is not registered.
            ValueError: If ``usage_minutes`` is negative.
        """
        if resource_id not in self._resources:
            raise KeyError(f"unknown resource '{resource_id}'")
        if usage_minutes < 0:
            raise ValueError(f"usage_minutes cannot be negative, got {usage_minutes}")
        self._usage_records.append(
            ResourceUsageRecord(
                resource_id=resource_id,
                workflow_id=workflow_id,
                dept_id=dept_id,
                usage_minutes=usage_minutes,
            )
        )

    def resource(self, resource_id: str) -> SharedResource:
        """Return the resource with ``resource_id``, raising ``KeyError`` if unknown."""
        return self._resources[resource_id]

    @property
    def resources(self) -> dict[str, SharedResource]:
        """All registered resources keyed by resource_id."""
        return dict(self._resources)

    @property
    def usage_records(self) -> list[ResourceUsageRecord]:
        """All recorded usage events."""
        return list(self._usage_records)

    def compute_contention(self, resource_id: str, days: int = 1) -> ResourceContention:
        """Compute contention for one resource over ``days`` working days.

        Args:
            resource_id: Resource to analyze.
            days: Reference period in working days (default: 1).

        Returns:
            A :class:`ResourceContention` summarizing demand vs. capacity.

        Raises:
            KeyError: If ``resource_id`` is not registered.
            ValueError: If ``days`` is less than 1.
        """
        if days < 1:
            raise ValueError(f"days must be >= 1, got {days}")
        res = self._resources[resource_id]
        records = [r for r in self._usage_records if r.resource_id == resource_id]
        total_demand = sum(r.usage_minutes for r in records)
        available = res.capacity_minutes_per_day * days
        ratio = total_demand / available if available > 0 else 0.0
        workflow_ids = list({r.workflow_id for r in records})
        return ResourceContention(
            resource_id=resource_id,
            resource_name=res.name,
            total_demand_minutes=total_demand,
            available_capacity_minutes=available,
            contention_ratio=ratio,
            requesting_workflow_ids=workflow_ids,
        )

    def all_contentions(self, days: int = 1) -> list[ResourceContention]:
        """Return contention objects for every registered resource.

        Results are sorted by descending ``contention_ratio`` so the
        most contended resources appear first.
        """
        contentions = [
            self.compute_contention(rid, days) for rid in self._resources
        ]
        return sorted(contentions, key=lambda c: c.contention_ratio, reverse=True)

    def bottleneck_resources(self, days: int = 1) -> list[ResourceContention]:
        """Return only resources where demand exceeds capacity."""
        return [c for c in self.all_contentions(days) if c.is_bottleneck]

    def at_risk_resources(self, days: int = 1) -> list[ResourceContention]:
        """Return resources whose overload_risk is not ``"none"``."""
        return [c for c in self.all_contentions(days) if c.overload_risk != "none"]

    def utilization_by_resource(self, days: int = 1) -> dict[str, float]:
        """Return demand/capacity ratios keyed by resource_id."""
        return {
            rid: self.compute_contention(rid, days).contention_ratio
            for rid in self._resources
        }

    def record_usage_from_kpi(
        self,
        workflow_id: str,
        dept_id: str,
        actor_busy_minutes: dict[str, float],
    ) -> None:
        """Record shared-resource usage from per-actor busy minutes.

        For each registered resource whose ``actor_ids`` intersect with
        ``actor_busy_minutes``, the sum of busy minutes for those actors
        is recorded as usage for that resource.

        Args:
            workflow_id: The workflow whose actor minutes are being processed.
            dept_id: The department that owns the workflow.
            actor_busy_minutes: Mapping of actor_id → busy minutes.  Use
                ``kpi.actor_busy_minutes`` for capacity-aware runs, or derive
                it from ``kpi.node_total_duration_minutes`` via the workflow's
                node→actor mapping for non-capacity-aware runs.
        """
        for resource in self._resources.values():
            if not resource.actor_ids:
                continue
            usage = sum(
                actor_busy_minutes.get(actor_id, 0.0)
                for actor_id in resource.actor_ids
            )
            if usage > 0.0:
                self._usage_records.append(
                    ResourceUsageRecord(
                        resource_id=resource.resource_id,
                        workflow_id=workflow_id,
                        dept_id=dept_id,
                        usage_minutes=usage,
                    )
                )

    def record_usage_from_kpi_results(
        self,
        actor_minutes_by_workflow: dict[str, dict[str, float]],
        dept_id_by_workflow: dict[str, str] | None = None,
    ) -> None:
        """Record usage from multiple actor-minutes mappings at once.

        Args:
            actor_minutes_by_workflow: Mapping of workflow_id →
                (actor_id → busy minutes).
            dept_id_by_workflow: Optional mapping of workflow_id → dept_id.
                If omitted, ``dept_id`` defaults to the workflow_id.
        """
        for workflow_id, actor_minutes in actor_minutes_by_workflow.items():
            dept_id = (
                dept_id_by_workflow.get(workflow_id, workflow_id)
                if dept_id_by_workflow
                else workflow_id
            )
            self.record_usage_from_kpi(workflow_id, dept_id, actor_minutes)


__all__ = [
    "AI_AGENT",
    "EXTERNAL_VENDOR",
    "FINANCE_APPROVER",
    "LEGAL_REVIEWER",
    "MANAGER",
    "RESOURCE_TYPE_LABELS",
    "RESOURCE_TYPES",
    "ResourceContention",
    "ResourceUsageRecord",
    "SharedResource",
    "SharedResourcePool",
    "SOFTWARE_TOOL",
    "SPECIALIST",
]
