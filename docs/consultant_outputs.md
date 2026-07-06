# Consultant Outputs

Every simulation result can be exported as a stakeholder-ready deliverable.

## Executive snapshot

One-page summary with decision headline, KPI table, ROI, top 3 bottlenecks, top 3 risks, recommendations, assumptions, and next steps.

```bash
b2b-simulator executive-snapshot invoice-processing \
  --cases 300 --implementation-cost 8000

b2b-simulator executive-snapshot invoice-processing \
  --cases 300 --implementation-cost 8000 --html-output snapshot.html
```

## Consultant packet

Ten-file deliverable directory:

```bash
b2b-simulator consultant-packet invoice-processing \
  --cases 300 --implementation-cost 8000 --output-dir packet/
```

Contents: `README.md`, `executive_snapshot.txt`, `executive_snapshot.html`, `workflow_before.mmd`, `workflow_after.mmd`, `roi_waterfall.svg`, `bottleneck_heatmap.svg`, `kpi_summary.json`, `assumptions.json`, `recommendations.txt`.

## ROI waterfall

```bash
b2b-simulator roi-waterfall invoice-processing \
  --cases 300 --implementation-cost 8000 --format svg --output roi.svg
```

## Bottleneck heatmap

```bash
b2b-simulator bottleneck-heatmap invoice-processing \
  --cases 500 --arrival-interval 10 --format svg --output heatmap.svg
```

## Workflow visualization

```bash
b2b-simulator visualize-workflow invoice-processing --format mermaid
b2b-simulator visualize-workflow invoice-processing --format text
```

Mermaid output can be pasted into [mermaid.live](https://mermaid.live) or embedded in Markdown.

## Case-study directory

Full deliverable tree for one or all scenarios across all profiles:

```bash
b2b-simulator generate-case-studies --output-dir case_studies/
b2b-simulator generate-case-studies --scenario it-support-triage --profiles base,conservative
```

Each scenario directory contains executive snapshots (3 profiles), SVGs, Mermaid diagrams, KPI JSON, and `consultant_packet_<profile>/` subdirectories.

## Configured case study

Client-specific case study with config diff:

```bash
b2b-simulator config-case-study path/to/config.json --output-dir case_study/
```

Adds `config.json`, `config_diff.txt`, and `config_diff.json` to the standard case-study artifacts.

## Org-level reports

```bash
b2b-simulator org-executive-report --cases 200 --html-output org_report.html
b2b-simulator scenario-matrix --format json --output matrix.json
```
