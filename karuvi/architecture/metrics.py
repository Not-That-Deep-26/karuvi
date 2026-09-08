"""
Graph Metrics Calculation
=========================

Computes global topological and centrality metrics once for the module graph:
Degrees, Betweenness Centrality, PageRank, Reachable Descendants, and Cycles (SCCs).
"""
from __future__ import annotations

from typing import Any

import networkx as nx


def calculate_metrics(module_graph: nx.DiGraph) -> dict[str, dict[str, Any]]:
    """
    Computes global topological metrics for all modules in the graph.

    Returns:
        Mapping of module_id -> metrics_dict containing:
        - in_degree, out_degree
        - weighted_in_degree, weighted_out_degree
        - betweenness_centrality
        - pagerank
        - reachable_descendant_count
        - is_in_cycle
        - cycle_size
    """
    metrics: dict[str, dict[str, Any]] = {}
    nodes = list(module_graph.nodes)
    n_nodes = len(nodes)

    if n_nodes == 0:
        return {}

    # 1. Betweenness Centrality (normalized)
    try:
        betweenness = nx.betweenness_centrality(module_graph, weight="weight")
    except Exception:
        betweenness = {n: 0.0 for n in nodes}

    # 2. PageRank
    try:
        pagerank = nx.pagerank(module_graph, weight="weight", alpha=0.85, max_iter=100)
    except Exception:
        pagerank = {n: 1.0 / n_nodes for n in nodes}

    # 3. Strongly Connected Components (cycles)
    sccs = list(nx.strongly_connected_components(module_graph))
    node_to_scc_size: dict[str, int] = {}
    for comp in sccs:
        size = len(comp)
        for node in comp:
            node_to_scc_size[node] = size

    # 4. Descendant reach and degrees
    for node in nodes:
        in_edges = list(module_graph.in_edges(node, data=True))
        out_edges = list(module_graph.out_edges(node, data=True))

        in_deg = len(in_edges)
        out_deg = len(out_edges)
        weighted_in = sum(d.get("weight", 1) for _, _, d in in_edges)
        weighted_out = sum(d.get("weight", 1) for _, _, d in out_edges)

        try:
            descendants = nx.descendants(module_graph, node)
            desc_count = len(descendants)
        except Exception:
            desc_count = 0

        scc_size = node_to_scc_size.get(node, 1)

        metrics[node] = {
            "in_degree": in_deg,
            "out_degree": out_deg,
            "weighted_in_degree": weighted_in,
            "weighted_out_degree": weighted_out,
            "betweenness_centrality": betweenness.get(node, 0.0),
            "pagerank": pagerank.get(node, 0.0),
            "reachable_descendant_count": desc_count,
            "is_in_cycle": scc_size > 1,
            "cycle_size": scc_size,
        }

    return metrics
