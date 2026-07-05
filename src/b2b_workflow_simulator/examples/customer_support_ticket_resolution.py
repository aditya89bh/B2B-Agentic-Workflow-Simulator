"""Example workflow: customer support ticket resolution, before and after AI adoption.

This example models a B2B customer support process:

    Ticket Intake -> Triage -> Response Drafting -> Follow-Up
                        \\              \\-> Exception: Low-Confidence Response
                         \\-> Escalation -> Follow-Up
                         \\-> Exception: Wrong Classification    \\-> Exception: Delayed Escalation
                         \\-> Exception: Missing Customer Context

The "before" variant staffs every stage with a human Support Agent, with
a Specialist handling escalations. The "after" variant (added separately)
introduces AI agents for triage and response drafting, while keeping a
human Support Reviewer in the loop for cases the AI flags as ambiguous or
low-confidence, and reserving the Specialist purely for true escalations.
"""

from __future__ import annotations

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.duration import DurationModel
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow


def build_before_workflow() -> Workflow:
    """Build the fully-manual "before" version of the ticket resolution process.

    Staffing:
        - Support Agent: handles intake, triage, response drafting, and
          the final customer follow-up.
        - Specialist: handles escalated tickets and reviews responses the
          Support Agent is not confident about.
    """
    workflow = Workflow(
        workflow_id="customer-support-ticket-resolution-before",
        name="Customer Support Ticket Resolution (Before: Manual)",
        entry_node_id="ticket_intake",
        description=(
            "Baseline support process where a Support Agent manually "
            "triages, drafts responses to, and follows up on every "
            "customer ticket, escalating complex cases to a Specialist."
        ),
    )

    workflow.add_actor(
        HumanActor(
            actor_id="support_agent",
            name="Support Agent",
            hourly_cost=25.0,
            speed_multiplier=1.0,
            error_rate=0.02,
        )
    )
    workflow.add_actor(
        HumanActor(
            actor_id="specialist",
            name="Specialist",
            hourly_cost=45.0,
            speed_multiplier=1.0,
            error_rate=0.02,
        )
    )

    workflow.add_node(
        Node(
            node_id="ticket_intake",
            name="Ticket Intake",
            actor_id="support_agent",
            description="Log the incoming ticket and capture customer/account context.",
            base_duration_minutes=5.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="triage",
            name="Triage",
            actor_id="support_agent",
            description="Classify the ticket type and priority.",
            base_duration_minutes=8.0,
            duration_model=DurationModel(kind="triangular", minimum=4.0, mode=8.0, maximum=18.0),
        )
    )
    workflow.add_node(
        Node(
            node_id="response_drafting",
            name="Response Drafting",
            actor_id="support_agent",
            description="Draft a resolution response for the customer.",
            base_duration_minutes=15.0,
            duration_model=DurationModel(kind="triangular", minimum=8.0, mode=15.0, maximum=35.0),
        )
    )
    workflow.add_node(
        Node(
            node_id="escalation",
            name="Escalation",
            actor_id="specialist",
            description="Investigate and resolve a complex or high-priority ticket.",
            base_duration_minutes=25.0,
            duration_model=DurationModel(kind="triangular", minimum=15.0, mode=25.0, maximum=60.0),
        )
    )
    workflow.add_node(
        Node(
            node_id="follow_up",
            name="Follow-Up",
            actor_id="support_agent",
            description="Confirm the resolution with the customer and close the ticket.",
            base_duration_minutes=5.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_wrong_classification",
            name="Exception: Wrong Classification",
            actor_id="support_agent",
            description="Re-triage a ticket that was routed to the wrong queue.",
            base_duration_minutes=10.0,
            duration_model=DurationModel(kind="uniform", minimum=5.0, maximum=18.0),
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_missing_customer_context",
            name="Exception: Missing Customer Context",
            actor_id="support_agent",
            description="Request additional account details from the customer before proceeding.",
            base_duration_minutes=12.0,
            duration_model=DurationModel(kind="uniform", minimum=6.0, maximum=20.0),
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_low_confidence",
            name="Exception: Low-Confidence Response",
            actor_id="specialist",
            description="Review a response the Support Agent was not confident about.",
            base_duration_minutes=15.0,
            duration_model=DurationModel(kind="uniform", minimum=8.0, maximum=25.0),
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_delayed_escalation",
            name="Exception: Delayed Escalation",
            actor_id="specialist",
            description="Log and remediate an escalation that breached its SLA.",
            base_duration_minutes=10.0,
            is_terminal=True,
        )
    )

    workflow.add_edge(Edge("ticket_intake", "triage", probability=1.0))
    workflow.add_edge(
        Edge("triage", "response_drafting", probability=0.55, condition="straightforward")
    )
    workflow.add_edge(Edge("triage", "escalation", probability=0.20, condition="needs_escalation"))
    workflow.add_edge(
        Edge(
            "triage",
            "exception_wrong_classification",
            probability=0.10,
            condition="wrong_classification",
        )
    )
    workflow.add_edge(
        Edge(
            "triage",
            "exception_missing_customer_context",
            probability=0.15,
            condition="missing_customer_context",
        )
    )
    workflow.add_edge(
        Edge("response_drafting", "follow_up", probability=0.85, condition="resolved")
    )
    workflow.add_edge(
        Edge(
            "response_drafting",
            "exception_low_confidence",
            probability=0.15,
            condition="low_confidence",
        )
    )
    workflow.add_edge(Edge("escalation", "follow_up", probability=0.80, condition="resolved"))
    workflow.add_edge(
        Edge(
            "escalation",
            "exception_delayed_escalation",
            probability=0.20,
            condition="delayed_escalation",
        )
    )

    return workflow


def build_after_workflow() -> Workflow:
    """Build the AI-augmented "after" version of the ticket resolution process.

    Redesign rationale:
        - Ticket Intake, Triage, Response Drafting, and Follow-Up become
          straight-through processing handled by AI agents: a triage
          agent classifies the ticket, and a response agent drafts
          replies and sends automated follow-ups.
        - Tickets the triage agent misroutes or cannot classify, and
          responses the response agent flags as low-confidence, are
          routed to a human Support Reviewer -- a new role introduced
          specifically to approve or correct AI output on complex cases.
        - The Specialist is reserved purely for genuine escalations and
          any resulting SLA breaches, matching how a real support
          organization would keep specialist capacity for the hardest
          cases only.
    """
    workflow = Workflow(
        workflow_id="customer-support-ticket-resolution-after",
        name="Customer Support Ticket Resolution (After: AI-Augmented)",
        entry_node_id="ticket_intake",
        description=(
            "Redesigned process where AI agents triage tickets and draft "
            "responses end to end, a human Support Reviewer approves "
            "complex or low-confidence cases, and a Specialist handles "
            "only genuine escalations."
        ),
    )

    workflow.add_actor(
        AIAgentActor(
            actor_id="triage_agent",
            name="Triage Agent",
            cost_per_execution=0.08,
            speed_multiplier=0.05,
            error_rate=0.02,
            escalation_rate=0.03,
            autonomy_level="autonomous",
        )
    )
    workflow.add_actor(
        AIAgentActor(
            actor_id="response_agent",
            name="Response Agent",
            cost_per_execution=0.15,
            speed_multiplier=0.08,
            error_rate=0.02,
            escalation_rate=0.04,
            autonomy_level="autonomous",
        )
    )
    workflow.add_actor(
        HumanActor(
            actor_id="specialist",
            name="Specialist",
            hourly_cost=45.0,
            speed_multiplier=1.0,
            error_rate=0.02,
        )
    )
    workflow.add_actor(
        HumanActor(
            actor_id="support_reviewer",
            name="Support Reviewer",
            hourly_cost=30.0,
            speed_multiplier=1.0,
            error_rate=0.02,
        )
    )

    workflow.add_node(
        Node(
            node_id="ticket_intake",
            name="Ticket Intake",
            actor_id="triage_agent",
            description="Automatically log the ticket and pull customer/account context.",
            base_duration_minutes=5.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="triage",
            name="Triage",
            actor_id="triage_agent",
            description="Automatically classify the ticket type and priority.",
            base_duration_minutes=8.0,
            duration_model=DurationModel(kind="uniform", minimum=5.0, maximum=12.0),
        )
    )
    workflow.add_node(
        Node(
            node_id="response_drafting",
            name="Response Drafting",
            actor_id="response_agent",
            description="Automatically draft a resolution response for the customer.",
            base_duration_minutes=15.0,
            duration_model=DurationModel(kind="uniform", minimum=10.0, maximum=22.0),
        )
    )
    workflow.add_node(
        Node(
            node_id="escalation",
            name="Escalation",
            actor_id="specialist",
            description="Investigate and resolve a complex or high-priority ticket.",
            base_duration_minutes=25.0,
            duration_model=DurationModel(kind="triangular", minimum=15.0, mode=25.0, maximum=60.0),
        )
    )
    workflow.add_node(
        Node(
            node_id="follow_up",
            name="Follow-Up",
            actor_id="response_agent",
            description="Automatically confirm the resolution with the customer and close it.",
            base_duration_minutes=5.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_wrong_classification",
            name="Exception: Wrong Classification",
            actor_id="support_reviewer",
            description="Correct a ticket the triage agent routed to the wrong queue.",
            base_duration_minutes=10.0,
            duration_model=DurationModel(kind="uniform", minimum=5.0, maximum=18.0),
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_missing_customer_context",
            name="Exception: Missing Customer Context",
            actor_id="support_reviewer",
            description="Request additional account details the AI could not find automatically.",
            base_duration_minutes=12.0,
            duration_model=DurationModel(kind="uniform", minimum=6.0, maximum=20.0),
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_low_confidence",
            name="Exception: Low-Confidence Response",
            actor_id="support_reviewer",
            description="Review and approve or rewrite a low-confidence AI-drafted response.",
            base_duration_minutes=15.0,
            duration_model=DurationModel(kind="uniform", minimum=8.0, maximum=25.0),
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="exception_delayed_escalation",
            name="Exception: Delayed Escalation",
            actor_id="specialist",
            description="Log and remediate an escalation that breached its SLA.",
            base_duration_minutes=10.0,
            is_terminal=True,
        )
    )

    workflow.add_edge(Edge("ticket_intake", "triage", probability=1.0))
    workflow.add_edge(
        Edge("triage", "response_drafting", probability=0.65, condition="straightforward")
    )
    workflow.add_edge(Edge("triage", "escalation", probability=0.15, condition="needs_escalation"))
    workflow.add_edge(
        Edge(
            "triage",
            "exception_wrong_classification",
            probability=0.05,
            condition="wrong_classification",
        )
    )
    workflow.add_edge(
        Edge(
            "triage",
            "exception_missing_customer_context",
            probability=0.15,
            condition="missing_customer_context",
        )
    )
    workflow.add_edge(
        Edge("response_drafting", "follow_up", probability=0.82, condition="resolved")
    )
    workflow.add_edge(
        Edge(
            "response_drafting",
            "exception_low_confidence",
            probability=0.18,
            condition="low_confidence",
        )
    )
    workflow.add_edge(Edge("escalation", "follow_up", probability=0.85, condition="resolved"))
    workflow.add_edge(
        Edge(
            "escalation",
            "exception_delayed_escalation",
            probability=0.15,
            condition="delayed_escalation",
        )
    )

    return workflow
