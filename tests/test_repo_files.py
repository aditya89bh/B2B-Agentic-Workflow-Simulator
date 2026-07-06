"""Tests verifying required repository infrastructure files exist and contain key content."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_ci_workflow_exists():
    assert (REPO_ROOT / ".github" / "workflows" / "ci.yml").exists()


def test_ci_workflow_contains_pytest():
    content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "pytest" in content


def test_ci_workflow_contains_ruff():
    content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "ruff" in content


def test_ci_workflow_contains_build():
    content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "python -m build" in content


def test_ci_workflow_covers_all_python_versions():
    content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "3.10" in content
    assert "3.11" in content
    assert "3.12" in content


def test_ci_workflow_triggers_on_push_and_pr():
    content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "push" in content
    assert "pull_request" in content


def test_contributing_exists():
    assert (REPO_ROOT / "CONTRIBUTING.md").exists()


def test_contributing_mentions_pytest():
    content = (REPO_ROOT / "CONTRIBUTING.md").read_text()
    assert "pytest" in content


def test_contributing_mentions_ruff():
    content = (REPO_ROOT / "CONTRIBUTING.md").read_text()
    assert "ruff" in content


def test_contributing_mentions_no_coauthored():
    content = (REPO_ROOT / "CONTRIBUTING.md").read_text()
    assert "Co-authored-by" in content or "co-authored" in content.lower()


def test_code_of_conduct_exists():
    assert (REPO_ROOT / "CODE_OF_CONDUCT.md").exists()


def test_code_of_conduct_has_standards_section():
    content = (REPO_ROOT / "CODE_OF_CONDUCT.md").read_text()
    assert "standard" in content.lower() or "pledge" in content.lower()
