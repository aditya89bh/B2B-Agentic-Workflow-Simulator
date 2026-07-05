# Compliance Engine

`policy.py` (see `docs/policy_engine.md`) encodes rules an organization
chooses to enforce internally. `compliance.py` encodes obligations that
exist independent of any one organization's preferences: regulatory
requirements like GDPR-style consent gates, audit trail obligations,
financial approval chains, segregation of duties for SOX-style controls,
mandatory documentation, record retention, and regulatory checkpoints.
`evaluate_compliance` checks a workflow against a set of these requirements
and produces both hard violations and informational audit findings.

## Requirement types

`evaluate_compliance(workflow, requirements)` accepts a list of any of the
following frozen dataclasses:

- **`GDPRApprovalRequirement`** -- a node that processes personal data
  (`personal_data_node_id`) must be reachable only after passing through at
  least one of `consent_node_ids`.
- **`AuditRequirement`** -- a node must carry the metadata fields listed in
  `required_metadata_keys` (if any); regardless of pass/fail, every audit
  requirement also produces an `AuditFinding` documenting that the node's
  executions are captured in the event log.
- **`FinancialApprovalChainRequirement`** -- a sequence of distinct approval
  checkpoints (`approval_chain_node_ids`) must each be able to reach the
  next, in order, before the final financial action node.
- **`SegregationOfDutiesRequirement`** -- two named nodes must be performed
  by different actors. This is deliberately a separate requirement type
  from `policy.py`'s `SeparationOfDutiesPolicy`: the same structural check
  can be a business policy an organization sets for itself, a regulatory
  control it must demonstrate to an auditor, or both at once.
- **`MandatoryDocumentationRequirement`** -- a node must carry specific
  business documentation metadata fields (e.g. call notes, budget
  confirmation), distinct from `AuditRequirement`'s audit-trail framing.
- **`RecordRetentionRequirement`** -- flags that records produced at a node
  must be retained for `retention_days`; always produces an `AuditFinding`,
  never a violation, since retention is a forward-looking obligation rather
  than something the workflow's structure can violate today.
- **`RegulatoryCheckpointRequirement`** -- flags a node as reviewed under a
  named regulation (`regulation_reference`); like record retention, this
  always produces an `AuditFinding`.

```python
from b2b_workflow_simulator.compliance import (
    AuditRequirement,
    FinancialApprovalChainRequirement,
    SegregationOfDutiesRequirement,
    evaluate_compliance,
    generate_compliance_report,
)

requirements = [
    FinancialApprovalChainRequirement(
        name="payment-approval-chain",
        node_id="payment_scheduling",
        approval_chain_node_ids=("validation", "approval"),
        description="Payments must be gated by validation, then approval, in order.",
    ),
    SegregationOfDutiesRequirement(
        name="posting-approval-segregation",
        node_id_a="approval",
        node_id_b="erp_entry",
        description="Approving and posting an invoice should not rest with one actor.",
    ),
    AuditRequirement(
        name="approval-audit-trail",
        node_id="approval",
        description="Every approval decision must be reconstructable from the event log.",
    ),
]

report = evaluate_compliance(workflow, requirements)
print(generate_compliance_report(report))
```

From the CLI:

```bash
b2b-simulator compliance-analysis invoice-processing --variant after
b2b-simulator compliance-analysis invoice-processing --variant after --html-output compliance.html
```

## Violations, compliance score, and audit findings

`evaluate_compliance` returns a `ComplianceReport`: the workflow name, the
number of requirements checked, a list of `ComplianceViolation` records
(requirement name/kind, node, and description), and a list of `AuditFinding`
records (informational observations, independent of pass/fail).

`ComplianceReport.compliance_score` is the percentage of *distinct*
requirements with zero violations -- not the percentage of individual
violation instances, so one requirement producing several violations still
only counts as one failing requirement out of the total checked. This
matches how a compliance officer would actually score a workflow: "how many
of our obligations are met," not "how many things technically went wrong."

## Worked example: exposing a real segregation-of-duties gap

The bundled invoice processing example's "after" (AI-augmented) variant
assigns both the `approval` and `erp_entry` nodes to the same
`approval_agent` actor. The "before" (manual) variant used a distinct
Controller and ERP-entry step, so this gap is a direct side effect of the
redesign, not a pre-existing issue:

```bash
b2b-simulator compliance-analysis invoice-processing --variant before   # 100% compliance score
b2b-simulator compliance-analysis invoice-processing --variant after    # flags the SoD gap
```

The "after" run reports a `SegregationOfDutiesRequirement` violation and a
compliance score below 100%, which is exactly the kind of regression a
transformation program needs surfaced *before* rollout: an AI redesign that
looks like a clear efficiency win on cost and cycle time can simultaneously
introduce a control weakness that a pure KPI comparison would never catch,
since `compare_workflows()` has no concept of compliance at all. Running
both engines side by side on the same redesign is how the executive report
(`docs/ai_adoption.md`, `executive-report`) combines a favorable ROI with an
honest compliance caveat instead of an incomplete recommendation.

## What this model does not do

- It does not verify compliance against real simulated case data (like
  `policy.py`, every check here is structural -- it verifies a compliant
  *path* exists, not that every case took it; see `docs/sla_modeling.md`
  for the event-log-based counterpart).
- It does not map requirements to specific named regulations beyond the
  free-text `regulation_reference` field -- there is no built-in GDPR/SOX/
  HIPAA rule library, since the specific obligations that apply vary by
  jurisdiction, industry, and organization.
- It does not track compliance drift over time (each `evaluate_compliance`
  call is a point-in-time snapshot; comparing snapshots across workflow
  revisions is left to the caller, the same way `compare_workflows()`
  compares two `KPIResult` snapshots rather than tracking history itself).
