"""Bottleneck heatmap: visualize pressure across workflow nodes and resources.

A heatmap scores each node and shared resource on multiple pressure
dimensions (duration, wait, failure, escalation) and renders them as a
ranked grid so bottlenecks leap out at a glance.  Output is either a
plain-text table or a self-contained SVG heat grid.

No external dependencies.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult
from b2b_workflow_simulator.workflow import Workflow

_PRESSURE_LEVELS = (
    (80.0, "critical", "#b22222"),
    (60.0, "high",     "#e57c00"),
    (40.0, "moderate", "#f0c040"),
    (20.0, "low",      "#70ad47"),
    (0.0,  "minimal",  "#d4edda"),
)


def _pressure_color(pressure: float) -> str:
    for threshold, _, color in _PRESSURE_LEVELS:
        if pressure >= threshold:
            return color
    return _PRESSURE_LEVELS[-1][2]


def _pressure_level(pressure: float) -> str:
    for threshold, level, _ in _PRESSURE_LEVELS:
        if pressure >= threshold:
            return level
    return _PRESSURE_LEVELS[-1][1]


def _normalize(values: dict[str, float]) -> dict[str, float]:
    """Normalize values to 0–100 scale."""
    if not values:
        return {}
    max_v = max(values.values())
    if max_v == 0:
        return {k: 0.0 for k in values}
    return {k: v / max_v * 100.0 for k, v in values.items()}


@dataclass(frozen=True)
class HeatmapCell:
    """One row in the bottleneck heatmap.

    Attributes:
        label: Human-readable name of the node/resource.
        category: ``"node"`` or ``"resource"``.
        duration_pressure: 0–100 score for time consumed.
        wait_pressure: 0–100 score for queue wait time.
        failure_pressure: 0–100 score for failure rate.
        escalation_pressure: 0–100 score for AI escalation rate.
        overall_pressure: Weighted composite of the four signals (0–100).
    """

    label: str
    category: str
    duration_pressure: float = 0.0
    wait_pressure: float = 0.0
    failure_pressure: float = 0.0
    escalation_pressure: float = 0.0
    overall_pressure: float = 0.0

    @property
    def level(self) -> str:
        """Qualitative pressure level string."""
        return _pressure_level(self.overall_pressure)


@dataclass
class BottleneckHeatmap:
    """Bottleneck pressure map for a workflow run.

    Attributes:
        workflow_name: Name of the workflow.
        cells: All heatmap cells, sorted by overall_pressure descending.
        assumptions: Plain-text notes about how pressure was computed.
    """

    workflow_name: str
    cells: list[HeatmapCell] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def top(self, n: int = 5) -> list[HeatmapCell]:
        """Return the ``n`` highest-pressure cells."""
        return sorted(self.cells, key=lambda c: c.overall_pressure, reverse=True)[:n]


def build_bottleneck_heatmap(
    workflow: Workflow,
    kpi: KPIResult,
    shared_resources=None,
) -> BottleneckHeatmap:
    """Build a :class:`BottleneckHeatmap` from simulation KPI data.

    Args:
        workflow: The workflow that was simulated.
        kpi: A ``KPIResult`` from a simulation run.
        shared_resources: Optional ``SharedResourcePool``; when provided,
            resource contention is included as additional heatmap cells.

    Returns:
        A :class:`BottleneckHeatmap` with cells sorted by pressure.
    """
    heatmap = BottleneckHeatmap(workflow_name=workflow.name)
    total_cases = max(kpi.total_cases, 1)

    raw_duration = {
        nid: kpi.node_total_duration_minutes.get(nid, 0.0)
        for nid in workflow.nodes
    }
    raw_wait = {
        nid: kpi.actor_wait_minutes.get(workflow.get_node(nid).actor_id, 0.0)
        for nid in workflow.nodes
    }
    raw_failure = {
        nid: kpi.node_failure_counts.get(nid, 0) / total_cases * 100.0
        for nid in workflow.nodes
    }
    raw_escalation = {
        nid: kpi.total_escalations / total_cases * 100.0
        for nid in workflow.nodes
    }

    norm_dur = _normalize(raw_duration)
    norm_wait = _normalize(raw_wait)
    norm_fail = _normalize(raw_failure)
    norm_esc = _normalize(raw_escalation)

    for node_id, node in workflow.nodes.items():
        visit_count = kpi.node_visit_counts.get(node_id, 0)
        if visit_count == 0:
            continue
        d = norm_dur.get(node_id, 0.0)
        w = norm_wait.get(node_id, 0.0)
        f = norm_fail.get(node_id, 0.0)
        e = norm_esc.get(node_id, 0.0)
        overall = d * 0.40 + w * 0.25 + f * 0.25 + e * 0.10
        heatmap.cells.append(HeatmapCell(
            label=node.name,
            category="node",
            duration_pressure=d,
            wait_pressure=w,
            failure_pressure=f,
            escalation_pressure=e,
            overall_pressure=overall,
        ))

    if shared_resources is not None:
        for contention in shared_resources.all_contentions():
            if contention.total_demand_minutes == 0:
                continue
            ratio = min(100.0, contention.contention_ratio * 100.0)
            heatmap.cells.append(HeatmapCell(
                label=f"[Resource] {contention.resource_name}",
                category="resource",
                duration_pressure=ratio,
                wait_pressure=ratio if contention.is_bottleneck else 0.0,
                failure_pressure=0.0,
                escalation_pressure=0.0,
                overall_pressure=ratio,
            ))

    heatmap.cells.sort(key=lambda c: c.overall_pressure, reverse=True)
    heatmap.assumptions += [
        "Duration pressure: node total duration / max across nodes (normalized).",
        "Wait pressure: actor wait minutes / max across actors (normalized).",
        "Failure pressure: node failure count / total cases (normalized).",
        "Escalation pressure: total escalations / total cases (normalized).",
        "Overall: duration 40% + wait 25% + failure 25% + escalation 10%.",
    ]
    return heatmap


def heatmap_to_text(heatmap: BottleneckHeatmap) -> str:
    """Render a :class:`BottleneckHeatmap` as a plain-text table.

    Args:
        heatmap: A computed bottleneck heatmap.

    Returns:
        A multi-line plain-text string.
    """
    if not heatmap.cells:
        return f"BOTTLENECK HEATMAP: {heatmap.workflow_name}\n\nNo data available."

    col_label = max(len(c.label) for c in heatmap.cells) + 2
    lines: list[str] = [
        "=" * 70,
        f"BOTTLENECK HEATMAP: {heatmap.workflow_name}",
        "=" * 70,
        "",
        f"{'Node/Resource':<{col_label}} {'Overall':>8} {'Duration':>9} "
        f"{'Wait':>6} {'Failure':>8} {'Level':<10}",
        "-" * 70,
    ]
    for cell in heatmap.cells:
        bar = "█" * int(cell.overall_pressure / 10) + "░" * (10 - int(cell.overall_pressure / 10))
        lines.append(
            f"{cell.label:<{col_label}} {cell.overall_pressure:>7.1f}% "
            f"{cell.duration_pressure:>8.1f}% "
            f"{cell.wait_pressure:>5.1f}% "
            f"{cell.failure_pressure:>7.1f}% "
            f"{cell.level:<10}  {bar}"
        )
    lines += [
        "",
        "Assumptions:",
        *[f"  - {a}" for a in heatmap.assumptions],
    ]
    return "\n".join(lines)


def heatmap_to_svg(
    heatmap: BottleneckHeatmap,
    width: int = 720,
    row_height: int = 32,
    top_n: int = 10,
) -> str:
    """Render a :class:`BottleneckHeatmap` as a standalone SVG heatmap grid.

    Shows the top ``top_n`` cells by overall pressure, with color-coded cells
    for each pressure dimension.

    Args:
        heatmap: A computed bottleneck heatmap.
        width: SVG canvas width in pixels.
        row_height: Height of each data row in pixels.
        top_n: Maximum number of rows to display.

    Returns:
        A self-contained SVG string.
    """
    cells = heatmap.cells[:top_n]
    if not cells:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="60">'
            f'<text x="10" y="30" font-family="Arial,sans-serif" font-size="12">'
            f'No bottleneck data available.</text></svg>'
        )

    cols = ["Overall", "Duration", "Wait", "Failure", "Escalation"]
    n_cols = len(cols)
    margin_left = 200
    margin_top = 60
    col_width = (width - margin_left - 20) // n_cols
    total_height = margin_top + len(cells) * row_height + 80

    title = html.escape(f"Bottleneck Heatmap: {heatmap.workflow_name}", quote=True)
    svg_parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{total_height}" '
        f'viewBox="0 0 {width} {total_height}">',
        f'  <rect width="{width}" height="{total_height}" fill="#ffffff"/>',
        f'  <text x="{width//2}" y="22" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="14" font-weight="bold" '
        f'fill="#1a1a1a">{title}</text>',
    ]

    for ci, col_name in enumerate(cols):
        cx = margin_left + ci * col_width + col_width // 2
        svg_parts.append(
            f'  <text x="{cx}" y="50" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="10" '
            f'font-weight="bold" fill="#333">{html.escape(col_name)}</text>'
        )

    for ri, cell in enumerate(cells):
        y = margin_top + ri * row_height
        pressures = [
            cell.overall_pressure,
            cell.duration_pressure,
            cell.wait_pressure,
            cell.failure_pressure,
            cell.escalation_pressure,
        ]
        label = html.escape(cell.label, quote=True)
        svg_parts.append(
            f'  <text x="{margin_left - 6}" y="{y + row_height//2 + 4}" '
            f'text-anchor="end" font-family="Arial,sans-serif" '
            f'font-size="10" fill="#1a1a1a">{label}</text>'
        )
        for ci, pressure in enumerate(pressures):
            cx = margin_left + ci * col_width
            color = _pressure_color(pressure)
            pct = html.escape(f"{pressure:.0f}%", quote=True)
            svg_parts.append(
                f'  <rect x="{cx + 2}" y="{y + 2}" '
                f'width="{col_width - 4}" height="{row_height - 4}" '
                f'fill="{color}" rx="3"/>'
            )
            svg_parts.append(
                f'  <text x="{cx + col_width//2}" y="{y + row_height//2 + 4}" '
                f'text-anchor="middle" font-family="Arial,sans-serif" '
                f'font-size="10" fill="#1a1a1a">{pct}</text>'
            )

    legend_y = margin_top + len(cells) * row_height + 12
    svg_parts.append(
        f'  <text x="{margin_left}" y="{legend_y}" '
        f'font-family="Arial,sans-serif" font-size="9" fill="#666">'
        f'Colors: critical ≥80% | high ≥60% | moderate ≥40% | low ≥20% | minimal</text>'
    )
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


__all__ = [
    "BottleneckHeatmap",
    "HeatmapCell",
    "build_bottleneck_heatmap",
    "heatmap_to_svg",
    "heatmap_to_text",
]
