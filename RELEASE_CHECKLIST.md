# v1.0.0 Release Checklist

Complete every item before tagging a release.

## Code quality

- [ ] `pytest` passes with no failures: `pytest`
- [ ] Zero ruff lint errors: `ruff check .`
- [ ] Package builds cleanly: `python -m build`
- [ ] Docs build in strict mode: `python -m mkdocs build --strict` (requires `pip install -e ".[docs]"`)

## Version checks

- [ ] `pyproject.toml` `version` matches release tag
- [ ] `src/b2b_workflow_simulator/__init__.py` `__version__` matches
- [ ] `b2b-simulator --version` output matches
- [ ] CHANGELOG.md entry for this version exists
- [ ] `docs/release_notes.md` covers this version

## Package data

- [ ] `examples/data/*.json` included: `pip install -e . && python -c "from b2b_workflow_simulator.examples import saas_org"`
- [ ] `examples/data/assumptions/**/*.json` included
- [ ] `examples/data/configs/*.json` included

## Generated outputs

- [ ] Run `b2b-simulator generate-example-gallery --output-dir examples/outputs`
- [ ] Run `b2b-simulator generate-release-examples --output-dir examples/outputs/final_release`
- [ ] Verify outputs directory is committed

## Git history

- [ ] All commits use correct author email: `git log --all --format="%ae" | sort -u`
- [ ] Zero Cursor / Co-authored-by references: `git log --all --format="%H %an %ae %s%n%b" | grep -iE "cursor|co-authored"`
- [ ] Working tree is clean: `git status`
- [ ] `main` is synced with `origin/main`: `git rev-list --left-right --count origin/main...main`

## CI

- [ ] CI passes on the release commit: check `.github/workflows/ci.yml`
- [ ] Docs workflow builds (if configured): `.github/workflows/docs.yml`

## Tag and release

- [ ] Create annotated tag: `git tag -a v1.0.0 -m "B2B Agentic Workflow Simulator v1.0.0"`
- [ ] Push tag: `git push origin v1.0.0`
- [ ] Verify tag is visible: `git tag -l v*`
- [ ] Create GitHub Release from tag (manual step in GitHub UI or via `gh release create`)

## Post-release

- [ ] Bump `pyproject.toml` version to `1.1.0.dev0` for next development cycle
- [ ] Update `__init__.py` `__version__` to match
