"""
Structural Role Detection
=========================

Assigns structural architectural roles to modules based on their topological position,
centrality distribution, and dependency flow direction.
"""
from __future__ import annotations

from typing import Any

import networkx as nx


def detect_roles(
    module_graph: nx.DiGraph,
    metrics: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """
    Assigns structural roles to modules based on graph topology and metric distributions.

    Roles:
    - ISOLATED: No incoming or outgoing dependencies
    - CYCLE_MEMBER: Member of a circular dependency loop (SCC > 1)
    - ENTRY_CANDIDATE: Low incoming degree, high downstream reach
    - LEAF: High incoming degree, low outgoing degree
    - BRIDGE: High relative betweenness centrality
    - HUB: High relative weighted total degree or PageRank
    - INTERMEDIARY: Balanced incoming and outgoing relationships
    """
    roles: dict[str, str] = {}
    nodes = list(module_graph.nodes)

    if not nodes:
        return {}

    # Collect metric distributions for percentile classification
    betweenness_values = [metrics[n]["betweenness_centrality"] for n in nodes]
    degrees = [metrics[n]["in_degree"] + metrics[n]["out_degree"] for n in nodes]

    max_betweenness = max(betweenness_values) if betweenness_values else 0.0
    max_degree = max(degrees) if degrees else 0

    # High betweenness threshold: > 0 and in the upper 20% of non-zero betweenness
    non_zero_bc = sorted([b for b in betweenness_values if b > 0.0])
    bridge_threshold = (
        non_zero_bc[int(len(non_zero_bc) * 0.8)] if len(non_zero_bc) >= 4 else (max_betweenness * 0.7 if max_betweenness > 0 else 1.0)
    )

    # High degree threshold for HUB: top 20% of degrees
    sorted_deg = sorted(degrees)
    hub_threshold = (
        sorted_deg[int(len(sorted_deg) * 0.8)] if len(sorted_deg) >= 4 else (max_degree * 0.75 if max_degree > 0 else 100)
    )

    for node in nodes:
        m = metrics[node]
        in_deg = m["in_degree"]
        out_deg = m["out_degree"]
        desc_count = m["reachable_descendant_count"]
        bc = m["betweenness_centrality"]
        tot_deg = in_deg + out_deg

        if in_deg == 0 and out_deg == 0:
            roles[node] = "ISOLATED"
        elif m.get("is_in_cycle", False):
            roles[node] = "CYCLE_MEMBER"
        elif in_deg == 0 and desc_count > 0:
            roles[node] = "ENTRY_CANDIDATE"
        elif out_deg == 0 and in_deg > 0:
            roles[node] = "LEAF"
        elif bc >= bridge_threshold and bc > 0.05 and in_deg > 0 and out_deg > 0:
            roles[node] = "BRIDGE"
        elif tot_deg >= hub_threshold and tot_deg >= 3:
            roles[node] = "HUB"
        elif in_deg > 0 and out_deg > 0:
            roles[node] = "INTERMEDIARY"
        elif in_deg <= 1 and desc_count >= 2:
            roles[node] = "ENTRY_CANDIDATE"
        else:
            roles[node] = "LEAF" if in_deg > out_deg else "INTERMEDIARY"

    return roles
