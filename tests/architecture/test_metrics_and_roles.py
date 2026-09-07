"""Tests for metrics and structural role detection."""
import networkx as nx
import pytest

from architecture.metrics import calculate_metrics
from architecture.roles import detect_roles


def test_metrics_and_roles_layered():
    # api -> services -> db
    G = nx.DiGraph()
    G.add_edge("api/main.py", "services/auth.py", weight=2)
    G.add_edge("services/auth.py", "db/users.py", weight=2)
    G.add_node("isolated.py")

    metrics = calculate_metrics(G)
    assert metrics["api/main.py"]["in_degree"] == 0
    assert metrics["api/main.py"]["reachable_descendant_count"] == 2
    assert metrics["db/users.py"]["out_degree"] == 0
    assert metrics["isolated.py"]["in_degree"] == 0
    assert metrics["isolated.py"]["out_degree"] == 0

    roles = detect_roles(G, metrics)
    assert roles["api/main.py"] == "ENTRY_CANDIDATE"
    assert roles["db/users.py"] == "LEAF"
    assert roles["isolated.py"] == "ISOLATED"
    assert roles["services/auth.py"] in ("INTERMEDIARY", "BRIDGE")


def test_metrics_and_roles_cycles():
    # a -> b -> c -> a (cycle)
    G = nx.DiGraph()
    G.add_edge("a.py", "b.py")
    G.add_edge("b.py", "c.py")
    G.add_edge("c.py", "a.py")

    metrics = calculate_metrics(G)
    assert metrics["a.py"]["is_in_cycle"] is True
    assert metrics["a.py"]["cycle_size"] == 3

    roles = detect_roles(G, metrics)
    assert roles["a.py"] == "CYCLE_MEMBER"
    assert roles["b.py"] == "CYCLE_MEMBER"
    assert roles["c.py"] == "CYCLE_MEMBER"
