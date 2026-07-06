# Release Notes

## v1.0.0 (2026-07-06)

First production-stable release of the B2B Agentic Workflow Simulator.

### What's included

**Core simulation (Phases 1–4)**
- Before/after workflow simulation with seeded, reproducible results
- KPI aggregation: completion rate, failure rate, cost per case, cycle time, wait time, escalation rate
- Redesign diff with ROI and payback analysis
- WorkflowPortfolio for multi-workflow ranking
- Sensitivity sweeps (1D and 2D grid)
- Monte Carlo comparison across seeds
- Capacity-aware scheduling with ActorPool support
- Simple and discrete-event simulation engines
- JSON workflow persistence
- `collect_events=False` mode for memory-efficient large runs

**Governance and risk (Phase 5)**
- Business policy engine (7 policy types)
- Compliance engine (7 requirement types)
- SLA engine (deadline tracking, breach analysis, financial penalties)
- Organizational risk scoring (6 categories, explainable factors)
- Recommendation engine (10 recommendation kinds)
- AI adoption readiness assessment
- Executive assessment report bundling all Phase 5 analyses

**Organizational digital twin (Phase 6)**
- Organization model (departments, teams, roles, reporting lines)
- Budget model (5 categories, utilization, overrun detection)
- Shared resource pool (contention ratios, overload risk)
- CrossWorkflowSimulator with resource usage wiring
- Restructuring scenario evaluation (7 scenario types, org-aware heuristics)
- Growth projection engine (12-month forecast, breaking-point detection)
- Organizational health score (8 dimensions, A–F grade)
- Org-level executive report

**Visualization and consulting output (Phase 7)**
- Mermaid flowchart and plain-text workflow visualization
- ROI waterfall generator (text + SVG)
- Bottleneck heatmap (text + SVG, 4 pressure dimensions)
- Executive snapshot (text + HTML, one-page)
- AssumptionProfile JSON-serializable configuration with behavioral multipliers
- Consultant packet export (10-file directory)
- Example gallery generation

**Industry scenario library (Phase 8)**
- 11 registered scenarios across 7 industries
- Healthcare, Insurance, HR, Procurement, Legal, IT, Finance, Customer Success, Sales
- Scenario registry with category constants and lookup API
- Case-study generator (full deliverable tree per scenario, 3 profiles)
- Scenario comparison matrix (text + JSON)
- 33 assumption profile JSON files (11 scenarios × 3 profiles)

**Scenario customization and calibration (Phase 9)**
- ScenarioConfig dataclass with ActorOverride, NodeOverride, EdgeOverride
- validate_scenario_config (checks IDs, probability sums, value bounds)
- apply_scenario_config (non-mutating, produces configured workflows)
- 6 bundled sample configs (healthcare, insurance, HR, procurement, legal, IT)
- Config diff with high-risk assumption warnings
- 8-section calibration questionnaire template
- Configured case-study export with config diff
- 9 new CLI commands

**Release hardening (Phase 10)**
- Version bumped to 1.0.0
- Production/Stable classifier
- `--version` CLI flag
- MkDocs documentation site
- CLI reference for all 46+ commands
- Golden-path walkthrough
- Deterministic release example outputs
- Documentation consistency tests
- Release smoke tests
- RELEASE_CHECKLIST.md
- v1.0.0 annotated tag

### Known limitations

See `docs/limitations.md` for a complete list.  Key items:

- All outputs are directional simulation estimates — not validated operational measurements.
- Scenarios use representative industry approximations; calibrate with real data.
- In-simulation governance enforcement (Phase 11+) is not yet implemented.
- Web UI workflow authoring (Phase 11+) is not yet implemented.
- Multi-currency scheduling (Phase 11+) is not yet implemented.

### Upgrade notes

This is the first production release; no upgrade from a prior version is required.

### Validation status

- 1822+ tests passing across Python 3.10, 3.11, 3.12
- Zero ruff lint errors
- Package builds cleanly (`python -m build`)
- MkDocs site builds in strict mode

---

## Earlier phases (development history)

See `CHANGELOG.md` for detailed per-phase release notes covering Phases 1–9.
