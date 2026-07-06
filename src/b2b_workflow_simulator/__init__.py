"""B2B Agentic Workflow Simulator v1.0.0.

An organizational digital twin for AI transformation.  Simulate a business
workflow **before** and **after** introducing AI agents, measure ROI, surface
bottlenecks, and generate stakeholder-ready consulting deliverables — all from
the command line with no external services.

Stable public API::

    from b2b_workflow_simulator import (
        SimulationRunner,
        AssumptionProfile,
        ScenarioConfig,
        get_scenario,
        list_scenarios,
    )

See https://github.com/aditya89bh/B2B-Agentic-Workflow-Simulator for full
documentation.
"""

from __future__ import annotations

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Stable public API convenience imports
# ---------------------------------------------------------------------------

from b2b_workflow_simulator.assumptions import AssumptionProfile
from b2b_workflow_simulator.scenario_config import ScenarioConfig
from b2b_workflow_simulator.scenarios import get_scenario, list_scenarios
from b2b_workflow_simulator.simulation import SimulationRunner

__all__ = [
    "__version__",
    "AssumptionProfile",
    "ScenarioConfig",
    "SimulationRunner",
    "get_scenario",
    "list_scenarios",
]
