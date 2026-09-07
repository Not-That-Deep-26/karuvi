"""Tests for component reconstruction and confidence calculation."""
import networkx as nx
import pytest

from architecture.components import (
    derive_component_name,
    reconstruct_components,
)
from architecture.models import ArchitectureConfig


def test_boundary_and_community_agreement():
    G = nx.DiGraph()
    G.add_edge("services/auth.py", "services/token.py", weight=5)

    module_to_boundary = {
        "services/auth.py": "services",
        "services/token.py": "services",
    }
    module_to_community = {
        "services/auth.py": 0,
        "services/token.py": 0,
    }

    components = reconstruct_components(G, module_to_boundary, module_to_community)
    assert len(components) == 1
    comp = list(components.values())[0]
    assert comp.name == "services"
    assert "BOUNDARY_AND_COMMUNITY" in comp.discovery_methods
    assert comp.confidence >= 0.8
    assert set(comp.modules) == {"services/auth.py", "services/token.py"}


def test_folder_splitting():
    """When a folder like utils has modules in divergent communities, split them."""
    G = nx.DiGraph()
    G.add_node("utils/auth.py")
    G.add_node("utils/db.py")
    G.add_node("utils/dates.py")
    G.add_edge("utils/auth.py", "utils/db.py", weight=10)

    module_to_boundary = {
        "utils/auth.py": "utils",
        "utils/db.py": "utils",
        "utils/dates.py": "utils",
    }
    # auth & db in community 0, dates in community 1
    module_to_community = {
        "utils/auth.py": 0,
        "utils/db.py": 0,
        "utils/dates.py": 1,
    }

    components = reconstruct_components(G, module_to_boundary, module_to_community)
    # Expect 2 components from utils
    assert len(components) == 2
    modules_in_comps = [set(c.modules) for c in components.values()]
    assert {"utils/auth.py", "utils/db.py"} in modules_in_comps
    assert {"utils/dates.py"} in modules_in_comps


def test_cross_folder_merging():
    """When modules in different folders belong to the same strong community."""
    G = nx.DiGraph()
    G.add_edge("auth/login.py", "sessions/token.py", weight=8)
    G.add_edge("sessions/token.py", "auth/login.py", weight=5)

    module_to_boundary = {
        "auth/login.py": "auth",
        "sessions/token.py": "sessions",
    }
    # Both in community 0
    module_to_community = {
        "auth/login.py": 0,
        "sessions/token.py": 0,
    }

    components = reconstruct_components(G, module_to_boundary, module_to_community)
    # Should merge into 1 component
    assert len(components) == 1
    comp = list(components.values())[0]
    assert "auth" in comp.name
    assert "sessions" in comp.name
    assert set(comp.modules) == {"auth/login.py", "sessions/token.py"}
