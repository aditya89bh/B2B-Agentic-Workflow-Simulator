"""Calibration questionnaire: generate structured questions for scenario calibration.

Before configuring a scenario for a client, a consultant should gather
real operational data to replace the simulation's default assumptions.
``build_calibration_template`` produces a structured set of questions
organized into sections that correspond directly to the simulation's
modeled parameters.

All answers feed into a :class:`~b2b_workflow_simulator.scenario_config.ScenarioConfig`;
the questions explicitly state which parameter each answer will affect.

No external dependencies.  Output is Markdown or JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class CalibrationQuestion:
    """One calibration question.

    Attributes:
        question_id: Short machine-readable identifier.
        text: The question text.
        parameter: The ScenarioConfig / workflow parameter this answer feeds.
        unit: Unit of the expected answer (e.g. ``"minutes"``, ``"$/hour"``).
        guidance: Additional guidance for the consultant.
        default_assumption: The value the simulation uses if this is not answered.
        required: Whether an answer is strongly recommended before running.
    """

    question_id: str
    text: str
    parameter: str
    unit: str = ""
    guidance: str = ""
    default_assumption: str = ""
    required: bool = False


@dataclass
class CalibrationSection:
    """A group of related calibration questions.

    Attributes:
        section_id: Short identifier.
        title: Section heading.
        purpose: One-sentence description of what this section measures.
        questions: Questions in this section.
    """

    section_id: str
    title: str
    purpose: str
    questions: list[CalibrationQuestion] = field(default_factory=list)


@dataclass
class CalibrationTemplate:
    """Complete calibration questionnaire for one scenario.

    Attributes:
        scenario_slug: Slug of the target scenario.
        scenario_name: Human-readable name.
        sections: Ordered list of :class:`CalibrationSection` objects.
        preamble: Instructions shown at the top of the questionnaire.
        closing: Notes shown at the bottom.
    """

    scenario_slug: str
    scenario_name: str
    sections: list[CalibrationSection] = field(default_factory=list)
    preamble: str = ""
    closing: str = ""


_PREAMBLE = """\
This questionnaire gathers real operational data to calibrate the simulation
for your organization. Fill in as many answers as possible before generating
the configured scenario.

All default values are reasonable industry approximations. The simulation is
only as accurate as the inputs you provide. Unanswered questions will use
the scenario defaults — clearly marked below.

Return completed answers to your consultant for configuration.
"""

_CLOSING = """\
IMPORTANT: All simulation outputs are directional estimates based on the
assumptions above. They do not constitute a validated business case. Validate
key metrics with real operational data before making investment decisions.
"""


def _volume_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="volume",
        title="1. Process Volume",
        purpose="Establish realistic case volumes for the simulation.",
        questions=[
            CalibrationQuestion(
                question_id="monthly_volume",
                text="How many cases does your team process per month (average)?",
                parameter="ScenarioConfig.profile_name → num_cases",
                unit="cases/month",
                guidance="Use a 3–6 month trailing average to smooth seasonality.",
                default_assumption="Varies by scenario (see profile defaults).",
                required=True,
            ),
            CalibrationQuestion(
                question_id="peak_multiplier",
                text="During peak periods, how much does volume increase above average (e.g. 1.5× = 50% higher)?",  # noqa: E501
                parameter="Not directly modeled; inform arrival_interval_minutes.",
                unit="multiplier",
                guidance="Useful for setting the conservative profile.",
                default_assumption="1.0 (no peak modeled by default).",
            ),
            CalibrationQuestion(
                question_id="arrival_pattern",
                text="Are cases spread evenly throughout the day or do they arrive in batches?",
                parameter="arrival_interval_minutes",
                unit="minutes between arrivals (average)",
                guidance="Set to None for unconstrained (default). Set a number to enable queueing.",  # noqa: E501
                default_assumption="Unconstrained (no arrival interval).",
            ),
        ],
    )


def _staffing_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="staffing",
        title="2. Staffing and Cost",
        purpose="Replace default actor costs with your organization's actual labor rates.",
        questions=[
            CalibrationQuestion(
                question_id="fully_loaded_cost",
                text="What is the fully-loaded hourly cost per FTE for each role involved? (Salary + benefits + overhead, divided by 2,080 hours/year.)",  # noqa: E501
                parameter="ActorOverride.hourly_cost",
                unit="$/hour per role",
                guidance="List each role separately. Includes: direct labor, benefits (typically 30–40% of salary), and allocated overhead.",  # noqa: E501
                default_assumption="Scenario-specific defaults (see actor list in scenario docs).",
                required=True,
            ),
            CalibrationQuestion(
                question_id="fte_count",
                text="How many FTEs are currently allocated to this process?",
                parameter="Informational; affects interpretation of utilization results.",
                unit="FTEs",
                guidance="This helps contextualize cycle-time and utilization outputs.",
                default_assumption="Not modeled (simulation treats each actor independently).",
            ),
            CalibrationQuestion(
                question_id="daily_capacity",
                text="How many productive hours per day does each role dedicate to this process?",
                parameter="ActorOverride.available_hours_per_day",
                unit="hours/day",
                guidance="Typically 4–6 hours for roles with other responsibilities.",
                default_assumption="8 hours/day for humans; 24 hours/day for AI agents.",
            ),
        ],
    )


def _cycle_time_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="cycle_time",
        title="3. Cycle Time",
        purpose="Calibrate how long each step actually takes in your organization.",
        questions=[
            CalibrationQuestion(
                question_id="step_durations",
                text="For each stage of the process, what is the typical elapsed time from when the work is started to when it is completed? (List each stage.)",  # noqa: E501
                parameter="NodeOverride.base_duration_minutes",
                unit="minutes per stage",
                guidance="Focus on active work time, not calendar wait time. Use median, not average.",  # noqa: E501
                default_assumption="Scenario-specific defaults (see node list in scenario docs).",
                required=True,
            ),
            CalibrationQuestion(
                question_id="longest_stage",
                text="Which single stage most often determines the overall process cycle time?",
                parameter="Informational; helps prioritize bottleneck analysis.",
                unit="stage name",
                guidance="This is your primary bottleneck candidate for AI automation.",
            ),
        ],
    )


def _failure_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="failure",
        title="4. Failure and Rework",
        purpose="Understand how often cases fail, are returned, or require rework.",
        questions=[
            CalibrationQuestion(
                question_id="overall_failure_rate",
                text="What percentage of cases are rejected, returned, or fail outright (not counting intentional denials)?",  # noqa: E501
                parameter="ActorOverride.error_rate",
                unit="percentage (0–100%)",
                guidance="Distinguish between intentional business outcomes (e.g. denied claims) and process failures (e.g. data entry errors).",  # noqa: E501
                default_assumption="3–6% depending on the scenario.",
                required=True,
            ),
            CalibrationQuestion(
                question_id="rework_impact",
                text="When a case fails, approximately how long does rework take relative to the original processing time?",  # noqa: E501
                parameter="Not directly modeled; affects failure_rate interpretation.",
                unit="multiplier (e.g. 1.5 = 50% longer)",
            ),
        ],
    )


def _escalation_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="escalation",
        title="5. AI Escalation Rate",
        purpose="Estimate how often an AI agent will need to defer to a human.",
        questions=[
            CalibrationQuestion(
                question_id="expected_ai_escalation",
                text="Based on your knowledge of similar AI deployments, what escalation rate (% of cases) would you expect from an AI agent in this process?",  # noqa: E501
                parameter="ActorOverride.escalation_rate",
                unit="percentage (0–100%)",
                guidance="Industry benchmarks vary widely (10–40%). If unsure, use the conservative profile (higher escalation).",  # noqa: E501
                default_assumption="15–30% depending on scenario stage complexity.",
            ),
            CalibrationQuestion(
                question_id="escalation_handling_capacity",
                text="How many escalations per day can your human team currently absorb without degrading quality?",  # noqa: E501
                parameter="Informational; affects capacity planning interpretation.",
                unit="escalations/day",
            ),
        ],
    )


def _compliance_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="compliance",
        title="6. Compliance and Audit Requirements",
        purpose="Surface regulatory constraints that affect automation feasibility.",
        questions=[
            CalibrationQuestion(
                question_id="human_in_loop_required",
                text="Are there regulatory or contractual requirements mandating human review at any stage?",  # noqa: E501
                parameter="Informational; affects which nodes can use AI actors.",
                unit="yes/no per stage",
                guidance="Document the specific regulation or contract clause for your records.",
            ),
            CalibrationQuestion(
                question_id="audit_trail_requirements",
                text="Are there audit trail requirements (e.g. decision logging) for this process?",
                parameter="Not directly modeled; affects implementation cost estimates.",
                unit="yes/no",
            ),
        ],
    )


def _ai_readiness_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="ai_readiness",
        title="7. AI Readiness",
        purpose="Assess your organization's readiness to deploy AI in this process.",
        questions=[
            CalibrationQuestion(
                question_id="data_quality",
                text="How would you rate the quality and completeness of the input data for this process? (1 = very poor, 5 = excellent)",  # noqa: E501
                parameter="Informational; lower quality → use conservative AI error rates.",
                unit="1–5 rating",
                guidance="Poor data quality is the #1 cause of AI underperformance; use the conservative profile if rating < 3.",  # noqa: E501
                required=True,
            ),
            CalibrationQuestion(
                question_id="existing_ai_tools",
                text="Does your organization already use AI tools in adjacent processes?",
                parameter="Informational; affects implementation_cost and time-to-value.",
                unit="yes/no with description",
            ),
            CalibrationQuestion(
                question_id="ai_vendor",
                text="Do you have a preferred AI vendor or platform for this automation?",
                parameter="Affects ActorOverride.cost_per_execution (use vendor pricing).",
                unit="vendor name and pricing tier",
            ),
        ],
    )


def _implementation_section(scenario_slug: str) -> CalibrationSection:
    return CalibrationSection(
        section_id="implementation",
        title="8. Implementation Constraints",
        purpose="Establish realistic cost and timeline bounds for the implementation.",
        questions=[
            CalibrationQuestion(
                question_id="implementation_cost_estimate",
                text="What is your current estimate for one-time implementation cost? (AI platform, integration development, training, change management.)",  # noqa: E501
                parameter="ScenarioConfig profile → implementation_cost",
                unit="$ total",
                guidance="Break down into: AI platform ($), integration dev ($), training ($), change management ($).",  # noqa: E501
                required=True,
            ),
            CalibrationQuestion(
                question_id="go_live_timeline",
                text="What is the target timeline from project start to go-live?",
                parameter="Not directly modeled; affects change management costs.",
                unit="months",
            ),
            CalibrationQuestion(
                question_id="rollback_plan",
                text="Is there a plan to revert to the manual process if the AI implementation fails?",  # noqa: E501
                parameter="Informational; high-risk indicator if answer is no.",
                unit="yes/no",
            ),
        ],
    )


def build_calibration_template(scenario_slug: str, scenario=None) -> CalibrationTemplate:
    """Build a calibration questionnaire for the given scenario.

    Args:
        scenario_slug: Slug of a registered scenario.
        scenario: Optional pre-loaded scenario definition.

    Returns:
        A :class:`CalibrationTemplate` with 8 sections and scenario-aware
        question defaults.
    """
    from b2b_workflow_simulator.scenarios import get_scenario

    if scenario is None:
        scenario = get_scenario(scenario_slug)

    template = CalibrationTemplate(
        scenario_slug=scenario_slug,
        scenario_name=scenario.name,
        preamble=_PREAMBLE.strip(),
        closing=_CLOSING.strip(),
    )

    template.sections = [
        _volume_section(scenario_slug),
        _staffing_section(scenario_slug),
        _cycle_time_section(scenario_slug),
        _failure_section(scenario_slug),
        _escalation_section(scenario_slug),
        _compliance_section(scenario_slug),
        _ai_readiness_section(scenario_slug),
        _implementation_section(scenario_slug),
    ]

    return template


def render_calibration_markdown(template: CalibrationTemplate) -> str:
    """Render a :class:`CalibrationTemplate` as a Markdown document.

    Args:
        template: A built calibration template.

    Returns:
        A multi-line Markdown string.
    """
    lines: list[str] = [
        f"# Calibration Questionnaire: {template.scenario_name}",
        "",
        template.preamble,
        "",
    ]
    for section in template.sections:
        lines += ["", f"## {section.title}", "", f"*{section.purpose}*", ""]
        for q in section.questions:
            req = " *(required)*" if q.required else ""
            lines.append(f"**{q.question_id}**{req}: {q.text}")
            if q.unit:
                lines.append(f"- Unit: {q.unit}")
            if q.default_assumption:
                lines.append(f"- Default used if unanswered: *{q.default_assumption}*")
            if q.guidance:
                lines.append(f"- Guidance: {q.guidance}")
            lines += ["", "**Answer:** _______________________________________________", ""]
    lines += ["", "---", "", template.closing]
    return "\n".join(lines)


def render_calibration_json(template: CalibrationTemplate) -> str:
    """Serialize a :class:`CalibrationTemplate` to a JSON string.

    Args:
        template: A built calibration template.

    Returns:
        A JSON string.
    """
    from dataclasses import asdict
    return json.dumps(asdict(template), indent=2)


__all__ = [
    "CalibrationQuestion",
    "CalibrationSection",
    "CalibrationTemplate",
    "build_calibration_template",
    "render_calibration_json",
    "render_calibration_markdown",
]
