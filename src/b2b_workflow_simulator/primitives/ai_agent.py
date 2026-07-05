"""AI agent actor primitive."""

from __future__ import annotations

from dataclasses import dataclass

from b2b_workflow_simulator.primitives.actor import Actor


@dataclass
class AIAgentActor(Actor):
    """An AI agent performing work in the workflow.

    AI agents are modeled differently from humans: cost is typically
    per-execution rather than hourly, latency is usually far lower than
    human task duration, and failure modes tend to be different (e.g.
    incorrect outputs or requests that fall outside the agent's
    competence) captured here as `error_rate` plus an `escalation_rate`
    describing how often the agent hands off to a human instead of
    completing the task itself.

    Attributes:
        cost_per_execution: Flat cost incurred each time the agent runs
            (e.g. LLM API cost, tool usage cost).
        speed_multiplier: Multiplier applied to a node's base duration,
            analogous to `HumanActor.speed_multiplier`. AI agents typically
            use values well below 1.0.
        error_rate: Probability (0.0-1.0) the agent produces an incorrect
            or unusable result on a given execution.
        escalation_rate: Probability (0.0-1.0) the agent defers the task to
            a human rather than attempting it, independent of error_rate.
        autonomy_level: Descriptive label such as "assist", "co-pilot", or
            "autonomous", used for reporting only.
    """

    cost_per_execution: float = 0.0
    speed_multiplier: float = 0.2
    error_rate: float = 0.0
    escalation_rate: float = 0.0
    autonomy_level: str = "autonomous"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.cost_per_execution < 0:
            raise ValueError("cost_per_execution cannot be negative")
        if self.speed_multiplier <= 0:
            raise ValueError("speed_multiplier must be positive")
        if not 0.0 <= self.error_rate <= 1.0:
            raise ValueError("error_rate must be between 0.0 and 1.0")
        if not 0.0 <= self.escalation_rate <= 1.0:
            raise ValueError("escalation_rate must be between 0.0 and 1.0")

    @property
    def kind(self) -> str:
        return "ai_agent"

    def cost_for_duration(self, minutes: float) -> float:
        """Return the cost of one execution.

        AI agent cost is modeled as a flat per-execution fee rather than
        scaling with duration, reflecting typical API/tool pricing.
        """
        del minutes
        return self.cost_per_execution
