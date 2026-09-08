"""
Component Dependency Graph Construction
=======================================

Collapses the fine-grained module graph into a coarse-grained component dependency graph.
Aggregates inter-component relationships while recording intra-component connectivity.
"""
from __future__ import annotations

from typing import Any

import networkx as nx

from .models import Component


def build_component_graph(
    module_graph: nx.DiGraph,
    components: dict[str, Component],
) -> nx.DiGraph:
    """
    Constructs a directed component graph by collapsing module graph edges.

    Each node is a Component, and directed edges represent aggregated inter-component
    dependencies with relationship type breakdowns and evidence.
    """
    comp_graph = nx.DiGraph()

    # 1. Invert mapping: module -> component_id
    mod_to_comp: dict[str, str] = {}
    for comp_id, comp in components.items():
        for mod in comp.modules:
            mod_to_comp[mod] = comp_id

    # 2. Add component nodes
    for comp_id, comp in components.items():
        comp_graph.add_node(
            comp_id,
            id=comp_id,
            name=comp.name,
            modules=comp.modules,
            module_count=len(comp.modules),
            confidence=comp.confidence,
            discovery_methods=comp.discovery_methods,
            metadata=comp.metadata,
        )

    # 3. Collapse module edges into component edges
    for u, v, edge_data in module_graph.edges(data=True):
        src_comp = mod_to_comp.get(u)
        tgt_comp = mod_to_comp.get(v)

        if not src_comp or not tgt_comp:
            continue

        weight = edge_data.get("weight", 1)
        rel_types = edge_data.get("relationship_types", {})

        if src_comp == tgt_comp:
            # Self-relationship inside component: update internal weight
            if comp_graph.has_node(src_comp):
                comp_meta = comp_graph.nodes[src_comp]["metadata"]
                comp_meta["internal_weight"] = comp_meta.get("internal_weight", 0) + weight
        else:
            # Cross-component relationship
            if comp_graph.has_edge(src_comp, tgt_comp):
                edge = comp_graph[src_comp][tgt_comp]
                edge["weight"] += weight
                for rt, count in rel_types.items():
                    edge["relationship_types"][rt] = edge["relationship_types"].get(rt, 0) + count
                edge["module_relationships"].append({
                    "source_module": u,
                    "target_module": v,
                    "weight": weight,
                })
            else:
                comp_graph.add_edge(
                    src_comp,
                    tgt_comp,
                    weight=weight,
                    relationship_types=dict(rel_types),
                    module_relationships=[{
                        "source_module": u,
                        "target_module": v,
                        "weight": weight,
                    }],
                )

    # 4. Calculate component in/out degrees
    for comp_id in comp_graph.nodes:
        in_degree = comp_graph.in_degree(comp_id)
        out_degree = comp_graph.out_degree(comp_id)
        comp_graph.nodes[comp_id]["in_degree"] = in_degree
        comp_graph.nodes[comp_id]["out_degree"] = out_degree

    return comp_graph
