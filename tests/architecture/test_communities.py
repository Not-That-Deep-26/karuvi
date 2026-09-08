"""Tests for graph community detection."""
import networkx as nx
import pytest

from karuvi.architecture.communities import (
    convert_to_undirected_weighted,
    detect_communities,
)


def test_small_graphs():
    # 0 nodes
    G0 = nx.DiGraph()
    assert detect_communities(G0) == {}

    # 1 node
    G1 = nx.DiGraph()
    G1.add_node("a.py")
    assert detect_communities(G1) == {"a.py": 0}

    # 2 nodes connected
    G2 = nx.DiGraph()
    G2.add_edge("a.py", "b.py", weight=2)
    comm2 = detect_communities(G2)
    assert comm2["a.py"] == comm2["b.py"]

    # 2 nodes disconnected
    G2_dis = nx.DiGraph()
    G2_dis.add_node("a.py")
    G2_dis.add_node("b.py")
    comm2_dis = detect_communities(G2_dis)
    assert comm2_dis["a.py"] != comm2_dis["b.py"]


def test_convert_to_undirected_weighted():
    G = nx.DiGraph()
    G.add_edge("a.py", "b.py", weight=3)
    G.add_edge("b.py", "a.py", weight=2)

    undirected = convert_to_undirected_weighted(G)
    assert undirected.has_edge("a.py", "b.py")
    assert undirected["a.py"]["b.py"]["weight"] == 5


def test_community_clusters():
    G = nx.DiGraph()
    # Cluster 1: a, b, c
    G.add_edge("a.py", "b.py", weight=10)
    G.add_edge("b.py", "c.py", weight=10)
    G.add_edge("c.py", "a.py", weight=10)

    # Cluster 2: x, y, z
    G.add_edge("x.py", "y.py", weight=10)
    G.add_edge("y.py", "z.py", weight=10)
    G.add_edge("z.py", "x.py", weight=10)

    # Weak bridge: c -> x
    G.add_edge("c.py", "x.py", weight=1)

    comm = detect_communities(G)

    # Cluster 1 members should share the same community
    assert comm["a.py"] == comm["b.py"] == comm["c.py"]

    # Cluster 2 members should share the same community
    assert comm["x.py"] == comm["y.py"] == comm["z.py"]

    # Cluster 1 and Cluster 2 should be different
    assert comm["a.py"] != comm["x.py"]
