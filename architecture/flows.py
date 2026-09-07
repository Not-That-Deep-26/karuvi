"""
Architectural Flow Detection
============================

Discovers high-level representative execution and dependency paths across components.
Uses graph condensation to safely handle cycles and bounds path complexity.
"""
from __future__ import annotations

from typing import Any

import networkx as nx

from architecture.models import ArchitectureFlow, Component


def detect_flows(
    component_graph: nx.DiGraph,
    entry_points: list[dict[str, Any]],
    components: dict[str, Component] | None = None,
    max_flows: int = 10,
) -> list[ArchitectureFlow]:
    """
    Computes representative architectural paths across components.

    Guarantees bounded complexity and cyclic safety via graph condensation.
    """
    if component_graph.number_of_nodes() < 2 or component_graph.number_of_edges() == 0:
        return []

    # Map module -> component
    mod_to_comp: dict[str, str] = {}
    if components:
        for comp_id, comp in components.items():
            for m in comp.modules:
                mod_to_comp[m] = comp_id

    # 1. Determine entry component candidates
    entry_comps: list[str] = []
    for ep in entry_points:
        m = ep["module"]
        c = mod_to_comp.get(m)
        if c and c in component_graph and c not in entry_comps:
            entry_comps.append(c)

    # Fallback to in-degree == 0 components
    if not entry_comps:
        entry_comps = [n for n in component_graph.nodes if component_graph.in_degree(n) == 0]

    # If all nodes are in cycles, pick node with lowest in-degree
    if not entry_comps:
        sorted_by_in = sorted(component_graph.nodes, key=lambda n: component_graph.in_degree(n))
        entry_comps = sorted_by_in[:2]

    # 2. Determine target / leaf component candidates (out_degree == 0 or low)
    target_comps = [n for n in component_graph.nodes if component_graph.out_degree(n) == 0]
    if not target_comps:
        sorted_by_out = sorted(component_graph.nodes, key=lambda n: component_graph.out_degree(n))
        target_comps = sorted_by_out[:2]

    # 3. Use graph condensation to safely handle cycles
    try:
        condensed = nx.condensation(component_graph)
    except Exception:
        condensed = None

    flows: list[ArchitectureFlow] = []
    seen_paths: set[tuple[str, ...]] = set()

    # 4. Find shortest paths from entry components to targets
    for src in entry_comps:
        for tgt in target_comps:
            if src == tgt:
                continue
            if len(flows) >= max_flows:
                break

            try:
                if nx.has_path(component_graph, src, tgt):
                    path = nx.shortest_path(component_graph, src, tgt)
                    path_tuple = tuple(path)
                    if path_tuple not in seen_paths and len(path) >= 2:
                        seen_paths.add(path_tuple)
                        flows.append(
                            ArchitectureFlow(
                                source=src,
                                target=tgt,
                                path=path,
                                evidence={
                                    "hop_count": len(path) - 1,
                                    "algorithm": "shortest_path",
                                },
                            )
                        )
            except Exception:
                continue

    # 5. If no entry-to-leaf paths found (e.g. single connected edge), include prominent edges
    if not flows:
        sorted_edges = sorted(
            component_graph.edges(data=True),
            key=lambda e: -e[2].get("weight", 1)
        )
        for u, v, data in sorted_edges[:max_flows]:
            if (u, v) not in seen_paths:
                seen_paths.add((u, v))
                flows.append(
                    ArchitectureFlow(
                        source=u,
                        target=v,
                        path=[u, v],
                        evidence={
                            "weight": data.get("weight", 1),
                            "algorithm": "direct_edge",
                        },
                    )
                )

    # 6. Annotate every flow with human-readable names and structural roles so
    # the UI can render them as labelled lanes (Entry -> ... -> Leaf / Cycle).
    def _comp_display_name(comp_id: str) -> str:
        if components is None:
            return str(comp_id)
        comp = components.get(comp_id)
        if comp is None:
            return str(comp_id)
        label = comp.metadata.get("distinguishing_label")
        return f"{comp.name} · {label}" if label else comp.name

    cycle_members: set[str] = set()
    try:
        for scc in nx.strongly_connected_components(component_graph):
            if len(scc) > 1:
                cycle_members.update(scc)
    except Exception:
        pass

    for flow in flows:
        flow.path_names = [_comp_display_name(cid) for cid in flow.path]
        flow.start_role = (
            "Entry" if flow.source in entry_comps
            else ("Cycle" if flow.source in cycle_members else "")
        )
        flow.end_role = (
            "Leaf" if flow.target in target_comps
            else ("Cycle" if flow.target in cycle_members else "")
        )

    return flows
