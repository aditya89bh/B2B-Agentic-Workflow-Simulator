# Quickstart

## Installation

```bash
git clone https://github.com/aditya89bh/B2B-Agentic-Workflow-Simulator
cd B2B-Agentic-Workflow-Simulator
pip install -e ".[dev]"
b2b-simulator --version
```

Expected output: `b2b-workflow-simulator 1.0.0`

## Your first scenario

```bash
# List available scenarios
b2b-simulator list-scenarios

# Run a healthcare prior-auth scenario
b2b-simulator run-example healthcare-prior-authorization --cases 300

# One-page stakeholder summary
b2b-simulator executive-snapshot healthcare-prior-authorization \
  --cases 300 --implementation-cost 18000

# Full consulting packet (10 files)
b2b-simulator consultant-packet healthcare-prior-authorization \
  --cases 300 --implementation-cost 18000 --output-dir packet/

ls packet/
```

## Compare all scenarios

```bash
b2b-simulator scenario-matrix
b2b-simulator scenario-matrix --profile conservative --format json
```

## Customize for a client

```bash
# See bundled sample configs
b2b-simulator list-configs

# Validate a config
b2b-simulator validate-config \
  src/b2b_workflow_simulator/examples/data/configs/healthcare-prior-auth-small-plan.json

# Run the configured scenario
b2b-simulator run-config \
  src/b2b_workflow_simulator/examples/data/configs/healthcare-prior-auth-small-plan.json
```

## Generate calibration questionnaire

```bash
b2b-simulator calibration-template healthcare-prior-authorization \
  --output healthcare_calibration.md
```

## Run tests

```bash
pytest                   # full suite (~1822 tests, ~8s)
ruff check .             # lint
python -m build          # build sdist + wheel
```
