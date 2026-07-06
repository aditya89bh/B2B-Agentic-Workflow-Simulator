"""Tests verifying that API reference documented import paths exist and are importable."""

from __future__ import annotations

import importlib


def _import(module: str, name: str) -> None:
    """Assert that `from module import name` succeeds."""
    mod = importlib.import_module(module)
    assert hasattr(mod, name), f"{module}.{name} not found"


def test_workflow_importable():
    _import("b2b_workflow_simulator.workflow", "Workflow")


def test_node_importable():
    _import("b2b_workflow_simulator.primitives", "Node")


def test_edge_importable():
    _import("b2b_workflow_simulator.primitives", "Edge")


def test_human_actor_importable():
    _import("b2b_workflow_simulator.primitives", "HumanActor")


def test_ai_agent_actor_importable():
    _import("b2b_workflow_simulator.primitives", "AIAgentActor")


def test_actor_pool_importable():
    _import("b2b_workflow_simulator.pool", "ActorPool")


def test_worker_importable():
    _import("b2b_workflow_simulator.primitives.worker", "Worker")


def test_simulation_runner_importable():
    _import("b2b_workflow_simulator.simulation", "SimulationRunner")


def test_kpi_result_importable():
    _import("b2b_workflow_simulator.kpi", "KPIResult")


def test_redesign_diff_importable():
    _import("b2b_workflow_simulator.redesign", "RedesignDiff")


def test_compare_workflows_importable():
    _import("b2b_workflow_simulator.redesign", "compare_workflows")


def test_workflow_portfolio_importable():
    _import("b2b_workflow_simulator.portfolio", "WorkflowPortfolio")


def test_monte_carlo_importable():
    _import("b2b_workflow_simulator.monte_carlo", "run_monte_carlo_comparison")


def test_sensitivity_importable():
    _import("b2b_workflow_simulator.sensitivity", "run_sensitivity_sweep")


def test_policy_importable():
    _import("b2b_workflow_simulator.policy", "evaluate_policies")


def test_compliance_importable():
    _import("b2b_workflow_simulator.compliance", "evaluate_compliance")


def test_sla_importable():
    _import("b2b_workflow_simulator.sla", "evaluate_sla")


def test_risk_importable():
    _import("b2b_workflow_simulator.risk", "compute_risk")


def test_recommendation_importable():
    _import("b2b_workflow_simulator.recommendation", "generate_recommendations")


def test_ai_adoption_importable():
    _import("b2b_workflow_simulator.ai_adoption", "assess_ai_adoption")


def test_executive_assessment_importable():
    _import("b2b_workflow_simulator.executive_report", "build_executive_assessment")


def test_organization_importable():
    _import("b2b_workflow_simulator.org_model", "Organization")


def test_department_importable():
    _import("b2b_workflow_simulator.org_model", "Department")


def test_team_importable():
    _import("b2b_workflow_simulator.org_model", "Team")


def test_role_importable():
    _import("b2b_workflow_simulator.org_model", "Role")


def test_org_budget_importable():
    _import("b2b_workflow_simulator.budget", "OrgBudget")


def test_shared_resource_pool_importable():
    _import("b2b_workflow_simulator.shared_resources", "SharedResourcePool")


def test_growth_projection_importable():
    _import("b2b_workflow_simulator.growth", "GrowthProjection")


def test_project_growth_importable():
    _import("b2b_workflow_simulator.growth", "project_growth")


def test_org_health_score_importable():
    _import("b2b_workflow_simulator.org_health", "OrgHealthScore")


def test_compute_org_health_importable():
    _import("b2b_workflow_simulator.org_health", "compute_org_health")


def test_visualization_importable():
    _import("b2b_workflow_simulator.visualization", "to_mermaid")
    _import("b2b_workflow_simulator.visualization", "to_text")
    _import("b2b_workflow_simulator.visualization", "compare_text")


def test_waterfall_importable():
    _import("b2b_workflow_simulator.waterfall", "build_roi_waterfall")
    _import("b2b_workflow_simulator.waterfall", "waterfall_to_text")
    _import("b2b_workflow_simulator.waterfall", "waterfall_to_svg")


def test_heatmap_importable():
    _import("b2b_workflow_simulator.heatmap", "build_bottleneck_heatmap")
    _import("b2b_workflow_simulator.heatmap", "heatmap_to_text")
    _import("b2b_workflow_simulator.heatmap", "heatmap_to_svg")


def test_snapshot_importable():
    _import("b2b_workflow_simulator.snapshot", "build_snapshot")
    _import("b2b_workflow_simulator.snapshot", "snapshot_to_text")
    _import("b2b_workflow_simulator.snapshot", "snapshot_to_html")


def test_assumption_profile_importable():
    _import("b2b_workflow_simulator.assumptions", "AssumptionProfile")
    _import("b2b_workflow_simulator.assumptions", "load_assumption_profile")
    _import("b2b_workflow_simulator.assumptions", "save_assumption_profile")


def test_packet_importable():
    _import("b2b_workflow_simulator.packet", "generate_packet")
