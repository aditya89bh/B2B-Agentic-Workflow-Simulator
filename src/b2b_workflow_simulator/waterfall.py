"""ROI waterfall: decompose the savings from a workflow redesign into named steps.

A waterfall breaks the net ROI number into its constituent parts so
stakeholders can see *where* the savings come from and *what* they are
paying for.  The typical structure is:

    Baseline cost  ────────────────────────────────────────────   $X
    AI/tooling cost  ─ cost of running AI agents                  -$y
    Labor savings  ── cost reduction from faster/cheaper actors   +$z
    Wait-time savings ─ value of freed capacity                   +$w
    Failure reduction ─ fewer failed cases                        +$v
    ─────────────────────────────────────────────────────────────
    Net savings (pre-implementation)                              +$S
    Implementation cost  ─ one-time investment                    -$I
    ─────────────────────────────────────────────────────────────
    Net ROI                                                       +$N

All amounts are in the simulation's native currency unit.

No external dependencies -- both text and SVG outputs use stdlib only.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

from b2b_workflow_simulator.kpi import KPIResult


@dataclass
class WaterfallBar:
    """One bar in the ROI waterfall chart.

    Attributes:
        label: Human-readable bar label.
        value: Amount in currency units.  Positive = benefit; negative = cost.
        is_subtotal: When ``True`` this bar is a running total line, not an
            incremental step.
        note: Optional one-line explanation attached to this bar.
    """

    label: str
    value: float
    is_subtotal: bool = False
    note: str = ""


@dataclass
class ROIWaterfall:
    """Decomposed ROI analysis showing each savings/cost component.

    Attributes:
        workflow_name: Name of the "after" workflow variant.
        currency: Currency symbol for display (default ``"$"``).
        bars: Ordered list of :class:`WaterfallBar` objects.
        assumptions: Plain-text assumptions that underpin the estimates.
    """

    workflow_name: str
    currency: str = "$"
    bars: list[WaterfallBar] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    @property
    def net_savings(self) -> float:
        """Sum of all non-subtotal bar values."""
        return sum(b.value for b in self.bars if not b.is_subtotal)

    @property
    def is_positive_roi(self) -> bool:
        """``True`` when net savings are positive (the redesign pays off)."""
        return self.net_savings > 0


def build_roi_waterfall(
    before_kpi: KPIResult,
    after_kpi: KPIResult,
    implementation_cost: float | None = None,
    currency: str = "$",
) -> ROIWaterfall:
    """Decompose the KPI difference into a named waterfall of savings and costs.

    Args:
        before_kpi: KPI result from the "before" simulation run.
        after_kpi: KPI result from the "after" simulation run.
        implementation_cost: Optional one-time cost of implementing the
            redesign (e.g. software, training, consulting).
        currency: Currency symbol for display.

    Returns:
        A :class:`ROIWaterfall` with one bar per cost/savings component.
    """
    waterfall = ROIWaterfall(
        workflow_name=after_kpi.workflow_name,
        currency=currency,
    )

    baseline_cost = before_kpi.total_cost
    after_cost = after_kpi.total_cost
    net_operating_delta = baseline_cost - after_cost

    total_cases = before_kpi.total_cases
    avg_before_cost = before_kpi.avg_cost_per_case
    avg_after_cost = after_kpi.avg_cost_per_case

    waterfall.bars.append(WaterfallBar(
        label="Baseline operating cost",
        value=baseline_cost,
        is_subtotal=True,
        note=f"{total_cases} cases × {currency}{avg_before_cost:,.2f}/case",
    ))

    labor_savings = net_operating_delta
    if labor_savings > 0:
        waterfall.bars.append(WaterfallBar(
            label="Labor/execution savings",
            value=labor_savings,
            note=f"Reduced from {currency}{avg_before_cost:,.2f} to "
                 f"{currency}{avg_after_cost:,.2f} per case",
        ))
    elif labor_savings < 0:
        waterfall.bars.append(WaterfallBar(
            label="Added execution cost",
            value=labor_savings,
            note=f"After variant costs {currency}{abs(labor_savings):,.2f} more",
        ))

    wait_saved = before_kpi.total_wait_minutes - after_kpi.total_wait_minutes
    if abs(wait_saved) > 0 and before_kpi.total_cases > 0:
        wait_value = wait_saved * (avg_before_cost / max(before_kpi.avg_cycle_time_minutes, 1.0))
        waterfall.bars.append(WaterfallBar(
            label="Wait-time savings",
            value=wait_value,
            note=(
                f"{wait_saved:,.0f} min saved × "
                f"{currency}{wait_value/max(wait_saved, 1):.2f}/min proxy"
            ),
        ))

    failure_delta = before_kpi.failed_cases - after_kpi.failed_cases
    if failure_delta != 0:
        failure_value = failure_delta * avg_before_cost
        waterfall.bars.append(WaterfallBar(
            label="Failure reduction value",
            value=failure_value,
            note=f"{failure_delta:+d} fewer failures × {currency}{avg_before_cost:,.2f} avg cost",
        ))

    running = sum(b.value for b in waterfall.bars if not b.is_subtotal) + baseline_cost
    waterfall.bars.append(WaterfallBar(
        label="Pre-implementation savings",
        value=running - baseline_cost,
        is_subtotal=True,
        note=f"Total cost after redesign: {currency}{running:,.2f}",
    ))

    if implementation_cost is not None and implementation_cost > 0:
        waterfall.bars.append(WaterfallBar(
            label="Implementation cost",
            value=-implementation_cost,
            note="One-time investment (software, training, consulting)",
        ))

    net = sum(b.value for b in waterfall.bars if not b.is_subtotal)
    waterfall.bars.append(WaterfallBar(
        label="Net ROI",
        value=net,
        is_subtotal=True,
        note=f"{'Savings' if net >= 0 else 'Net cost'}: {currency}{abs(net):,.2f}",
    ))

    if implementation_cost is not None and implementation_cost > 0 and net > 0:
        per_case_savings = net / max(total_cases, 1)
        payback_cases = implementation_cost / max(per_case_savings, 0.01)
        waterfall.assumptions.append(
            f"Payback period: ~{payback_cases:,.0f} cases at current savings rate."
        )

    waterfall.assumptions += [
        f"Costs derived from {total_cases} simulated cases.",
        "Wait-time savings proxy: (wait minutes saved) × (baseline cost/cycle time).",
        "Failure reduction value: (failures avoided) × (baseline avg cost/case).",
        "All figures are directional estimates from simulation; validate against real data.",
    ]

    return waterfall


def _fmt(value: float, currency: str = "$") -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{currency}{abs(value):,.2f}"


def waterfall_to_text(waterfall: ROIWaterfall) -> str:
    """Render a :class:`ROIWaterfall` as a plain-text chart.

    Args:
        waterfall: A computed ROI waterfall.

    Returns:
        A multi-line plain-text string suitable for CLI output.
    """
    cur = waterfall.currency
    col1 = max(len(b.label) for b in waterfall.bars) + 2
    col2 = 14
    lines: list[str] = [
        "=" * 60,
        f"ROI WATERFALL: {waterfall.workflow_name}",
        "=" * 60,
        "",
        f"{'Component':<{col1}}{'Amount':>{col2}}",
        "-" * (col1 + col2),
    ]
    running = 0.0
    for bar in waterfall.bars:
        if bar.is_subtotal:
            val_str = _fmt(bar.value, cur)
            lines.append(f"{'':2}{'─' * (col1 - 2)}")
            lines.append(f"{'':2}{bar.label:<{col1 - 2}}{val_str:>{col2}}")
            if bar.note:
                lines.append(f"{'':4}{bar.note}")
            lines.append("")
        else:
            running += bar.value
            val_str = _fmt(bar.value, cur)
            lines.append(f"  {bar.label:<{col1 - 2}}{val_str:>{col2}}")
            if bar.note:
                lines.append(f"    {bar.note}")

    lines += [
        "Assumptions:",
        *[f"  - {a}" for a in waterfall.assumptions],
    ]
    return "\n".join(lines)


def _svg_bar_color(bar: WaterfallBar) -> str:
    if bar.is_subtotal:
        return "#4472C4"
    return "#70AD47" if bar.value >= 0 else "#FF0000"


def waterfall_to_svg(waterfall: ROIWaterfall, width: int = 700, bar_height: int = 36) -> str:
    """Render a :class:`ROIWaterfall` as a standalone SVG string.

    All text is HTML-escaped.  No external fonts, scripts, or assets.

    Args:
        waterfall: A computed ROI waterfall.
        width: SVG canvas width in pixels.
        bar_height: Height of each bar row in pixels.

    Returns:
        A self-contained SVG string.
    """
    cur = waterfall.currency
    bars = waterfall.bars
    n = len(bars)
    margin_left = 220
    margin_right = 30
    margin_top = 50
    chart_width = width - margin_left - margin_right
    chart_height = n * bar_height
    total_height = margin_top + chart_height + 80

    all_vals = [b.value for b in bars]
    max_abs = max(abs(v) for v in all_vals) if all_vals else 1.0
    scale = (chart_width * 0.45) / max(max_abs, 1.0)
    zero_x = margin_left + chart_width * 0.5

    def px(value: float) -> float:
        return zero_x + value * scale

    title = html.escape(f"ROI Waterfall: {waterfall.workflow_name}", quote=True)
    svg_parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{total_height}" '
        f'viewBox="0 0 {width} {total_height}">',
        f'  <rect width="{width}" height="{total_height}" fill="#ffffff"/>',
        f'  <text x="{width//2}" y="28" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="14" font-weight="bold" '
        f'fill="#1a1a1a">{title}</text>',
        f'  <line x1="{zero_x:.1f}" y1="{margin_top}" '
        f'x2="{zero_x:.1f}" y2="{margin_top + chart_height}" '
        f'stroke="#999" stroke-width="1"/>',
    ]

    for i, bar in enumerate(bars):
        y = margin_top + i * bar_height
        cy = y + bar_height * 0.5
        label = html.escape(bar.label, quote=True)
        val_str = html.escape(_fmt(bar.value, cur), quote=True)
        color = _svg_bar_color(bar)
        fw = "bold" if bar.is_subtotal else "normal"

        bar_x = min(px(0), px(bar.value))
        bar_w = abs(bar.value) * scale
        bar_w = max(bar_w, 2.0)

        svg_parts.append(
            f'  <rect x="{bar_x:.1f}" y="{y + 4}" '
            f'width="{bar_w:.1f}" height="{bar_height - 8}" '
            f'fill="{color}" rx="2"/>'
        )
        svg_parts.append(
            f'  <text x="{margin_left - 6}" y="{cy + 5}" '
            f'text-anchor="end" font-family="Arial,sans-serif" '
            f'font-size="11" font-weight="{fw}" fill="#1a1a1a">{label}</text>'
        )
        val_x = px(bar.value)
        anchor = "start" if bar.value >= 0 else "end"
        offset = 4 if bar.value >= 0 else -4
        svg_parts.append(
            f'  <text x="{val_x + offset:.1f}" y="{cy + 5}" '
            f'text-anchor="{anchor}" font-family="Arial,sans-serif" '
            f'font-size="11" font-weight="{fw}" fill="#1a1a1a">{val_str}</text>'
        )

    note_y = margin_top + chart_height + 20
    svg_parts.append(
        f'  <text x="{margin_left}" y="{note_y}" '
        f'font-family="Arial,sans-serif" font-size="9" fill="#666666">'
        f'Simulation estimate. Validate against real operational data.</text>'
    )
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


__all__ = [
    "ROIWaterfall",
    "WaterfallBar",
    "build_roi_waterfall",
    "waterfall_to_svg",
    "waterfall_to_text",
]
