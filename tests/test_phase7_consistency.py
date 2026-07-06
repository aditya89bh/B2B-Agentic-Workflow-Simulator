"""Tests for Phase 7 consistency cleanup:

- compare-example --assumptions changes output vs base assumptions
- CLI help text mentions that assumption profiles modify simulation inputs
- assumptions.py docstring no longer contains stale 'description only' language
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from b2b_workflow_simulator.assumptions import AssumptionProfile, save_assumption_profile
from b2b_workflow_simulator.cli import main

# ---------------------------------------------------------------------------
# assumptions.py docstring accuracy
# ---------------------------------------------------------------------------


def test_docstring_no_longer_claims_description_only():
    """The module docstring must not say multipliers are only logged / description-only."""
    import b2b_workflow_simulator.assumptions as mod

    doc = mod.__doc__ or ""
    stale_phrases = [
        "reported in the profile",
        "applies them by description only",
        "description only",
    ]
    for phrase in stale_phrases:
        assert phrase not in doc, (
            f"Stale phrase {phrase!r} still present in assumptions.py docstring"
        )


def test_docstring_mentions_apply_profile_to_workflow():
    """The module docstring should mention apply_profile_to_workflow."""
    import b2b_workflow_simulator.assumptions as mod

    doc = mod.__doc__ or ""
    assert "apply_profile_to_workflow" in doc


def test_docstring_mentions_cli_commands():
    """The module docstring should mention which CLI commands apply multipliers."""
    import b2b_workflow_simulator.assumptions as mod

    doc = mod.__doc__ or ""
    assert "compare-example" in doc or "executive-snapshot" in doc


# ---------------------------------------------------------------------------
# CLI --assumptions help text quality
# ---------------------------------------------------------------------------


def _get_help(command: str) -> str:
    """Run `b2b-simulator <command> --help` and return stdout."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            main([command, "--help"])
    except SystemExit:
        pass
    return buf.getvalue()


@pytest.mark.parametrize("command", [
    "roi-waterfall",
    "bottleneck-heatmap",
    "executive-snapshot",
    "consultant-packet",
    "compare-example",
])
def test_assumptions_flag_exists_in_help(command):
    """Every assumption-aware command should list --assumptions in its help."""
    help_text = _get_help(command)
    assert "--assumptions" in help_text, (
        f"`{command} --help` does not mention --assumptions"
    )


@pytest.mark.parametrize("command", [
    "roi-waterfall",
    "bottleneck-heatmap",
    "executive-snapshot",
    "consultant-packet",
    "compare-example",
])
def test_assumptions_help_mentions_scaling(command):
    """--assumptions help text should say that it scales AI or human parameters."""
    help_text = _get_help(command)
    scaling_keywords = ["Scales", "error rates", "costs", "simulation"]
    found = any(kw in help_text for kw in scaling_keywords)
    assert found, (
        f"`{command} --help` --assumptions description does not mention scaling. "
        f"Got: {help_text[help_text.find('--assumptions'):help_text.find('--assumptions')+300]!r}"
    )


# ---------------------------------------------------------------------------
# compare-example --assumptions changes output
# ---------------------------------------------------------------------------


def test_compare_example_accepts_assumptions_flag():
    """compare-example should accept --assumptions without error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profile = AssumptionProfile(num_cases=50, seed=1)
        path = str(Path(tmpdir) / "profile.json")
        save_assumption_profile(profile, path)
        ret = main(["compare-example", "invoice-processing", "--assumptions", path])
    assert ret == 0


def test_compare_example_conservative_differs_from_base(capsys):
    """compare-example with conservative profile (high AI error) changes the report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = AssumptionProfile(num_cases=100, seed=42)
        conservative = AssumptionProfile(
            num_cases=100, seed=42, ai_error_rate_multiplier=3.0
        )
        base_path = str(Path(tmpdir) / "base.json")
        cons_path = str(Path(tmpdir) / "cons.json")
        save_assumption_profile(base, base_path)
        save_assumption_profile(conservative, cons_path)

        main(["compare-example", "invoice-processing", "--assumptions", base_path])
        base_out = capsys.readouterr().out

        main(["compare-example", "invoice-processing", "--assumptions", cons_path])
        cons_out = capsys.readouterr().out

    assert base_out != cons_out, (
        "compare-example with 3× AI error rate should produce a different report than base"
    )


def test_compare_example_aggressive_has_lower_cost(capsys):
    """compare-example with aggressive (lower AI cost) should report lower after-cost."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = AssumptionProfile(num_cases=200, seed=1)
        aggressive = AssumptionProfile(
            num_cases=200, seed=1, ai_cost_multiplier=0.1
        )
        base_path = str(Path(tmpdir) / "base.json")
        aggr_path = str(Path(tmpdir) / "aggr.json")
        save_assumption_profile(base, base_path)
        save_assumption_profile(aggressive, aggr_path)

        main(["compare-example", "invoice-processing", "--assumptions", base_path])
        base_out = capsys.readouterr().out

        main(["compare-example", "invoice-processing", "--assumptions", aggr_path])
        aggr_out = capsys.readouterr().out

    assert base_out != aggr_out, (
        "compare-example with 0.1× AI cost should produce a different report than base"
    )


def test_compare_example_profile_overrides_cases(capsys):
    """Profile num_cases should override the default when --cases is not set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_100 = AssumptionProfile(num_cases=100, seed=7)
        profile_50 = AssumptionProfile(num_cases=50, seed=7)
        p100 = str(Path(tmpdir) / "p100.json")
        p50 = str(Path(tmpdir) / "p50.json")
        save_assumption_profile(profile_100, p100)
        save_assumption_profile(profile_50, p50)

        main(["compare-example", "invoice-processing", "--assumptions", p100])
        out100 = capsys.readouterr().out

        main(["compare-example", "invoice-processing", "--assumptions", p50])
        out50 = capsys.readouterr().out

    assert out100 != out50, (
        "Profile with different num_cases should produce different output"
    )


def test_compare_example_1x_multipliers_matches_default(capsys):
    """Profile with 1.0 multipliers and same cases/seed should produce identical output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profile = AssumptionProfile(
            num_cases=100, seed=42,
            ai_error_rate_multiplier=1.0,
            ai_cost_multiplier=1.0,
            human_hourly_cost_multiplier=1.0,
        )
        path = str(Path(tmpdir) / "base.json")
        save_assumption_profile(profile, path)

        main(["compare-example", "invoice-processing", "--cases", "100",
              "--seed", "42", "--assumptions", path])
        with_profile = capsys.readouterr().out

        main(["compare-example", "invoice-processing", "--cases", "100", "--seed", "42"])
        without_profile = capsys.readouterr().out

    assert with_profile == without_profile, (
        "1.0 multipliers should produce identical output to running without a profile"
    )
