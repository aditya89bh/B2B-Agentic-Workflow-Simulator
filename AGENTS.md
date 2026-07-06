# AGENTS.md

## Cursor Cloud specific instructions

This is a self-contained, pure-Python CLI tool (`b2b_workflow_simulator`, `src/`-layout). It has **no runtime dependencies**, no services, no database, and no network/ports — it is a stateless CLI that runs, computes, prints/writes output, and exits.

### Environment
- Python 3.10+ (VM has 3.12). Work inside the virtualenv at `.venv` (created by the update script). Activate with `source .venv/bin/activate`, or call tools via `.venv/bin/<tool>`.
- The package is installed editable (`pip install -e ".[dev]"`), so source edits under `src/` take effect immediately with no reinstall.

### Lint / test / build / run (standard commands, see `README.md` and `pyproject.toml`)
- Lint: `ruff check .`
- Test: `pytest` (≈630 tests, runs in ~1–2s)
- Build: `python -m build`
- Run the CLI: `b2b-simulator <subcommand>` (e.g. `b2b-simulator run-example sales-lead-qualification --cases 300 --seed 7`). See `b2b-simulator --help` for all subcommands.

### Notes
- There is nothing to "start up" — do not look for a server/daemon. End-to-end testing is just running the CLI and/or `pytest`.
- HTML/JSON/CSV outputs are only written when an `--output`/`--output-dir`/`--html-output` flag is passed; otherwise output goes to stdout.
