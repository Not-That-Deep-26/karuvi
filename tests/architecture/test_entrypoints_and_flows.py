"""Tests for entry point detection and architectural flows."""
import networkx as nx
import pytest

from architecture.entrypoints import detect_entry_points
from architecture.flows import detect_flows
from architecture.metrics import calculate_metrics
from architecture.models import Component


def test_detect_entry_points():
    G = nx.DiGraph()
    G.add_edge("api/main.py", "services/auth.py")
    G.add_edge("services/auth.py", "db/users.py")
    G.add_node("unused.py")

    metrics = calculate_metrics(G)
    entry_points = detect_entry_points(G, metrics)

    assert len(entry_points) >= 1
    top_entry = entry_points[0]
    assert top_entry["module"] == "api/main.py"
    assert top_entry["entry_score"] > 0.0
    assert top_entry["evidence"]["incoming_dependencies"] == 0
    assert top_entry["evidence"]["reachable_modules"] == 2


def test_detect_flows():
    CG = nx.DiGraph()
    CG.add_edge("api", "services", weight=5)
    CG.add_edge("services", "db", weight=3)

    entry_points = [{"module": "api/main.py"}]
    components = {
        "api": Component(id="api", name="api", modules=["api/main.py"]),
        "services": Component(id="services", name="services", modules=["services/auth.py"]),
        "db": Component(id="db", name="db", modules=["db/users.py"]),
    }

    flows = detect_flows(CG, entry_points, components, max_flows=5)
    assert len(flows) >= 1
    main_flow = flows[0]
    assert main_flow.source == "api"
    assert main_flow.target == "db"
    assert main_flow.path == ["api", "services", "db"]


def test_flows_carry_human_names_and_roles():
    """Flows should expose human-readable component names plus entry/leaf roles."""
    CG = nx.DiGraph()
    CG.add_edge("api", "services", weight=5)
    CG.add_edge("services", "db", weight=3)

    entry_points = [{"module": "api/main.py"}]
    components = {
        "api": Component(
            id="api", name="api", modules=["api/main.py"],
            metadata={"distinguishing_label": "main"},
        ),
        "services": Component(id="services", name="services", modules=["services/auth.py"]),
        "db": Component(id="db", name="db", modules=["db/users.py"]),
    }

    flows = detect_flows(CG, entry_points, components, max_flows=5)
    assert len(flows) >= 1
    main_flow = flows[0]
    assert main_flow.path_names == ["api · main", "services", "db"]
    assert main_flow.start_role == "Entry"
    assert main_flow.end_role == "Leaf"
