# JSON Workflow Definitions

Every `Workflow` can be serialized to and loaded from a plain JSON file,
independent of the Python code that originally built it. This makes it
possible to author or hand-edit a workflow definition, check it into
version control as a readable artifact, or share it with someone who
does not want to write Python.

## Saving and loading

```python
from b2b_workflow_simulator.workflow_io import load_workflow, save_workflow

save_workflow(my_workflow, "workflows/my-workflow.json")
loaded = load_workflow("workflows/my-workflow.json")
```

Or from the CLI:

```bash
b2b-simulator save-example invoice-processing --output-dir workflows
b2b-simulator load-example workflows/invoice-processing-after.json --cases 200
```

`save-example` writes both the before and after variants of a bundled
example. `load-example` accepts *any* workflow JSON file -- not just
ones this project produced -- validates its structure, and prints a
simulated KPI summary.

## Document structure

```json
{
  "workflow_id": "invoice-processing-after",
  "name": "Invoice Processing (After: AI-Augmented)",
  "description": "...",
  "entry_node_id": "invoice_intake",
  "actors": [
    {
      "actor_id": "intake_agent",
      "name": "Invoice Intake Agent",
      "type": "ai_agent",
      "available_hours_per_day": 24.0,
      "cost_per_execution": 0.12,
      "speed_multiplier": 0.06,
      "error_rate": 0.02,
      "escalation_rate": 0.03,
      "autonomy_level": "autonomous"
    }
  ],
  "nodes": [
    {
      "node_id": "invoice_intake",
      "name": "Invoice Intake",
      "actor_id": "intake_agent",
      "description": "...",
      "base_duration_minutes": 8.0,
      "duration_model": { "kind": "fixed", "minimum": null, "maximum": null, "mode": null },
      "is_terminal": false,
      "metadata": {}
    }
  ],
  "edges": [
    { "source": "invoice_intake", "target": "validation", "probability": 1.0, "condition": "" }
  ]
}
```

- `actors[].type` is `"human"` or `"ai_agent"`. Numeric fields differ by
  type: `hourly_cost`/`speed_multiplier`/`error_rate` for humans;
  `cost_per_execution`/`speed_multiplier`/`error_rate`/`escalation_rate`/`autonomy_level`
  for AI agents. Both accept `available_hours_per_day`.
- `nodes[].duration_model.kind` is `"fixed"`, `"uniform"`, or
  `"triangular"`; see `docs/capacity_modeling.md` for what each does.
  Omitting `duration_model` defaults to a fixed duration.
- `edges[].probability` defaults to `1.0` if omitted; all outgoing
  edges from the same node must still sum to `1.0` when the workflow is
  validated.

## Validation

Loading a workflow validates its structure before building any object,
using `validate_workflow_dict()`. This is deliberately implemented as a
direct, stdlib-only tree walk (`isinstance` checks with descriptive
error messages) rather than a dependency on a JSON Schema library --
the structure is simple enough that hand-written validation is both
sufficient and easier to read:

```python
from b2b_workflow_simulator.workflow_io import WorkflowSchemaError, load_workflow

try:
    workflow = load_workflow("workflows/broken.json")
except WorkflowSchemaError as exc:
    print(f"Invalid workflow definition: {exc}")
```

Errors name exactly where the problem is, for example:

```
actors[2].hourly_cost must be a number
nodes[0].duration_model.kind must be one of ('fixed', 'uniform', 'triangular')
edges[3] is missing required field 'target'
```

`load_workflow()` can also raise a plain `ValueError` if the document
is structurally valid JSON but internally inconsistent in a way schema
validation cannot catch alone -- for example, a node referencing an
actor id that was never declared (`Workflow.add_node()` checks this).

## Sample workflows

Every bundled example ships a ready-made JSON definition under
`src/b2b_workflow_simulator/examples/data/`:

- `sales_lead_qualification_before.json` / `_after.json`
- `invoice_processing_before.json` / `_after.json`
- `customer_support_ticket_resolution_before.json` / `_after.json`

These are generated directly from the corresponding Python `build_*_workflow()`
functions (`workflow_to_dict(build_before_workflow())`, written to
disk), so the two representations cannot silently drift apart; a test
loads and validates every sample file. They double as a reference for
the expected JSON shape when authoring a new workflow definition by
hand.
