# Contributing

## Local setup

```bash
git clone https://github.com/aditya89bh/B2B-Agentic-Workflow-Simulator
cd B2B-Agentic-Workflow-Simulator
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Standard commands

```bash
pytest                # run the full test suite (~946 tests, ~2s)
ruff check .          # lint
python -m build       # build sdist + wheel
b2b-simulator --help  # CLI entry point
```

## Running a subset of tests

```bash
pytest tests/test_simulation.py          # one file
pytest -k "test_kpi_parity"              # by name pattern
pytest tests/ -x                         # stop on first failure
```

## Making changes

1. Work on `main` for small, well-scoped changes, or create a feature branch for anything larger.
2. Keep changes small and focused.  Each commit should do exactly one thing.
3. Add tests for every behavioral change.  The test suite should pass before you open a PR.
4. Run `ruff check .` before committing.  The CI pipeline enforces zero lint errors.

## Commit hygiene

- Write commit messages in the imperative mood: `feat: add X`, `fix: correct Y`, `test: cover Z`, `docs: update W`.
- Use conventional-commit prefixes: `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `style`, `perf`.
- Keep the subject line under 72 characters.
- Do not include tool, vendor, or AI assistant references in commit messages or bodies.
- Do not add `Co-authored-by` trailers.
- Author name and email must match your own identity.

## PR checklist

- [ ] `pytest` passes with no failures
- [ ] `ruff check .` passes with no errors
- [ ] `python -m build` succeeds
- [ ] New behavior is covered by tests
- [ ] Existing tests are not broken
- [ ] Commit messages follow the conventions above
- [ ] Backward compatibility is maintained (no removed public API, no changed defaults)
- [ ] Docstrings are updated if the public API changed

## Architecture overview

See `docs/architecture.md` for the layered design.  The short version:
- `primitives/` → `workflow.py` → `simulation.py` → `kpi.py`
- Analysis layers (`redesign`, `portfolio`, `sensitivity`, `monte_carlo`, `capacity_planning`, `policy`, `compliance`, `sla`, `risk`, `recommendation`, `ai_adoption`) depend only on lower layers.
- Phase 6 org layer (`org_model`, `budget`, `shared_resources`, `cross_workflow`, `restructuring`, `growth`, `org_health`, `org_report`) depends on the simulation stack but nothing in Phase 6 imports from Phase 5 analysis layers.
- `cli.py` and `html_report.py` depend on everything above them but nothing depends on them.
