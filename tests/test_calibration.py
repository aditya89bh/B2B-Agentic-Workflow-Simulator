"""Tests for the calibration questionnaire module."""

from __future__ import annotations

import json

import pytest

from b2b_workflow_simulator.calibration import (
    CalibrationTemplate,
    build_calibration_template,
    render_calibration_json,
    render_calibration_markdown,
)
from b2b_workflow_simulator.scenarios import scenario_names


@pytest.mark.parametrize("slug", scenario_names())
def test_build_template_for_all_scenarios(slug):
    template = build_calibration_template(slug)
    assert isinstance(template, CalibrationTemplate)
    assert template.scenario_slug == slug


def test_template_has_8_sections():
    template = build_calibration_template("healthcare-prior-authorization")
    assert len(template.sections) == 8


def test_template_has_preamble_and_closing():
    template = build_calibration_template("it-support-triage")
    assert len(template.preamble) > 20
    assert len(template.closing) > 20


def test_template_has_questions_in_each_section():
    template = build_calibration_template("invoice-processing")
    for section in template.sections:
        assert len(section.questions) >= 1


def test_markdown_output_contains_scenario_name():
    template = build_calibration_template("healthcare-prior-authorization")
    md = render_calibration_markdown(template)
    assert "Healthcare" in md or "Prior Auth" in md


def test_markdown_output_starts_with_heading():
    template = build_calibration_template("it-support-triage")
    md = render_calibration_markdown(template)
    assert md.startswith("# Calibration Questionnaire")


def test_markdown_contains_all_section_titles():
    template = build_calibration_template("invoice-processing")
    md = render_calibration_markdown(template)
    for section in template.sections:
        assert section.title in md


def test_json_output_valid():
    template = build_calibration_template("hr-recruiting-screening")
    json_str = render_calibration_json(template)
    data = json.loads(json_str)
    assert "scenario_slug" in data
    assert "sections" in data


def test_json_output_has_questions():
    template = build_calibration_template("it-support-triage")
    data = json.loads(render_calibration_json(template))
    total_questions = sum(len(s["questions"]) for s in data["sections"])
    assert total_questions >= 15


def test_markdown_deterministic():
    template = build_calibration_template("it-support-triage")
    assert render_calibration_markdown(template) == render_calibration_markdown(template)


def test_json_deterministic():
    template = build_calibration_template("it-support-triage")
    assert render_calibration_json(template) == render_calibration_json(template)


def test_output_file_creation(tmp_path):
    from b2b_workflow_simulator.cli import main
    out = str(tmp_path / "calibration.md")
    ret = main(["calibration-template", "it-support-triage", "--output", out])
    assert ret == 0
    assert (tmp_path / "calibration.md").exists()
    assert len((tmp_path / "calibration.md").read_text()) > 100


def test_json_format_cli(capsys):
    from b2b_workflow_simulator.cli import main
    ret = main(["calibration-template", "it-support-triage", "--format", "json"])
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["scenario_slug"] == "it-support-triage"
