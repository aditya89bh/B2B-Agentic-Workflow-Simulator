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
pytest                # run the full test suite (~1822 tests, ~8s)
ruff check .          # lint (zero errors required)
python -m build       # build sdist + wheel
b2b-simulator --help  # CLI entry point
```

## Docs build (optional)

```bash
pip install -e ".[docs]"
python -m mkdocs build --strict
```

## Commit conventions

- Use conventional-commit prefixes: `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `style`, `perf`.
- Subject line under 72 characters, imperative mood.
- Do not include tool, vendor, or AI assistant references in commit messages.
- Do not add `Co-authored-by` trailers.
- Author name and email must match your own identity.

## PR checklist

- [ ] `pytest` passes with no failures
- [ ] `ruff check .` passes with no errors
- [ ] `python -m build` succeeds
- [ ] New behavior is covered by tests
- [ ] Backward compatibility maintained
- [ ] Docstrings updated if public API changed

## Architecture

See `docs/architecture.md` for the layered design.  Short version:

- `primitives/` → `workflow.py` → `simulation.py` → `kpi.py`
- Analysis layers (redesign, portfolio, sensitivity, Monte Carlo, governance, risk)
- Phase 6 org layer (org_model, budget, shared_resources, growth, health)
- Phase 7 output layer (visualization, waterfall, heatmap, snapshot, packet)
- Phase 8 scenario library (scenarios, case_studies, scenario_matrix)
- Phase 9 customization layer (scenario_config, config_diff, calibration, configured_case_study)
- `cli.py` and `html_report.py` depend on everything above them
