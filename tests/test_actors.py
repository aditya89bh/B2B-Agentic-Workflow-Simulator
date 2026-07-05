import pytest

from b2b_workflow_simulator.primitives.actor import Actor
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.human import HumanActor


def test_actor_rejects_empty_actor_id():
    with pytest.raises(ValueError, match="actor_id"):
        Actor(actor_id="", name="Someone")


def test_actor_rejects_empty_name():
    with pytest.raises(ValueError, match="name"):
        Actor(actor_id="a1", name="")


def test_actor_base_kind_is_generic():
    actor = Actor(actor_id="a1", name="Generic")
    assert actor.kind == "actor"


def test_human_actor_defaults():
    human = HumanActor(actor_id="sdr", name="Sales Rep")

    assert human.hourly_cost == 0.0
    assert human.speed_multiplier == 1.0
    assert human.error_rate == 0.0
    assert human.available_hours_per_day == 8.0
    assert human.kind == "human"


def test_human_actor_cost_for_duration():
    human = HumanActor(actor_id="sdr", name="Sales Rep", hourly_cost=60.0)

    assert human.cost_for_duration(30.0) == pytest.approx(30.0)
    assert human.cost_for_duration(60.0) == pytest.approx(60.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hourly_cost": -1.0},
        {"speed_multiplier": 0.0},
        {"speed_multiplier": -1.0},
        {"error_rate": -0.1},
        {"error_rate": 1.1},
        {"available_hours_per_day": 0.0},
    ],
)
def test_human_actor_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        HumanActor(actor_id="sdr", name="Sales Rep", **kwargs)


def test_ai_agent_actor_defaults():
    agent = AIAgentActor(actor_id="bot", name="Intake Bot")

    assert agent.cost_per_execution == 0.0
    assert agent.speed_multiplier == 0.2
    assert agent.error_rate == 0.0
    assert agent.escalation_rate == 0.0
    assert agent.autonomy_level == "autonomous"
    assert agent.kind == "ai_agent"


def test_ai_agent_actor_cost_for_duration_is_flat_fee():
    agent = AIAgentActor(actor_id="bot", name="Intake Bot", cost_per_execution=0.25)

    assert agent.cost_for_duration(1.0) == pytest.approx(0.25)
    assert agent.cost_for_duration(1000.0) == pytest.approx(0.25)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cost_per_execution": -1.0},
        {"speed_multiplier": 0.0},
        {"error_rate": -0.1},
        {"error_rate": 1.1},
        {"escalation_rate": -0.1},
        {"escalation_rate": 1.1},
    ],
)
def test_ai_agent_actor_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        AIAgentActor(actor_id="bot", name="Intake Bot", **kwargs)
