"""Tests for v1.0.0 package version, public API, and CLI --version flag."""

from __future__ import annotations

from pathlib import Path

import pytest

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _pyproject_version() -> str:
    for line in _PYPROJECT.read_text().splitlines():
        if line.strip().startswith("version") and "=" in line:
            # version = "1.0.0"
            return line.split("=")[1].strip().strip('"')
    raise ValueError("version not found in pyproject.toml")


# ---------------------------------------------------------------------------
# Version consistency
# ---------------------------------------------------------------------------


def test_init_version_is_1_0_0():
    import b2b_workflow_simulator as pkg
    assert pkg.__version__ == "1.0.0"


def test_pyproject_version_matches_init():
    import b2b_workflow_simulator as pkg
    assert pkg.__version__ == _pyproject_version()


def test_cli_version_flag_output(capsys):
    from b2b_workflow_simulator.cli import main
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "1.0.0" in out
    assert "b2b-workflow-simulator" in out


# ---------------------------------------------------------------------------
# Public API imports
# ---------------------------------------------------------------------------


def test_simulation_runner_importable():
    from b2b_workflow_simulator import SimulationRunner
    assert callable(SimulationRunner)


def test_assumption_profile_importable():
    from b2b_workflow_simulator import AssumptionProfile
    assert callable(AssumptionProfile)


def test_scenario_config_importable():
    from b2b_workflow_simulator import ScenarioConfig
    assert callable(ScenarioConfig)


def test_get_scenario_importable():
    from b2b_workflow_simulator import get_scenario
    assert callable(get_scenario)


def test_list_scenarios_importable():
    from b2b_workflow_simulator import list_scenarios
    assert callable(list_scenarios)


def test_all_exports_are_importable():
    import b2b_workflow_simulator as pkg
    for name in pkg.__all__:
        assert hasattr(pkg, name), f"{name} in __all__ but not accessible"


def test_package_is_production_stable():
    content = _PYPROJECT.read_text()
    assert "Production/Stable" in content


def test_docs_extra_defined():
    content = _PYPROJECT.read_text()
    assert "docs" in content
    assert "mkdocs" in content
