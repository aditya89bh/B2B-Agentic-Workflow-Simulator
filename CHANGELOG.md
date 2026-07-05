# Changelog

## Phase 1 - Foundation

Established the core domain model and a working end-to-end simulation.

- Core primitives: `Node`, `Edge`, `Actor`, `HumanActor`, `AIAgentActor`,
  `Task`, `Event`.
- `Workflow` graph model with structural validation.
- `KPIResult` aggregation object with derived business metrics.
- `SimulationRunner`: seeded, reproducible execution engine.
- Bundled example: sales lead qualification, before (human-only) and
  after (AI-augmented) variants.
- `b2b-simulator` CLI with a `run-example` command that prints a
  before/after KPI comparison.
- Unit test coverage for every primitive, the workflow model, the
  simulation runner, the example workflow, and the CLI.
- Project scaffolding: `pyproject.toml`, README, architecture and
  getting-started docs, MIT license.
