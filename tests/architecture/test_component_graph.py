"""Tests for component dependency graph construction."""
import networkx as nx
import pytest

from karuvi.architecture.component_graph import build_component_graph
from karuvi.architecture.models import Component


def test_build_component_graph():
    # Module graph
    MG = nx.DiGraph()
    # Inter-component edges
    MG.add_edge("api/login.py", "services/auth.py", weight=3, relationship_types={"CALL": 3})
    MG.add_edge("api/users.py", "services/auth.py", weight=2, relationship_types={"CALL": 2})
    MG.add_edge("services/auth.py", "db/users.py", weight=4, relationship_types={"REFERENCE": 4})
    # Intra-component edge inside services
    MG.add_edge("services/auth.py", "services/token.py", weight=1, relationship_types={"CALL": 1})

    components = {
        "api": Component(id="api", name="api", modules=["api/login.py", "api/users.py"]),
        "services": Component(id="services", name="services", modules=["services/auth.py", "services/token.py"]),
        "db": Component(id="db", name="db", modules=["db/users.py"]),
    }

    CG = build_component_graph(MG, components)

    # 3 components
    assert set(CG.nodes) == {"api", "services", "db"}

    # No self-loop on services
    assert not CG.has_edge("services", "services")
    assert CG.nodes["services"]["metadata"].get("internal_weight") == 1

    # Edge api -> services aggregated: 3 + 2 = 5
    assert CG.has_edge("api", "services")
    edge_data = CG["api"]["services"]
    assert edge_data["weight"] == 5
    assert edge_data["relationship_types"]["CALL"] == 5

    # Edge services -> db: 4
    assert CG.has_edge("services", "db")
    assert CG["services"]["db"]["weight"] == 4

    # Degrees
    assert CG.nodes["api"]["out_degree"] == 1
    assert CG.nodes["api"]["in_degree"] == 0
    assert CG.nodes["services"]["in_degree"] == 1
    assert CG.nodes["services"]["out_degree"] == 1
    assert CG.nodes["db"]["in_degree"] == 1
    assert CG.nodes["db"]["out_degree"] == 0
