"""
Graph Community Detection
=========================

Discovers densely connected topological module clusters using Louvain community
partitioning on an undirected weighted projection of the module graph.
"""
from __future__ import annotations

import logging
from typing import Any

import networkx as nx

from .models import ArchitectureConfig

logger = logging.getLogger(__name__)


def convert_to_undirected_weighted(module_graph: nx.DiGraph) -> nx.Graph:
    """
    Converts a directed module graph into a weighted undirected graph.

    Aggregates forward and reverse edge weights between any pair of nodes:
        undirected_weight = forward_weight + reverse_weight
    """
    undirected = nx.Graph()

    for node, data in module_graph.nodes(data=True):
        undirected.add_node(node, **data)

    for u, v, data in module_graph.edges(data=True):
        if u == v:
            continue
        weight = data.get("weight", 1)
        if undirected.has_edge(u, v):
            undirected[u][v]["weight"] += weight
        else:
            undirected.add_edge(u, v, weight=weight)

    return undirected


def detect_communities(
    module_graph: nx.DiGraph,
    config: ArchitectureConfig | None = None,
) -> dict[str, int]:
    """
    Detects graph communities across modules.

    Handles small graphs (0, 1, 2 nodes) and disconnected components explicitly.
    Returns:
        Mapping of module_id -> community_id (e.g. {"services/auth.py": 0, "db/users.py": 1})
    """
    nodes = list(module_graph.nodes)
    node_count = len(nodes)

    # 1. Base cases for small graphs
    if node_count == 0:
        return {}
    if node_count == 1:
        return {nodes[0]: 0}

    undirected = convert_to_undirected_weighted(module_graph)
    seed = config.community_seed if config else 42

    # 2. If graph has no edges at all, assign distinct communities
    if undirected.number_of_edges() == 0:
        return {node: i for i, node in enumerate(nodes)}

    # 3. For 2 nodes with an edge
    if node_count == 2:
        if undirected.has_edge(nodes[0], nodes[1]):
            return {nodes[0]: 0, nodes[1]: 0}
        return {nodes[0]: 0, nodes[1]: 1}

    # 4. Run Louvain community detection
    try:
        # Use NetworkX built-in Louvain algorithm
        communities_sets = nx.community.louvain_communities(
            undirected,
            weight="weight",
            seed=seed,
        )

        community_map: dict[str, int] = {}
        # Sort community sets by size descending, then deterministically by min node
        sorted_communities = sorted(
            communities_sets,
            key=lambda s: (-len(s), min(s) if s else "")
        )

        for comm_id, node_set in enumerate(sorted_communities):
            for node in node_set:
                community_map[node] = comm_id

        # Any node not partitioned (e.g. isolated) gets its own community
        next_id = len(sorted_communities)
        for node in nodes:
            if node not in community_map:
                community_map[node] = next_id
                next_id += 1

        return community_map

    except Exception as exc:
        logger.warning(
            f"Community detection fallback triggered due to: {exc}. "
            "Falling back to connected components."
        )
        # Fallback to connected components
        conn_comps = list(nx.connected_components(undirected))
        community_map = {}
        for comm_id, comp_nodes in enumerate(conn_comps):
            for node in comp_nodes:
                community_map[node] = comm_id
        return community_map
