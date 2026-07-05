from b2b_workflow_simulator.capacity_planning import analyze_capacity, simulate_hiring
from b2b_workflow_simulator.compliance import GDPRApprovalRequirement, evaluate_compliance
from b2b_workflow_simulator.html_report import (
    render_capacity_html,
    render_compliance_html,
    render_diff_html,
    render_hiring_html,
    render_monte_carlo_comparison_html,
    render_monte_carlo_html,
    render_policy_html,
    render_portfolio_html,
    render_sensitivity_grid_html,
    render_sla_html,
)
from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.monte_carlo import run_monte_carlo, run_monte_carlo_comparison
from b2b_workflow_simulator.policy import SeparationOfDutiesPolicy, evaluate_policies
from b2b_workflow_simulator.pool import ActorPool
from b2b_workflow_simulator.portfolio import WorkflowPortfolio
from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.primitives.event import Event, EventType
from b2b_workflow_simulator.primitives.human import HumanActor
from b2b_workflow_simulator.primitives.node import Node
from b2b_workflow_simulator.primitives.worker import Worker
from b2b_workflow_simulator.redesign import compare_workflows
from b2b_workflow_simulator.sensitivity_grid import run_sensitivity_grid
from b2b_workflow_simulator.simulation import SimulationResult
from b2b_workflow_simulator.sla import CompletionSLA, evaluate_sla
from b2b_workflow_simulator.workflow import Workflow


def make_before_kpi(name: str = "Before") -> KPIResult:
    return KPIResult(
        workflow_name=name,
        total_cases=100,
        completed_cases=70,
        failed_cases=30,
        total_cost=10000.0,
        total_duration_minutes=6000.0,
        node_total_duration_minutes={"a": 4000.0, "b": 2000.0},
        actor_utilization={"human_rep": 0.9},
    )


def make_after_kpi(name: str = "After") -> KPIResult:
    return KPIResult(
        workflow_name=name,
        total_cases=100,
        completed_cases=90,
        failed_cases=10,
        total_cost=4000.0,
        total_duration_minutes=2000.0,
        total_escalations=15,
        node_total_duration_minutes={"a": 1500.0, "b": 500.0},
        actor_utilization={"ai_agent": 0.95},
    )


def test_render_diff_html_is_well_formed_document():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert output.startswith("<!DOCTYPE html>")
    assert "<html" in output
    assert "</html>" in output
    assert "<title>" in output


def test_render_diff_html_includes_workflow_names():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert "Before" in output
    assert "After" in output


def test_render_diff_html_escapes_special_characters_in_names():
    before = make_before_kpi(name="Before <script>alert('x')</script>")
    after = make_after_kpi(name="After & Co.")
    diff = compare_workflows(before, after)

    output = render_diff_html(diff)

    assert "<script>alert" not in output
    assert "&lt;script&gt;" in output
    assert "After &amp; Co." in output


def test_render_diff_html_includes_all_expected_sections():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert "KPI Comparison" in output
    assert "ROI Summary" in output
    assert "Bottlenecks" in output
    assert "Actor Utilization" in output
    assert "Risks" in output
    assert "Recommendation" in output


def test_render_diff_html_includes_payback_when_implementation_cost_given():
    diff = compare_workflows(make_before_kpi(), make_after_kpi(), implementation_cost=1000.0)

    output = render_diff_html(diff)

    assert "Payback" in output


def test_render_diff_html_marks_cost_reduction_as_positive():
    diff = compare_workflows(make_before_kpi(), make_after_kpi())

    output = render_diff_html(diff)

    assert 'class="positive"' in output


def build_portfolio() -> WorkflowPortfolio:
    portfolio = WorkflowPortfolio(name="Q1 Transformation")
    portfolio.add_entry(
        "workflow-a", make_before_kpi(), make_after_kpi(), implementation_cost=1000.0
    )
    return portfolio


def test_render_portfolio_html_is_well_formed_document():
    output = render_portfolio_html(build_portfolio())

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_render_portfolio_html_includes_portfolio_name():
    output = render_portfolio_html(build_portfolio())

    assert "Q1 Transformation" in output


def test_render_portfolio_html_includes_all_expected_sections():
    output = render_portfolio_html(build_portfolio())

    assert "Workflow Ranking" in output
    assert "Aggregate ROI" in output
    assert "Risks" in output
    assert "Recommended Rollout Order" in output


def test_render_portfolio_html_escapes_workflow_names():
    portfolio = WorkflowPortfolio(name="<b>Bold</b> Portfolio")
    portfolio.add_entry("workflow<script>", make_before_kpi(), make_after_kpi())

    output = render_portfolio_html(portfolio)

    assert "<script>" not in output.split("<style>")[1]
    assert "&lt;b&gt;Bold&lt;/b&gt;" in output


def test_render_portfolio_html_handles_empty_portfolio():
    portfolio = WorkflowPortfolio(name="Empty")

    output = render_portfolio_html(portfolio)

    assert "0 workflow(s)" in output


def build_mc_workflow(name: str = "Monte Carlo Test <script>") -> Workflow:
    workflow = Workflow(workflow_id="mc-test", name=name, entry_node_id="review")
    workflow.add_actor(
        HumanActor(actor_id="agent", name="Agent", hourly_cost=30.0, error_rate=0.1)
    )
    workflow.add_node(
        Node(
            node_id="review",
            name="Review",
            actor_id="agent",
            base_duration_minutes=20.0,
            is_terminal=True,
        )
    )
    return workflow


def build_mc_after_workflow() -> Workflow:
    workflow = Workflow(workflow_id="mc-after", name="Monte Carlo After", entry_node_id="ai")
    workflow.add_actor(
        AIAgentActor(actor_id="ai", name="AI Reviewer", cost_per_execution=1.0, error_rate=0.05)
    )
    workflow.add_node(
        Node(
            node_id="ai",
            name="AI Review",
            actor_id="ai",
            base_duration_minutes=2.0,
            is_terminal=True,
        )
    )
    return workflow


def test_render_monte_carlo_html_is_well_formed_document():
    result = run_monte_carlo(build_mc_workflow, 20, [1, 2, 3])

    output = render_monte_carlo_html(result)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_render_monte_carlo_html_includes_expected_sections():
    result = run_monte_carlo(build_mc_workflow, 20, [1, 2, 3])

    output = render_monte_carlo_html(result)

    assert "Executive Summary" in output
    assert "Metric Distribution" in output
    assert "3 simulated runs" in output


def test_render_monte_carlo_html_escapes_workflow_name():
    result = run_monte_carlo(build_mc_workflow, 20, [1, 2, 3])

    output = render_monte_carlo_html(result)

    assert "<script>" not in output.split("<style>")[1]
    assert "&lt;script&gt;" in output


def test_render_monte_carlo_comparison_html_is_well_formed_document():
    result = run_monte_carlo_comparison(
        build_mc_workflow, build_mc_after_workflow, 20, [1, 2, 3], implementation_cost=50.0
    )

    output = render_monte_carlo_comparison_html(result)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output
    assert "Payback" in output


def test_render_monte_carlo_comparison_html_handles_missing_payback():
    result = run_monte_carlo_comparison(build_mc_workflow, build_mc_after_workflow, 20, [1, 2, 3])

    output = render_monte_carlo_comparison_html(result)

    assert "n/a" in output


def test_render_sensitivity_grid_html_is_well_formed_document():
    result = run_sensitivity_grid(
        build_mc_workflow,
        build_mc_after_workflow,
        "ai_error_rate",
        [0.05, 0.1],
        "ai_cost_per_execution",
        [0.5, 1.0],
        num_cases=20,
        seed=1,
    )

    output = render_sensitivity_grid_html(result)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output


def test_render_sensitivity_grid_html_includes_expected_sections():
    result = run_sensitivity_grid(
        build_mc_workflow,
        build_mc_after_workflow,
        "ai_error_rate",
        [0.05, 0.1],
        "ai_cost_per_execution",
        [0.5, 1.0],
        num_cases=20,
        seed=1,
    )

    output = render_sensitivity_grid_html(result)

    assert "ROI Matrix" in output
    assert "Operating Regions" in output
    assert "region-" in output


def test_render_sensitivity_grid_html_marks_unstable_cells():
    result = run_sensitivity_grid(
        build_mc_workflow,
        build_mc_after_workflow,
        "ai_error_rate",
        [0.01, 0.95],
        "ai_cost_per_execution",
        [0.5],
        num_cases=30,
        seed=1,
    )

    output = render_sensitivity_grid_html(result)

    if result.unstable_region_points():
        assert 'class="region-unstable"' in output


def build_pool_workflow(num_workers: int = 1) -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Pooled <b>Team</b>", entry_node_id="handle")
    workers = [
        Worker(worker_id=f"w{i}", name=f"Worker {i}", hourly_cost=40.0)
        for i in range(num_workers)
    ]
    workflow.add_actor(ActorPool(actor_id="team", name="Support Team", workers=workers))
    workflow.add_node(
        Node(
            node_id="handle",
            name="Handle",
            actor_id="team",
            base_duration_minutes=30.0,
            is_terminal=True,
        )
    )
    return workflow


def test_render_capacity_html_is_well_formed_document():
    kpi = KPIResult(workflow_name="Ops <script>", actor_utilization={"agent": 0.95})
    plan = analyze_capacity(kpi)

    output = render_capacity_html(plan)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output
    assert "<script>" not in output.split("<style>")[1]
    assert "&lt;script&gt;" in output


def test_render_capacity_html_includes_recommendations_table():
    kpi = KPIResult(workflow_name="Ops", actor_utilization={"agent": 0.95, "reviewer": 0.2})
    plan = analyze_capacity(kpi)

    output = render_capacity_html(plan)

    assert "Staffing Recommendations" in output
    assert "agent" in output
    assert "reviewer" in output


def test_render_capacity_html_handles_empty_plan():
    kpi = KPIResult(workflow_name="Empty Ops")
    plan = analyze_capacity(kpi)

    output = render_capacity_html(plan)

    assert "No capacity-aware utilization data" in output


def test_render_hiring_html_is_well_formed_document():
    extra = [Worker(worker_id="w-extra", name="Extra", hourly_cost=40.0)]
    result = simulate_hiring(
        build_pool_workflow, "team", extra, num_cases=20, seed=1, arrival_interval_minutes=5.0
    )

    output = render_hiring_html(result)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output
    assert "<script>" not in output.split("<style>")[1]


def test_render_hiring_html_includes_headcount_change():
    extra = [Worker(worker_id="w-extra", name="Extra", hourly_cost=40.0)]
    result = simulate_hiring(
        build_pool_workflow, "team", extra, num_cases=20, seed=1, arrival_interval_minutes=5.0
    )

    output = render_hiring_html(result)

    assert "1" in output
    assert "2" in output
    assert "Impact" in output


def build_policy_workflow() -> Workflow:
    workflow = Workflow(workflow_id="wf", name="Invoice <script>", entry_node_id="intake")
    workflow.add_actor(HumanActor(actor_id="clerk", name="Clerk"))
    workflow.add_node(Node(node_id="intake", name="Intake", actor_id="clerk", is_terminal=True))
    return workflow


def test_render_policy_html_is_well_formed_document():
    workflow = build_policy_workflow()
    policy = SeparationOfDutiesPolicy(name="sod", node_id_a="intake", node_id_b="intake")
    evaluation = evaluate_policies(workflow, [policy])

    output = render_policy_html(evaluation)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output
    assert "<script>" not in output.split("<style>")[1]
    assert "&lt;script&gt;" in output


def test_render_policy_html_includes_violations_table():
    workflow = build_policy_workflow()
    policy = SeparationOfDutiesPolicy(name="sod", node_id_a="intake", node_id_b="intake")
    evaluation = evaluate_policies(workflow, [policy])

    output = render_policy_html(evaluation)

    assert "Violations found" in output
    assert "separation_of_duties" in output


def test_render_policy_html_for_compliant_workflow():
    workflow = build_policy_workflow()
    evaluation = evaluate_policies(workflow, [])

    output = render_policy_html(evaluation)

    assert "Compliant" in output
    assert "No violations to report" in output


def test_render_compliance_html_is_well_formed_document():
    workflow = build_policy_workflow()
    requirement = GDPRApprovalRequirement(
        name="gdpr", personal_data_node_id="intake", consent_node_ids=("nowhere",)
    )
    report = evaluate_compliance(workflow, [requirement])

    output = render_compliance_html(report)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output
    assert "<script>" not in output.split("<style>")[1]
    assert "&lt;script&gt;" in output


def test_render_compliance_html_includes_score_and_violations():
    workflow = build_policy_workflow()
    requirement = GDPRApprovalRequirement(
        name="gdpr", personal_data_node_id="intake", consent_node_ids=("nowhere",)
    )
    report = evaluate_compliance(workflow, [requirement])

    output = render_compliance_html(report)

    assert "Compliance score: 0.0%" in output
    assert "gdpr_approval" in output


def test_render_compliance_html_for_fully_compliant_workflow():
    workflow = build_policy_workflow()
    report = evaluate_compliance(workflow, [])

    output = render_compliance_html(report)

    assert "Compliance score: 100.0%" in output
    assert "No violations to report" in output


def build_sla_result():
    events = [
        Event(EventType.CASE_STARTED, 0.0, "case-1"),
        Event(EventType.CASE_COMPLETED, 90.0, "case-1"),
    ]
    return SimulationResult(workflow_name="Ops <script>", events=events)


def test_render_sla_html_is_well_formed_document():
    result = build_sla_result()
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0, penalty_per_minute=5.0)
    report = evaluate_sla(result, [rule])

    output = render_sla_html(report)

    assert output.startswith("<!DOCTYPE html>")
    assert "</html>" in output
    assert "<script>" not in output.split("<style>")[1]
    assert "&lt;script&gt;" in output


def test_render_sla_html_includes_attainment_and_penalty():
    result = build_sla_result()
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=60.0, penalty_per_minute=5.0)
    report = evaluate_sla(result, [rule])

    output = render_sla_html(report)

    assert "Attainment rate: 0.0%" in output
    assert "$150.00" in output
    assert "fast-resolution" in output


def test_render_sla_html_omits_penalty_line_when_not_configured():
    result = build_sla_result()
    rule = CompletionSLA(name="fast-resolution", deadline_minutes=120.0)
    report = evaluate_sla(result, [rule])

    output = render_sla_html(report)

    assert "Attainment rate: 100.0%" in output
    assert "Estimated financial penalty" not in output
