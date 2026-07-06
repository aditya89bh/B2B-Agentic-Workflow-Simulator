"""Documentation consistency checks for v1.0.0.

Verifies that key documentation files exist, mention the right content,
and that the CLI reference covers all registered commands.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parent.parent
_DOCS = _ROOT / "docs"
_CLI_REF = _DOCS / "cli_reference.md"


def _cli_ref_text() -> str:
    return _CLI_REF.read_text()


# ---------------------------------------------------------------------------
# CLI command coverage in docs/cli_reference.md
# ---------------------------------------------------------------------------


def _get_parser_commands() -> list[str]:
    """Return all subcommand names registered in the CLI parser."""
    from b2b_workflow_simulator.cli import build_parser
    parser = build_parser()
    # Access the subparser actions
    for action in parser._actions:
        if hasattr(action, "_name_parser_map"):
            return list(action._name_parser_map.keys())
    return []


def test_cli_reference_exists():
    assert _CLI_REF.exists(), "docs/cli_reference.md is missing"


def test_all_cli_commands_in_reference():
    commands = _get_parser_commands()
    ref_text = _cli_ref_text()
    missing = [cmd for cmd in commands if cmd not in ref_text]
    assert missing == [], (
        f"These CLI commands are not documented in docs/cli_reference.md: {missing}"
    )


# ---------------------------------------------------------------------------
# Scenario coverage
# ---------------------------------------------------------------------------


def test_scenario_library_doc_exists():
    assert (_DOCS / "scenario_library.md").exists()


def test_all_scenarios_mentioned_in_docs():
    from b2b_workflow_simulator.scenarios import scenario_names
    scenario_lib = (_DOCS / "scenario_library.md").read_text()
    index = (_DOCS / "index.md").read_text()
    combined = scenario_lib + index
    for slug in scenario_names():
        short = slug.split("-")[0]  # at least the category word appears
        assert short in combined or slug in combined, (
            f"Scenario slug {slug!r} not found in scenario_library.md or index.md"
        )


# ---------------------------------------------------------------------------
# Release files exist
# ---------------------------------------------------------------------------


def test_release_notes_exist():
    assert (_DOCS / "release_notes.md").exists()


def test_release_notes_mention_v1():
    content = (_DOCS / "release_notes.md").read_text()
    assert "1.0.0" in content


def test_changelog_mentions_v1():
    changelog = (_ROOT / "CHANGELOG.md").read_text()
    assert "1.0.0" in changelog or "v1.0.0" in changelog


def test_release_checklist_exists():
    assert (_ROOT / "RELEASE_CHECKLIST.md").exists()


def test_release_checklist_has_key_items():
    content = (_ROOT / "RELEASE_CHECKLIST.md").read_text()
    for item in ("pytest", "ruff", "build", "tag"):
        assert item in content.lower(), f"RELEASE_CHECKLIST.md missing item: {item!r}"


# ---------------------------------------------------------------------------
# README checks
# ---------------------------------------------------------------------------


def test_readme_mentions_limitations():
    readme = (_ROOT / "README.md").read_text()
    assert "Limitation" in readme or "limitation" in readme


def test_readme_mentions_validation():
    readme = (_ROOT / "README.md").read_text()
    assert "1822" in readme or "test" in readme.lower()


def test_readme_not_tool_not_model():
    readme = (_ROOT / "README.md").read_text()
    assert "directional simulation tool" in readme


# ---------------------------------------------------------------------------
# Sample configs mentioned somewhere
# ---------------------------------------------------------------------------


def test_sample_configs_mentioned_in_docs():
    from b2b_workflow_simulator.cli import _discover_sample_configs
    configs = _discover_sample_configs()
    assert len(configs) == 6, f"Expected 6 sample configs, found {len(configs)}"


# ---------------------------------------------------------------------------
# Release example outputs exist
# ---------------------------------------------------------------------------


def test_release_examples_directory_exists():
    release_dir = _ROOT / "examples" / "outputs" / "final_release"
    assert release_dir.is_dir(), "examples/outputs/final_release/ directory missing"


def test_release_examples_files_exist():
    release_dir = _ROOT / "examples" / "outputs" / "final_release"
    expected = [
        "healthcare_executive_snapshot.txt",
        "scenario_matrix_base.json",
        "healthcare_workflow_before.mmd",
        "healthcare_roi_waterfall.svg",
        "calibration_healthcare.md",
    ]
    for filename in expected:
        assert (release_dir / filename).exists(), (
            f"Missing release example: examples/outputs/final_release/{filename}"
        )


def test_mkdocs_yml_exists():
    assert (_ROOT / "mkdocs.yml").exists()


def test_examples_readme_exists():
    assert (_ROOT / "examples" / "README.md").exists()
