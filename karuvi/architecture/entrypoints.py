"""
Structural Entry Point Detection
================================

Identifies high-value structural starting points for codebase exploration based on
low incoming dependency coupling and high downstream transitive reach.
"""
from __future__ import annotations

from typing import Any

import networkx as nx

from .models import Component


def detect_entry_points(
    module_graph: nx.DiGraph,
    metrics: dict[str, dict[str, Any]],
    components: dict[str, Component] | None = None,
) -> list[dict[str, Any]]:
    """
    Ranks modules as structural entry point candidates based on low incoming coupling
    and high reachable downstream descendants.

    Returns:
        Sorted list of dicts:
        [
            {
                "module": "api/main.py",
                "entry_score": 0.92,
                "evidence": {
                    "incoming_dependencies": 0,
                    "reachable_modules": 14,
                    "reachable_components": 3
                }
            },
            ...
        ]
    """
    nodes = list(module_graph.nodes)
    total_nodes = len(nodes)
    if total_nodes == 0:
        return []

    # Map module -> component
    mod_to_comp: dict[str, str] = {}
    if components:
        for comp_id, comp in components.items():
            for m in comp.modules:
                mod_to_comp[m] = comp_id

    candidates = []

    for node in nodes:
        m = metrics.get(node, {})
        in_deg = m.get("in_degree", 0)
        desc_count = m.get("reachable_descendant_count", 0)

        # Skip isolated modules (0 in, 0 out) as entry candidates
        if in_deg == 0 and desc_count == 0:
            continue

        # Inverted incoming coupling score: 1.0 for 0 in-degree, 0.5 for 1, 0.33 for 2, etc.
        low_incoming_score = 1.0 / (1.0 + in_deg)

        # Reach score relative to all other modules
        reach_score = desc_count / max(1, total_nodes - 1)

        # Final score
        entry_score = low_incoming_score * reach_score

        # Find reachable components
        reachable_comps = set()
        try:
            descendants = nx.descendants(module_graph, node)
            for d in descendants:
                c = mod_to_comp.get(d)
                if c:
                    reachable_comps.add(c)
        except Exception:
            pass

        candidates.append({
            "module": node,
            "entry_score": round(entry_score, 3),
            "evidence": {
                "incoming_dependencies": in_deg,
                "reachable_modules": desc_count,
                "reachable_components": len(reachable_comps),
            },
        })

    # Sort descending by entry_score, then by reachable_modules
    candidates.sort(
        key=lambda c: (-c["entry_score"], -c["evidence"]["reachable_modules"], c["module"])
    )

    return candidates
