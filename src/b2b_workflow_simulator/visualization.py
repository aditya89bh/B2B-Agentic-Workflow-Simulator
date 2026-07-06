"""Workflow graph visualization: Mermaid flowchart and plain-text output.

Turns a ``Workflow`` object into a visual representation that can be
included in reports, slide decks, or pasted into Mermaid-compatible
markdown editors (GitHub, Notion, VS Code).

No external dependencies -- Mermaid is just text syntax.

Usage::

    from b2b_workflow_simulator.visualization import to_mermaid, to_text
    from b2b_workflow_simulator.examples import invoice_processing

    wf = invoice_processing.build_before_workflow()
    print(to_mermaid(wf))   # paste into any Mermaid renderer
    print(to_text(wf))      # plain-text ASCII graph
"""

from __future__ import annotations

from b2b_workflow_simulator.primitives.ai_agent import AIAgentActor
from b2b_workflow_simulator.workflow import Workflow


def _safe_id(node_id: str) -> str:
    """Convert a node_id to a Mermaid-safe identifier (alphanumeric + underscore)."""
    return node_id.replace("-", "_").replace(" ", "_").replace(".", "_")


def _node_label(workflow: Workflow, node_id: str) -> str:
    """Build a human-readable node label: name + actor kind."""
    node = workflow.get_node(node_id)
    actor = workflow.get_actor(node.actor_id)
    actor_kind = "AI" if isinstance(actor, AIAgentActor) else "Human"
    return f"{node.name}\\n[{actor_kind}: {actor.actor_id}]"


def to_mermaid(workflow: Workflow) -> str:
    """Render a ``Workflow`` as a Mermaid LR flowchart string.

    Terminal nodes are rendered with stadium shape ``([label])``.
    Non-terminal nodes use rectangular shape ``[label]``.
    Edges with probability < 1.0 show the probability as a label.
    Multi-actor nodes show a ``*`` prefix.

    Args:
        workflow: A validated workflow definition.

    Returns:
        A multi-line Mermaid flowchart string ready to paste into any
        Mermaid renderer.
    """
    lines = ["flowchart LR"]

    for node_id, node in workflow.nodes.items():
        safe = _safe_id(node_id)
        actor = workflow.get_actor(node.actor_id)
        actor_kind = "AI" if isinstance(actor, AIAgentActor) else "Human"
        multi = "* " if node.is_multi_resource else ""
        label = f"{multi}{node.name}\\n[{actor_kind}: {actor.actor_id}]"
        if node.is_terminal:
            lines.append(f"    {safe}([{label}])")
        else:
            lines.append(f"    {safe}[{label}]")

    lines.append("")

    entry_safe = _safe_id(workflow.entry_node_id)
    lines.append(f"    style {entry_safe} fill:#d4edda,stroke:#28a745")

    for node_id, node in workflow.nodes.items():
        if node.is_terminal:
            safe = _safe_id(node_id)
            lines.append(f"    style {safe} fill:#f8f9fa,stroke:#6c757d")

    lines.append("")

    for edge in workflow.edges:
        src = _safe_id(edge.source)
        tgt = _safe_id(edge.target)
        if abs(edge.probability - 1.0) < 1e-6:
            lines.append(f"    {src} --> {tgt}")
        else:
            pct = f"{edge.probability:.0%}"
            lines.append(f"    {src} -->|{pct}| {tgt}")

    return "\n".join(lines)


def to_text(workflow: Workflow) -> str:
    """Render a ``Workflow`` as a plain-text graph.

    Shows nodes with actor info, and edges with branch probabilities.
    Entry node is marked with ``[ENTRY]`` and terminal nodes with
    ``[TERMINAL]``.

    Args:
        workflow: A validated workflow definition.

    Returns:
        A multi-line plain-text string.
    """
    lines: list[str] = [
        f"Workflow: {workflow.name}",
        f"Entry: {workflow.entry_node_id}",
        "=" * 60,
        "",
    ]

    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(workflow.entry_node_id, 0)]
    while queue:
        node_id, depth = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        node = workflow.get_node(node_id)
        actor = workflow.get_actor(node.actor_id)
        actor_kind = "AI" if isinstance(actor, AIAgentActor) else "Human"
        indent = "  " * depth
        flags = []
        if node_id == workflow.entry_node_id:
            flags.append("ENTRY")
        if node.is_terminal:
            flags.append("TERMINAL")
        if node.is_multi_resource:
            flags.append("MULTI-ACTOR")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"{indent}Node: {node.name} (id: {node_id}){flag_str}"
        )
        lines.append(f"{indent}  Actor: {actor.actor_id} ({actor_kind})")
        lines.append(f"{indent}  Duration: {node.base_duration_minutes:.0f} min base")

        out_edges = workflow.outgoing_edges(node_id)
        for edge in out_edges:
            prob_str = f"{edge.probability:.0%}"
            lines.append(f"{indent}  --> {edge.target}  ({prob_str})")
            if edge.target not in visited:
                queue.append((edge.target, depth + 1))
        lines.append("")

    return "\n".join(lines)


def compare_text(before: Workflow, after: Workflow) -> str:
    """Render a side-by-side text comparison of two workflow variants.

    Args:
        before: The "before" (current-state) workflow.
        after: The "after" (redesigned) workflow.

    Returns:
        A plain-text comparison showing structural differences.
    """
    before_nodes = set(before.nodes)
    after_nodes = set(after.nodes)
    added = after_nodes - before_nodes
    removed = before_nodes - after_nodes
    common = before_nodes & after_nodes

    lines: list[str] = [
        "WORKFLOW COMPARISON",
        f"Before: {before.name}",
        f"After:  {after.name}",
        "=" * 60,
        "",
        f"Nodes: {len(before_nodes)} → {len(after_nodes)} "
        f"({len(added)} added, {len(removed)} removed, {len(common)} unchanged)",
        f"Edges: {len(before.edges)} → {len(after.edges)}",
        "",
    ]

    if added:
        lines.append("Added nodes:")
        for nid in sorted(added):
            node = after.get_node(nid)
            actor = after.get_actor(node.actor_id)
            kind = "AI" if isinstance(actor, AIAgentActor) else "Human"
            lines.append(f"  + {node.name} (id: {nid}, {kind}: {actor.actor_id})")
        lines.append("")

    if removed:
        lines.append("Removed nodes:")
        for nid in sorted(removed):
            node = before.get_node(nid)
            actor = before.get_actor(node.actor_id)
            kind = "AI" if isinstance(actor, AIAgentActor) else "Human"
            lines.append(f"  - {node.name} (id: {nid}, {kind}: {actor.actor_id})")
        lines.append("")

    if common:
        changed = []
        for nid in sorted(common):
            b_node = before.get_node(nid)
            a_node = after.get_node(nid)
            b_actor = before.get_actor(b_node.actor_id)
            a_actor = after.get_actor(a_node.actor_id)
            b_kind = "AI" if isinstance(b_actor, AIAgentActor) else "Human"
            a_kind = "AI" if isinstance(a_actor, AIAgentActor) else "Human"
            if b_node.actor_id != a_node.actor_id or b_kind != a_kind:
                changed.append(
                    f"  ~ {b_node.name}: {b_kind}:{b_actor.actor_id} → "
                    f"{a_kind}:{a_actor.actor_id}"
                )
        if changed:
            lines.append("Changed actors:")
            lines.extend(changed)
            lines.append("")

    lines.append("Before graph:")
    lines.append(to_text(before))
    lines.append("After graph:")
    lines.append(to_text(after))
    return "\n".join(lines)


def compare_mermaid(before: Workflow, after: Workflow) -> str:
    """Return Mermaid for before and after workflows with a separator comment.

    The output contains two Mermaid diagrams separated by a comment block.
    Paste each separately into a Mermaid renderer.

    Args:
        before: The "before" workflow.
        after: The "after" workflow.

    Returns:
        Two Mermaid flowchart blocks separated by a comment line.
    """
    separator = f"%% --- Before: {before.name} ---"
    sep2 = f"%% --- After: {after.name} ---"
    return f"{separator}\n{to_mermaid(before)}\n\n{sep2}\n{to_mermaid(after)}"


__all__ = [
    "compare_mermaid",
    "compare_text",
    "to_mermaid",
    "to_text",
]
