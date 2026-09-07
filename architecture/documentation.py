"""
Deterministic Markdown Documentation Generator
==============================================

Generates human-readable, beginner-friendly Markdown architectural explanations
directly derived from the structural evidence in the ArchitectureModel.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from architecture.models import ArchitectureModel


def generate_architecture_markdown(model: ArchitectureModel) -> str:
    """
    Generates a comprehensive, beginner-friendly Markdown report of the architecture.
    """
    lines: list[str] = []

    # Title & Overview
    lines.append("# Repository Architecture")
    lines.append("")
    lines.append(f"Karuvi analyzed repository: `{model.repository_root}`")
    lines.append("")

    stats = model.metadata.get("statistics", {})
    mod_count = len(model.modules)
    comp_count = len(model.components)
    sym_count = sum(m.symbol_count for m in model.modules.values())
    rel_count = model.module_graph.number_of_edges() if model.module_graph else 0

    lines.append(f"- **{mod_count}** modules analyzed")
    lines.append(f"- **{sym_count}** symbols indexed")
    lines.append(f"- **{rel_count}** inter-module relationships resolved")
    lines.append(f"- **{comp_count}** architectural components discovered")
    lines.append("")

    # Structural Entry Points
    lines.append("## Structural Entry Points")
    lines.append("")
    if model.entry_points:
        lines.append("These modules have low incoming coupling and reach large downstream parts of the codebase:")
        lines.append("")
        for ep in model.entry_points[:5]:
            m = ep["module"]
            score = ep["entry_score"]
            ev = ep["evidence"]
            lines.append(
                f"- **`{m}`** (Score: {score:.2f}) — reaches {ev['reachable_modules']} modules across {ev['reachable_components']} components"
            )
    else:
        lines.append("*No prominent entry points identified.*")
    lines.append("")

    # Representative Architecture Flows
    lines.append("## High-Level Architecture Flows")
    lines.append("")
    if model.flows:
        lines.append("Key paths across architectural components:")
        lines.append("")
        for flow in model.flows:
            path_str = " ➔ ".join(f"`{c}`" for c in flow.path)
            lines.append(f"- {path_str}")
    else:
        lines.append("*No cross-component flows identified.*")
    lines.append("")

    # Component Breakdown
    lines.append("## Architectural Components")
    lines.append("")

    for comp_id, comp in model.components.items():
        lines.append(f"### Component: {comp.name}")
        lines.append("")
        lines.append(f"- **Confidence**: `{comp.confidence:.1%}`")
        lines.append(f"- **Modules ({len(comp.modules)})**:")
        for m in comp.modules:
            role = model.roles.get(m, "MODULE")
            lines.append(f"  - `{m}` _(Role: {role})_")

        # In-edges and Out-edges from component graph
        if model.component_graph and model.component_graph.has_node(comp_id):
            deps = [tgt for _, tgt in model.component_graph.out_edges(comp_id)]
            dep_bys = [src for src, _ in model.component_graph.in_edges(comp_id)]

            if deps:
                lines.append(f"- **Depends on**: {', '.join(f'`{d}`' for d in deps)}")
            else:
                lines.append("- **Depends on**: _None (Leaf)_")

            if dep_bys:
                lines.append(f"- **Used by**: {', '.join(f'`{u}`' for u in dep_bys)}")
            else:
                lines.append("- **Used by**: _None (Root/Entry)_")

        lines.append("")

    return "\n".join(lines)
