"""Example workflow: B2B sales lead qualification, before and after AI adoption.

This example models a common enterprise sales motion:

    Lead Intake -> Initial Research -> Discovery Call -> Proposal Draft -> Handoff
                                    \\-> Disqualified            \\-> Disqualified

The "before" variant staffs every stage with humans (SDRs and Account
Executives). The "after" variant (added separately) introduces AI agents
for the repetitive, judgment-light stages while keeping humans on the
stages that require relationship-building and negotiation, illustrating
the kind of hybrid redesign this simulator is meant to evaluate.
"""

from __future__ import annotations

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.edge import Edge
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.workflow import Workflow


def build_before_workflow() -> Workflow:
    """Build the fully-human "before" version of the lead qualification process.

    Staffing:
        - Sales Development Rep (SDR): handles intake and initial research.
        - Account Executive (AE): runs the discovery call and drafts proposals.
    """
    workflow = Workflow(
        workflow_id="sales-lead-qualification-before",
        name="Sales Lead Qualification (Before: Human-Only)",
        entry_node_id="lead_intake",
        description=(
            "Baseline process where SDRs and Account Executives manually "
            "qualify every inbound lead before it becomes a sales opportunity."
        ),
    )

    workflow.add_actor(
        HumanActor(
            actor_id="sdr",
            name="Sales Development Rep",
            hourly_cost=35.0,
            speed_multiplier=1.0,
            error_rate=0.06,
        )
    )
    workflow.add_actor(
        HumanActor(
            actor_id="ae",
            name="Account Executive",
            hourly_cost=65.0,
            speed_multiplier=1.0,
            error_rate=0.04,
        )
    )

    workflow.add_node(
        Node(
            node_id="lead_intake",
            name="Lead Intake",
            actor_id="sdr",
            description="Log the inbound lead and capture firmographic details.",
            base_duration_minutes=10.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="initial_research",
            name="Initial Research",
            actor_id="sdr",
            description="Research the account and score fit against the ICP.",
            base_duration_minutes=15.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="discovery_call",
            name="Discovery Call",
            actor_id="ae",
            description="Run a discovery call to validate needs and budget.",
            base_duration_minutes=30.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="proposal_draft",
            name="Proposal Draft",
            actor_id="ae",
            description="Draft a tailored proposal for the qualified opportunity.",
            base_duration_minutes=45.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="qualified_handoff",
            name="Qualified Handoff",
            actor_id="ae",
            description="Hand the qualified opportunity to the deal desk.",
            base_duration_minutes=5.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="disqualified",
            name="Disqualified",
            actor_id="sdr",
            description="Record the disqualification reason and close the lead.",
            base_duration_minutes=5.0,
            is_terminal=True,
        )
    )

    workflow.add_edge(Edge("lead_intake", "initial_research", probability=1.0))
    workflow.add_edge(
        Edge("initial_research", "discovery_call", probability=0.6, condition="fits_icp")
    )
    workflow.add_edge(
        Edge("initial_research", "disqualified", probability=0.4, condition="does_not_fit_icp")
    )
    workflow.add_edge(
        Edge("discovery_call", "proposal_draft", probability=0.7, condition="needs_confirmed")
    )
    workflow.add_edge(
        Edge("discovery_call", "disqualified", probability=0.3, condition="no_budget_or_need")
    )
    workflow.add_edge(Edge("proposal_draft", "qualified_handoff", probability=1.0))

    return workflow


def build_after_workflow() -> Workflow:
    """Build the AI-augmented "after" version of the lead qualification process.

    Redesign rationale:
        - Lead Intake and Initial Research are high-volume, low-judgment
          tasks well suited to AI agents: an intake agent structures the
          lead record, and a research agent scores fit against the ideal
          customer profile using firmographic data.
        - Discovery Call stays human: it requires rapport-building and
          real-time judgment that the simulator intentionally does not
          hand to an agent.
        - Proposal Draft is AI-assisted: the agent produces a first draft
          which shortens the Account Executive's effective drafting time,
          modeled here as a fast, low-cost agent step feeding into the
          same human sign-off pattern used elsewhere.
    """
    workflow = Workflow(
        workflow_id="sales-lead-qualification-after",
        name="Sales Lead Qualification (After: AI-Augmented)",
        entry_node_id="lead_intake",
        description=(
            "Redesigned process where AI agents absorb high-volume, "
            "low-judgment stages so Account Executives spend their time "
            "only on qualified, high-value conversations."
        ),
    )

    workflow.add_actor(
        AIAgentActor(
            actor_id="intake_agent",
            name="Lead Intake Agent",
            cost_per_execution=0.15,
            speed_multiplier=0.08,
            error_rate=0.02,
            escalation_rate=0.03,
            autonomy_level="autonomous",
        )
    )
    workflow.add_actor(
        AIAgentActor(
            actor_id="research_agent",
            name="Account Research Agent",
            cost_per_execution=0.40,
            speed_multiplier=0.10,
            error_rate=0.05,
            escalation_rate=0.08,
            autonomy_level="autonomous",
        )
    )
    workflow.add_actor(
        AIAgentActor(
            actor_id="proposal_agent",
            name="Proposal Drafting Agent",
            cost_per_execution=0.60,
            speed_multiplier=0.15,
            error_rate=0.05,
            escalation_rate=0.10,
            autonomy_level="assist",
        )
    )
    workflow.add_actor(
        HumanActor(
            actor_id="ae",
            name="Account Executive",
            hourly_cost=65.0,
            speed_multiplier=1.0,
            error_rate=0.04,
        )
    )

    workflow.add_node(
        Node(
            node_id="lead_intake",
            name="Lead Intake",
            actor_id="intake_agent",
            description="Structure the inbound lead record from raw form/email data.",
            base_duration_minutes=10.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="initial_research",
            name="Initial Research",
            actor_id="research_agent",
            description="Score account fit against the ICP using firmographic data.",
            base_duration_minutes=15.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="discovery_call",
            name="Discovery Call",
            actor_id="ae",
            description="Run a discovery call to validate needs and budget.",
            base_duration_minutes=30.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="proposal_draft",
            name="Proposal Draft",
            actor_id="proposal_agent",
            description="Generate a first-pass proposal draft for AE review.",
            base_duration_minutes=45.0,
        )
    )
    workflow.add_node(
        Node(
            node_id="qualified_handoff",
            name="Qualified Handoff",
            actor_id="ae",
            description="Hand the qualified opportunity to the deal desk.",
            base_duration_minutes=5.0,
            is_terminal=True,
        )
    )
    workflow.add_node(
        Node(
            node_id="disqualified",
            name="Disqualified",
            actor_id="intake_agent",
            description="Record the disqualification reason and close the lead.",
            base_duration_minutes=5.0,
            is_terminal=True,
        )
    )

    workflow.add_edge(Edge("lead_intake", "initial_research", probability=1.0))
    workflow.add_edge(
        Edge("initial_research", "discovery_call", probability=0.6, condition="fits_icp")
    )
    workflow.add_edge(
        Edge("initial_research", "disqualified", probability=0.4, condition="does_not_fit_icp")
    )
    workflow.add_edge(
        Edge("discovery_call", "proposal_draft", probability=0.7, condition="needs_confirmed")
    )
    workflow.add_edge(
        Edge("discovery_call", "disqualified", probability=0.3, condition="no_budget_or_need")
    )
    workflow.add_edge(Edge("proposal_draft", "qualified_handoff", probability=1.0))

    return workflow
