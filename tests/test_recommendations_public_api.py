"""Tests proving the build_recommendations_text refactor is correct.

1. build_recommendations_text() returns the same output as the private alias.
2. configured_case_study.py uses the public helper (no private import).
3. No source file outside packet.py imports _build_recommendations_txt.
"""

from __future__ import annotations

import ast
from pathlib import Path

from b2b_workflow_simulator.examples import invoice_processing
from b2b_workflow_simulator.packet import _build_recommendations_txt, build_recommendations_text
from b2b_workflow_simulator.simulation import SimulationRunner

_SRC_ROOT = Path(__file__).parent.parent / "src" / "b2b_workflow_simulator"


def _run_pair(n: int = 100, seed: int = 42):
    r1 = SimulationRunner(seed=seed).run(
        invoice_processing.build_before_workflow(), n, collect_events=False
    )
    r2 = SimulationRunner(seed=seed).run(
        invoice_processing.build_after_workflow(), n, collect_events=False
    )
    return r1.kpi, r2.kpi


# ---------------------------------------------------------------------------
# 1. Public and private names return identical output
# ---------------------------------------------------------------------------


def test_public_function_matches_private_alias():
    before, after = _run_pair()
    public = build_recommendations_text(before, after)
    private = _build_recommendations_txt(before, after)
    assert public == private


def test_public_function_output_is_non_empty():
    before, after = _run_pair()
    result = build_recommendations_text(before, after)
    assert len(result) > 0


def test_public_function_contains_recommendations_header():
    before, after = _run_pair()
    result = build_recommendations_text(before, after)
    assert "RECOMMENDATIONS" in result


def test_public_function_deterministic():
    before, after = _run_pair()
    assert build_recommendations_text(before, after) == build_recommendations_text(before, after)


def test_public_function_exported_in_all():
    from b2b_workflow_simulator import packet
    assert "build_recommendations_text" in packet.__all__


def test_private_alias_still_works():
    """Backward-compatible private alias must not be removed."""
    before, after = _run_pair()
    result = _build_recommendations_txt(before, after)
    assert "RECOMMENDATIONS" in result


# ---------------------------------------------------------------------------
# 2. configured_case_study.py uses the public import
# ---------------------------------------------------------------------------


def test_configured_case_study_imports_public_name():
    src = (_SRC_ROOT / "configured_case_study.py").read_text()
    assert "build_recommendations_text" in src, (
        "configured_case_study.py should import build_recommendations_text"
    )


def test_configured_case_study_does_not_import_private_name():
    src = (_SRC_ROOT / "configured_case_study.py").read_text()
    assert "_build_recommendations_txt" not in src, (
        "configured_case_study.py must not import the private alias _build_recommendations_txt"
    )


# ---------------------------------------------------------------------------
# 3. No source file outside packet.py imports the private name
# ---------------------------------------------------------------------------


def _get_all_imports(source: str) -> list[str]:
    """Return a flat list of imported names from a Python source string."""
    imported: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return imported
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
    return imported


def test_no_source_module_imports_private_helper():
    """Outside packet.py, no source file should import _build_recommendations_txt."""
    violations = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        if path.name == "packet.py":
            continue
        src = path.read_text()
        if "_build_recommendations_txt" in src:
            violations.append(str(path.relative_to(_SRC_ROOT.parent.parent)))
    assert violations == [], (
        f"These source files import a private helper from packet.py: {violations}"
    )


def test_packet_py_defines_both_names():
    """packet.py should define the public function and the private alias."""
    import b2b_workflow_simulator.packet as pkg
    assert callable(getattr(pkg, "build_recommendations_text", None))
    assert callable(getattr(pkg, "_build_recommendations_txt", None))
