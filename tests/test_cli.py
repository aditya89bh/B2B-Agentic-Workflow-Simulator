import json

from b2b_workflow_simulator.cli import build_parser, main


def test_build_parser_requires_a_command():
    parser = build_parser()

    exit_code = None
    try:
        parser.parse_args([])
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code == 2


def test_run_example_prints_comparison_table(capsys):
    exit_code = main(["run-example", "sales-lead-qualification", "--cases", "20", "--seed", "1"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Before" in output
    assert "After" in output
    assert "Completion rate" in output
    assert "Total cost" in output


def test_run_example_rejects_unknown_example(capsys):
    parser = build_parser()
    args = parser.parse_args(["run-example", "sales-lead-qualification"])
    args.name = "not-a-real-example"

    from b2b_workflow_simulator.cli import run_example

    exit_code = run_example(args.name, args.cases, args.seed)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_run_example_is_deterministic_for_a_fixed_seed(capsys):
    main(["run-example", "sales-lead-qualification", "--cases", "50", "--seed", "3"])
    first_output = capsys.readouterr().out

    main(["run-example", "sales-lead-qualification", "--cases", "50", "--seed", "3"])
    second_output = capsys.readouterr().out

    assert first_output == second_output


def test_run_example_supports_discrete_engine(capsys):
    exit_code = main(
        ["run-example", "sales-lead-qualification", "--cases", "20", "--engine", "discrete"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Engine: discrete" in output


def test_run_example_rejects_unknown_engine():
    parser = build_parser()

    exit_code = None
    try:
        parser.parse_args(["run-example", "sales-lead-qualification", "--engine", "quantum"])
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code == 2


def test_run_example_supports_invoice_processing(capsys):
    exit_code = main(["run-example", "invoice-processing", "--cases", "20", "--seed", "1"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "invoice-processing" in output


def test_run_example_supports_customer_support_ticket_resolution(capsys):
    exit_code = main(
        ["run-example", "customer-support-ticket-resolution", "--cases", "20", "--seed", "1"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "customer-support-ticket-resolution" in output


def test_run_portfolio_prints_summary_for_each_workflow(capsys):
    exit_code = main(
        [
            "run-portfolio",
            "sales-lead-qualification",
            "invoice-processing",
            "--cases",
            "20",
            "--seed",
            "1",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "sales-lead-qualification" in output
    assert "invoice-processing" in output
    assert "Before Cost" in output


def test_run_portfolio_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import run_portfolio

    exit_code = run_portfolio(["not-a-real-example"], 10, 1)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_compare_portfolio_prints_full_report(capsys):
    exit_code = main(
        [
            "compare-portfolio",
            "sales-lead-qualification",
            "invoice-processing",
            "--cases",
            "30",
            "--seed",
            "1",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "WORKFLOW PORTFOLIO ANALYSIS" in output
    assert "WORKFLOW RANKING" in output
    assert "RECOMMENDED ROLLOUT ORDER" in output


def test_compare_portfolio_writes_html_report_when_requested(tmp_path, capsys):
    html_path = tmp_path / "portfolio.html"
    exit_code = main(
        [
            "compare-portfolio",
            "sales-lead-qualification",
            "invoice-processing",
            "--cases",
            "20",
            "--seed",
            "1",
            "--html-output",
            str(html_path),
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert html_path.exists()
    assert "<!DOCTYPE html>" in html_path.read_text()
    assert "HTML report written" in output


def test_compare_portfolio_supports_rank_by_roi_percentage(capsys):
    exit_code = main(
        [
            "compare-portfolio",
            "sales-lead-qualification",
            "invoice-processing",
            "--cases",
            "20",
            "--seed",
            "1",
            "--rank-by",
            "roi_percentage",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "WORKFLOW RANKING" in output


def test_compare_portfolio_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import compare_portfolio

    exit_code = compare_portfolio(
        ["not-a-real-example"], 10, 1, None, None, "total_cost_savings", None
    )
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_compare_example_prints_full_roi_report(capsys):
    exit_code = main(
        ["compare-example", "sales-lead-qualification", "--cases", "50", "--seed", "1"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "WORKFLOW REDESIGN ANALYSIS" in output
    assert "EXECUTIVE SUMMARY" in output
    assert "RECOMMENDATION" in output


def test_compare_example_includes_payback_with_implementation_cost(capsys):
    main(
        [
            "compare-example",
            "invoice-processing",
            "--cases",
            "100",
            "--seed",
            "2",
            "--implementation-cost",
            "1000",
        ]
    )
    output = capsys.readouterr().out

    assert "payback" in output.lower()


def test_compare_example_supports_arrival_interval(capsys):
    exit_code = main(
        [
            "compare-example",
            "sales-lead-qualification",
            "--cases",
            "30",
            "--seed",
            "1",
            "--arrival-interval",
            "15",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "ACTOR UTILIZATION" in output


def test_compare_example_supports_discrete_engine(capsys):
    exit_code = main(
        [
            "compare-example",
            "sales-lead-qualification",
            "--cases",
            "30",
            "--seed",
            "1",
            "--engine",
            "discrete",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "WORKFLOW REDESIGN ANALYSIS" in output


def test_compare_example_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import compare_example

    exit_code = compare_example("not-a-real-example", 10, 1, None, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_sensitivity_example_prints_table_and_break_even(capsys):
    exit_code = main(
        [
            "sensitivity-example",
            "invoice-processing",
            "--parameter",
            "ai_cost_per_execution",
            "--values",
            "0,5,10,20",
            "--cases",
            "100",
            "--seed",
            "1",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Sensitivity: ai_cost_per_execution" in output
    assert "Break-even" in output


def test_sensitivity_example_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import sensitivity_example

    exit_code = sensitivity_example("not-a-real-example", "ai_error_rate", [0.1], 10, 1, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_sensitivity_example_parses_comma_separated_values():
    from b2b_workflow_simulator.cli import _parse_float_list

    assert _parse_float_list("0.0,0.1,0.2") == [0.0, 0.1, 0.2]


def test_sensitivity_example_rejects_malformed_values():
    from b2b_workflow_simulator.cli import build_parser

    parser = build_parser()
    exit_code = None
    try:
        parser.parse_args(
            [
                "sensitivity-example",
                "invoice-processing",
                "--parameter",
                "ai_error_rate",
                "--values",
                "not-a-number",
            ]
        )
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code == 2


def test_html_report_example_writes_html_file(tmp_path, capsys):
    output_path = tmp_path / "report.html"
    exit_code = main(
        [
            "html-report-example",
            "sales-lead-qualification",
            "--cases",
            "20",
            "--seed",
            "1",
            "--output",
            str(output_path),
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output_path.exists()
    content = output_path.read_text()
    assert content.startswith("<!DOCTYPE html>")
    assert "HTML report written" in output


def test_html_report_example_includes_payback_with_implementation_cost(tmp_path):
    output_path = tmp_path / "report.html"
    main(
        [
            "html-report-example",
            "invoice-processing",
            "--cases",
            "50",
            "--seed",
            "1",
            "--implementation-cost",
            "1000",
            "--output",
            str(output_path),
        ]
    )

    assert "Payback" in output_path.read_text()


def test_html_report_example_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import html_report_example

    exit_code = html_report_example("not-a-real-example", 10, 1, None, None, "out.html")
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_save_example_writes_before_and_after_json(tmp_path):
    output_dir = tmp_path / "workflows"
    exit_code = main(["save-example", "invoice-processing", "--output-dir", str(output_dir)])

    assert exit_code == 0
    before_path = output_dir / "invoice-processing-before.json"
    after_path = output_dir / "invoice-processing-after.json"
    assert before_path.exists()
    assert after_path.exists()
    json.loads(before_path.read_text())
    json.loads(after_path.read_text())


def test_save_example_rejects_unknown_example(tmp_path, capsys):
    from b2b_workflow_simulator.cli import save_example

    exit_code = save_example("not-a-real-example", str(tmp_path))
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_load_example_prints_kpi_summary_for_saved_workflow(tmp_path, capsys):
    output_dir = tmp_path / "workflows"
    main(["save-example", "invoice-processing", "--output-dir", str(output_dir)])
    capsys.readouterr()

    exit_code = main(
        [
            "load-example",
            str(output_dir / "invoice-processing-after.json"),
            "--cases",
            "20",
            "--seed",
            "1",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Loaded workflow" in output
    assert "Completion rate" in output


def test_load_example_reports_error_for_missing_file(tmp_path, capsys):
    missing_path = tmp_path / "does-not-exist.json"

    exit_code = main(["load-example", str(missing_path)])
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Failed to load workflow" in error_output


def test_load_example_reports_error_for_invalid_workflow(tmp_path, capsys):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"not": "a workflow"}))

    exit_code = main(["load-example", str(bad_path)])
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Failed to load workflow" in error_output


def test_export_example_writes_json_files(tmp_path):
    output_dir = tmp_path / "exports"
    exit_code = main(
        [
            "export-example",
            "sales-lead-qualification",
            "--cases",
            "10",
            "--seed",
            "1",
            "--format",
            "json",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    expected_files = [
        "sales-lead-qualification-before-events.json",
        "sales-lead-qualification-after-events.json",
        "sales-lead-qualification-before-kpi.json",
        "sales-lead-qualification-after-kpi.json",
        "sales-lead-qualification-comparison.json",
    ]
    for filename in expected_files:
        file_path = output_dir / filename
        assert file_path.exists()
        json.loads(file_path.read_text())


def test_export_example_writes_csv_comparison_only(tmp_path):
    output_dir = tmp_path / "exports"
    exit_code = main(
        [
            "export-example",
            "invoice-processing",
            "--cases",
            "10",
            "--seed",
            "1",
            "--format",
            "csv",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    csv_path = output_dir / "invoice-processing-comparison.csv"
    assert csv_path.exists()
    assert csv_path.read_text().startswith("metric,before,after,delta,percent_change")


def test_export_example_rejects_unknown_example(tmp_path, capsys):
    from b2b_workflow_simulator.cli import export_example

    exit_code = export_example("not-a-real-example", 10, 1, "json", str(tmp_path), None, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_monte_carlo_example_prints_report(capsys):
    exit_code = main(
        [
            "monte-carlo-example",
            "sales-lead-qualification",
            "--cases",
            "20",
            "--seeds",
            "1,2,3",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "MONTE CARLO REDESIGN COMPARISON" in output
    assert "Seeds: 3" in output


def test_monte_carlo_example_writes_html_file(tmp_path):
    output_path = tmp_path / "mc.html"
    exit_code = main(
        [
            "monte-carlo-example",
            "sales-lead-qualification",
            "--cases",
            "20",
            "--seeds",
            "1,2",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_monte_carlo_example_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import monte_carlo_example

    exit_code = monte_carlo_example("not-a-real-example", 20, [1, 2], None, None, "simple", None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_monte_carlo_example_rejects_bad_seeds_list():
    parser = build_parser()

    exit_code = None
    try:
        parser.parse_args(
            ["monte-carlo-example", "sales-lead-qualification", "--seeds", "not-a-number"]
        )
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code == 2


def test_monte_carlo_portfolio_prints_summary_table(capsys):
    exit_code = main(
        [
            "monte-carlo-portfolio",
            "sales-lead-qualification",
            "invoice-processing",
            "--cases",
            "20",
            "--seeds",
            "1,2,3",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "sales-lead-qualification" in output
    assert "invoice-processing" in output


def test_monte_carlo_portfolio_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import monte_carlo_portfolio

    exit_code = monte_carlo_portfolio(["not-a-real-example"], 20, [1, 2], None, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_sensitivity_grid_example_prints_roi_matrix(capsys):
    exit_code = main(
        [
            "sensitivity-grid-example",
            "sales-lead-qualification",
            "--x-parameter",
            "ai_error_rate",
            "--x-values",
            "0.05,0.1",
            "--y-parameter",
            "ai_cost_per_execution",
            "--y-values",
            "0.5,1.0",
            "--cases",
            "20",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "MULTI-PARAMETER SENSITIVITY ANALYSIS" in output
    assert "ROI MATRIX" in output


def test_sensitivity_grid_example_writes_html_file(tmp_path):
    output_path = tmp_path / "grid.html"
    exit_code = main(
        [
            "sensitivity-grid-example",
            "sales-lead-qualification",
            "--x-parameter",
            "ai_error_rate",
            "--x-values",
            "0.05,0.1",
            "--y-parameter",
            "ai_cost_per_execution",
            "--y-values",
            "0.5,1.0",
            "--cases",
            "20",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_sensitivity_grid_example_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import sensitivity_grid_example

    exit_code = sensitivity_grid_example(
        "not-a-real-example",
        "ai_error_rate",
        [0.1],
        "ai_cost_per_execution",
        [0.5],
        20,
        1,
        None,
        None,
    )
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_capacity_analysis_prints_report(capsys):
    exit_code = main(
        [
            "capacity-analysis",
            "sales-lead-qualification",
            "--variant",
            "after",
            "--cases",
            "50",
            "--arrival-interval",
            "5.0",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "CAPACITY PLANNING ANALYSIS" in output
    assert "STAFFING RECOMMENDATIONS" in output


def test_capacity_analysis_writes_html_file(tmp_path):
    output_path = tmp_path / "capacity.html"
    exit_code = main(
        [
            "capacity-analysis",
            "sales-lead-qualification",
            "--cases",
            "50",
            "--arrival-interval",
            "5.0",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_capacity_analysis_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import capacity_analysis

    exit_code = capacity_analysis("not-a-real-example", "after", 20, 1, None, 0.75, 0.9, 0.4, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_team_utilization_prints_actor_utilization(capsys):
    exit_code = main(
        [
            "team-utilization",
            "sales-lead-qualification",
            "--variant",
            "after",
            "--cases",
            "50",
            "--arrival-interval",
            "5.0",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Actor utilization" in output


def test_team_utilization_without_arrival_interval_reports_no_data(capsys):
    exit_code = main(["team-utilization", "sales-lead-qualification", "--cases", "20"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "No capacity data available" in output


def test_team_utilization_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import team_utilization

    exit_code = team_utilization("not-a-real-example", "after", 20, 1, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_policy_analysis_prints_report(capsys):
    exit_code = main(["policy-analysis", "invoice-processing", "--variant", "after"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "POLICY COMPLIANCE ANALYSIS" in output


def test_policy_analysis_writes_html_file(tmp_path):
    output_path = tmp_path / "policy.html"
    exit_code = main(
        [
            "policy-analysis",
            "invoice-processing",
            "--variant",
            "after",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_policy_analysis_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import policy_analysis

    exit_code = policy_analysis("not-a-real-example", "after", None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_compliance_analysis_prints_report(capsys):
    exit_code = main(["compliance-analysis", "invoice-processing", "--variant", "after"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "COMPLIANCE ANALYSIS" in output


def test_compliance_analysis_writes_html_file(tmp_path):
    output_path = tmp_path / "compliance.html"
    exit_code = main(
        [
            "compliance-analysis",
            "invoice-processing",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_compliance_analysis_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import compliance_analysis

    exit_code = compliance_analysis("not-a-real-example", "after", None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_risk_analysis_prints_report(capsys):
    exit_code = main(["risk-analysis", "invoice-processing", "--variant", "after", "--cases", "50"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Organizational Risk Assessment" in output
    assert "Overall risk score" in output


def test_risk_analysis_writes_html_file(tmp_path):
    output_path = tmp_path / "risk.html"
    exit_code = main(
        [
            "risk-analysis",
            "invoice-processing",
            "--cases",
            "50",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_risk_analysis_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import risk_analysis

    exit_code = risk_analysis("not-a-real-example", "after", 20, 1, None, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_readiness_analysis_prints_report(capsys):
    exit_code = main(
        ["readiness-analysis", "invoice-processing", "--variant", "after", "--cases", "50"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "AI Adoption Assessment" in output
    assert "Readiness index" in output


def test_readiness_analysis_writes_html_file(tmp_path):
    output_path = tmp_path / "readiness.html"
    exit_code = main(
        [
            "readiness-analysis",
            "invoice-processing",
            "--cases",
            "50",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_readiness_analysis_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import readiness_analysis

    exit_code = readiness_analysis("not-a-real-example", "after", 20, 1, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_recommend_redesign_prints_report(capsys):
    exit_code = main(
        ["recommend-redesign", "invoice-processing", "--variant", "after", "--cases", "50"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Recommendations:" in output


def test_recommend_redesign_writes_html_file(tmp_path):
    output_path = tmp_path / "recommend.html"
    exit_code = main(
        [
            "recommend-redesign",
            "invoice-processing",
            "--cases",
            "50",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_recommend_redesign_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import recommend_redesign

    exit_code = recommend_redesign("not-a-real-example", "after", 20, 1, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


def test_executive_report_prints_report(capsys):
    exit_code = main(["executive-report", "invoice-processing", "--cases", "50"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "EXECUTIVE ASSESSMENT REPORT" in output
    assert "KPI SUMMARY" in output
    assert "ROI" in output
    assert "AI ADOPTION ASSESSMENT" in output


def test_executive_report_writes_html_file(tmp_path):
    output_path = tmp_path / "executive.html"
    exit_code = main(
        [
            "executive-report",
            "invoice-processing",
            "--cases",
            "50",
            "--html-output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("<!DOCTYPE html>")


def test_executive_report_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import executive_report

    exit_code = executive_report("not-a-real-example", 20, 1, None, None, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output
