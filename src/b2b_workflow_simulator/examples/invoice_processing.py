"""Example workflow: B2B invoice processing (accounts payable), before and after AI adoption.

This example models a standard accounts payable process:

    Invoice Intake -> Validation -> Approval -> ERP Entry -> Payment Scheduling
                             \\           \\-> Approval Delay (exception)
                              \\-> Missing PO / Mismatched Amount / Vendor Data Issue

The "before" variant staffs every stage with an AP Clerk and a Controller.
The "after" variant (added separately) introduces AI agents for intake,
validation, approval, and ERP entry, while keeping a human AP Specialist
in the loop specifically for exceptions -- invoices with a missing
purchase order, a mismatched amount, a vendor data problem, or an
approval that would otherwise stall past SLA.
"""

from __future__ import annotations

from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow


def build_before_workflow() -> Workflow:
    """Build the fully-manual "before" version of the invoice processing process.

    Staffing:
        - AP Clerk: handles intake, validation, exception logging, ERP
          entry, and payment scheduling.
        - Controller: reviews and approves invoices above the AP Clerk's
          authorization threshold.
    """
    workflow = Workflow(
        workflow_id="invoice-processing-before",
        name="Invoice Processing (Before: Manual)",
        entry_node_id="invoice_intake",
        description=(
            "Baseline accounts payable process where AP Clerks and a "
            "Controller manually intake, validate, approve, and post every "
            "vendor invoice."
        ),
    )

    workflow.add_actor(
        HumanActor(
            actor_id="ap_clerk",
            name="AP Clerk",
            hourly_cost=28.0,
            speed_multiplier=1.0,
            error_rate=0.04,
        )
    )
    workflow.add_actor(
        HumanActor(
            actor_id="controller",
            name="Controller",
            hourly_cost=55.0,
            speed_multiplier=1.0,
            error_rate=0.03,
        )
    )

    workflow.add_node(
        Node(
            node_id="invoice_intake",
            name="Invoice Intake",
            actor_id="ap_clerk",
            description="Log the incoming invoice and attach it to the vendor record.",
            base_duration_minutes=8.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="validation",
            name="Validation",
            actor_id="ap_clerk",
            description="Match the invoice against the PO, receipt, and vendor master data.",
            base_duration_minutes=12.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="approval",
            name="Approval",
            actor_id="controller",
            description="Review and approve the validated invoice for payment.",
            base_duration_minutes=20.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="erp_entry",
            name="ERP Entry",
            actor_id="ap_clerk",
            description="Post the approved invoice into the ERP system.",
            base_duration_minutes=10.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="payment_scheduling",
            name="Payment Scheduling",
            actor_id="ap_clerk",
            description="Schedule the payment run for the posted invoice.",
            base_duration_minutes=5.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_missing_po",
            name="Exception: Missing PO",
            actor_id="ap_clerk",
            description="Return the invoice to the vendor pending a valid purchase order.",
            base_duration_minutes=15.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_mismatched_amount",
            name="Exception: Mismatched Amount",
            actor_id="ap_clerk",
            description="Flag the amount mismatch and route back to the vendor for correction.",
            base_duration_minutes=15.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_vendor_data_issue",
            name="Exception: Vendor Data Issue",
            actor_id="ap_clerk",
            description="Escalate incomplete or inconsistent vendor master data for correction.",
            base_duration_minutes=15.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_approval_delay",
            name="Exception: Approval Delay",
            actor_id="controller",
            description="Log an invoice that stalled in the approval queue past SLA.",
            base_duration_minutes=10.0,
            is_terminal=True,
        )
    )

    workflow.add_edge(Edge("invoice_intake", "validation", probability=1.0))
    workflow.add_edge(
        Edge("validation", "approval", probability=0.65, condition="matched")
    )
    workflow.add_edge(
        Edge(
            "validation",
            "exception_missing_po",
            probability=0.10,
            condition="missing_po",
        )
    )
    workflow.add_edge(
        Edge(
            "validation",
            "exception_mismatched_amount",
            probability=0.15,
            condition="mismatched_amount",
        )
    )
    workflow.add_edge(
        Edge(
            "validation",
            "exception_vendor_data_issue",
            probability=0.10,
            condition="vendor_data_issue",
        )
    )
    workflow.add_edge(Edge("approval", "erp_entry", probability=0.85, condition="approved"))
    workflow.add_edge(
        Edge(
            "approval",
            "exception_approval_delay",
            probability=0.15,
            condition="stalled_past_sla",
        )
    )
    workflow.add_edge(Edge("erp_entry", "payment_scheduling", probability=1.0))

    return workflow
