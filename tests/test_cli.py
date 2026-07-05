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


def test_compare_example_rejects_unknown_example(capsys):
    from b2b_workflow_simulator.cli import compare_example

    exit_code = compare_example("not-a-real-example", 10, 1, None, None)
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output


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

    exit_code = export_example(
        "not-a-real-example", 10, 1, "json", str(tmp_path), None, None
    )
    error_output = capsys.readouterr().err

    assert exit_code == 1
    assert "Unknown example" in error_output
