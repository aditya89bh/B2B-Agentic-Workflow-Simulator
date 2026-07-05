# Business Policy Engine

Everything so far answers "what happens" when a workflow runs. `policy.py`
answers a different question: "is what happens actually allowed to happen
this way?" A policy is a governance rule -- an approval gate, a routing
restriction, an escalation requirement, a retry safety net, a business-hours
constraint, a mandatory human review, or a separation-of-duties rule --
attached to a `Workflow` and checked against its *structure*, independent of
running any simulation.

## Policy types

`evaluate_policies(workflow, policies)` accepts a list of any of the
following frozen dataclasses, each modeling one kind of governance rule:

- **`ApprovalPolicy`** -- `target_node_id` must not be reachable without
  first passing through at least one of `required_before_node_ids`. Models
  rules like "a payment cannot be scheduled without first passing through
  approval."
- **`RoutingPolicy`** -- restricts which nodes are allowed to directly
  follow `node_id`, flagging any outgoing edge that leads somewhere not on
  the allowed list.
- **`EscalationPolicy`** -- requires an AI-operated node to have a reachable
  human (or human-team-pool) escalation path, so an automated step can never
  strand a case with no human able to intervene.
- **`RetryPolicy`** -- if `node_id` participates in a retry loop, the loop
  must have at least one edge leaving it; otherwise a case could retry
  forever with no way out. `max_attempts` is recorded on the policy for
  reporting purposes.
- **`BusinessHoursPolicy`** -- every `Worker` shift assigned to a pooled
  node must fall within `allowed_start_hour`/`allowed_end_hour`.
- **`MandatoryHumanReviewPolicy`** -- `node_id` must be assigned to a human
  actor or a team pool, never an AI agent alone.
- **`SeparationOfDutiesPolicy`** -- two named nodes must be performed by
  different actors, so the same person or agent cannot both originate and
  approve the same case.

```python
from b2b_workflow_simulator.policy import (
    ApprovalPolicy,
    SeparationOfDutiesPolicy,
    evaluate_policies,
    generate_policy_report,
)

policies = [
    ApprovalPolicy(
        name="erp-entry-requires-approval",
        target_node_id="erp_entry",
        required_before_node_ids=("approval",),
        description="Invoices must be approved before being posted to the ERP.",
    ),
    SeparationOfDutiesPolicy(
        name="validation-approval-segregation",
        node_id_a="validation",
        node_id_b="approval",
        description="Whoever validates an invoice must not also approve it.",
    ),
]

evaluation = evaluate_policies(workflow, policies)
print(generate_policy_report(evaluation))
```

From the CLI:

```bash
b2b-simulator policy-analysis invoice-processing --variant after
b2b-simulator policy-analysis invoice-processing --variant after --html-output policy.html
```

## Violations and evaluation results

`evaluate_policies` returns a `PolicyEvaluation`: the workflow name, how
many policies were checked, and a list of `PolicyViolation` records, each
carrying the offending policy's name and kind, the node involved (if any), a
severity (`"error"` or `"warning"`), and a human-readable description.
`PolicyEvaluation.is_compliant`, `.violation_count`, `.error_count`, and
`.warning_count` are computed properties, so there is exactly one source of
truth for whether a workflow passes.

Most violations are errors; `BusinessHoursPolicy` violations are warnings,
reflecting that a shift falling slightly outside a preferred window is
usually a scheduling inconvenience rather than a hard compliance failure --
the caller can still decide to treat any warning as blocking by checking
`warning_count` directly.

## Attaching policies to tasks vs. workflows

A policy set is just a plain Python list, so "attaching" a policy to a
single task is simply constructing a policy that targets that task's
`node_id`, and "attaching" it to the whole workflow is including it in the
list passed to `evaluate_policies`. There is no separate workflow-level vs.
task-level policy object: `ApprovalPolicy`, `EscalationPolicy`,
`RetryPolicy`, `BusinessHoursPolicy`, `MandatoryHumanReviewPolicy`, and
`SeparationOfDutiesPolicy` all reference specific node IDs already, and a
`RoutingPolicy` is inherently node-scoped since it restricts one node's
outgoing edges. This keeps the policy model as data, mirroring how
`Workflow` itself is represented, and means policy sets can be built,
combined, and reused across workflow variants exactly like the bundled
`examples/governance.py` definitions do for the "before" and "after"
variants of each example.

## Worked example: catching a segregation-of-duties gap introduced by a redesign

The bundled invoice processing example's "after" (AI-augmented) variant
assigns both `approval` and `erp_entry` to the same `approval_agent` actor
-- a segregation-of-duties gap that did not exist in the "before" (manual)
variant, where a Controller approved and a separate ERP entry step posted
the transaction:

```bash
b2b-simulator policy-analysis invoice-processing --variant before   # no violations
b2b-simulator policy-analysis invoice-processing --variant after    # flags nothing new here...
```

The policy set does not currently include a duties check between those two
specific nodes (that check lives in the compliance engine instead -- see
`docs/compliance.md`), which is itself a useful illustration of the
difference between the two engines: `policy.py` encodes internal governance
rules the organization chooses to enforce, while `compliance.py` encodes
regulatory/audit obligations that exist independent of any single
organization's preferences. The same `Workflow` can, and often should, be
checked against both.

## What this model does not do

- It does not check runtime behavior (an `ApprovalPolicy` verifies a graph
  path exists, not that every simulated case actually took it -- for that,
  see the SLA engine's event-log replay in `docs/sla_modeling.md`).
- It does not resolve conflicting policies (if two policies disagree, both
  sets of violations are reported; reconciling them is left to the caller).
- It does not persist policy sets as JSON alongside workflow definitions
  (policies are plain Python dataclasses, so they serialize with the
  standard library the same way workflows do, but no dedicated
  `policy_io.py` exists yet).
