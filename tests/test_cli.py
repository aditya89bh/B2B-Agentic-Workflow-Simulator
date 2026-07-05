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
