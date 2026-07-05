from importlib import resources

import pytest

from b2b_workflow_simulator.workflow_io import load_workflow

SAMPLE_FILES = (
    "sales_lead_qualification_before.json",
    "sales_lead_qualification_after.json",
    "invoice_processing_before.json",
    "invoice_processing_after.json",
    "customer_support_ticket_resolution_before.json",
    "customer_support_ticket_resolution_after.json",
)


def _sample_path(filename: str):
    return resources.files("b2b_workflow_simulator.examples.data").joinpath(filename)


@pytest.mark.parametrize("filename", SAMPLE_FILES)
def test_sample_json_workflow_loads_and_validates(filename):
    workflow = load_workflow(_sample_path(filename))

    workflow.validate()
    assert workflow.nodes
    assert workflow.actors


def test_all_bundled_examples_have_before_and_after_samples():
    names = {filename.rsplit("_", 1)[0] for filename in SAMPLE_FILES}

    for name in names:
        assert f"{name}_before.json" in SAMPLE_FILES
        assert f"{name}_after.json" in SAMPLE_FILES
