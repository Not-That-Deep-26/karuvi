"""Tests for module graph construction and path normalization."""
from pathlib import Path
import networkx as nx
import pytest

from architecture.module_graph import (
    build_module_graph,
    normalize_module_path,
)


def test_path_normalization():
    repo = Path("/home/user/myproject")

    # Absolute within repo
    assert normalize_module_path("/home/user/myproject/src/auth.py", repo) == "src/auth.py"

    # Relative with ./
    assert normalize_module_path("./src/auth.py", repo) == "src/auth.py"

    # Clean relative
    assert normalize_module_path("services/login.py", repo) == "services/login.py"

    # Backslashes normalized
    assert normalize_module_path("services\\utils\\crypto.py", repo) == "services/utils/crypto.py"


def test_module_node_creation_and_edge_aggregation():
    repo = Path("/repo")
    G = nx.DiGraph()

    # Symbol nodes in different files
    G.add_node("sym:login", file="api/login.py", kind="function", name="login")
    G.add_node("sym:logout", file="api/login.py", kind="function", name="logout")
    G.add_node("sym:auth", file="services/auth.py", kind="function", name="authenticate")
    G.add_node("sym:token", file="services/auth.py", kind="function", name="verify_token")
    G.add_node("sym:user_db", file="db/users.py", kind="class", name="UserDB")

    # Edges between symbols:
    # login -> auth (CALL)
    # logout -> auth (CALL)
    # auth -> user_db (REFERENCE)
    # auth -> token (intra-module CALL in services/auth.py)
    G.add_edge("sym:login", "sym:auth", type="CALL", symbol="authenticate")
    G.add_edge("sym:logout", "sym:auth", type="CALL", symbol="authenticate")
    G.add_edge("sym:auth", "sym:user_db", type="REFERENCE", symbol="UserDB")
    G.add_edge("sym:auth", "sym:token", type="CALL", symbol="verify_token")  # intra-module

    module_graph = build_module_graph(G, repo)

    # 3 module nodes created
    assert set(module_graph.nodes) == {"api/login.py", "services/auth.py", "db/users.py"}

    # Intra-module relationship excluded from module edges
    assert not module_graph.has_edge("services/auth.py", "services/auth.py")
    assert module_graph.nodes["services/auth.py"]["internal_relationship_count"] == 1

    # Edge aggregation: api/login.py -> services/auth.py has weight 2
    assert module_graph.has_edge("api/login.py", "services/auth.py")
    edge_data = module_graph["api/login.py"]["services/auth.py"]
    assert edge_data["weight"] == 2
    assert edge_data["relationship_types"]["CALL"] == 2
    assert len(edge_data["symbol_edges"]) == 2

    # Edge services/auth.py -> db/users.py has weight 1
    assert module_graph.has_edge("services/auth.py", "db/users.py")
    edge_data_db = module_graph["services/auth.py"]["db/users.py"]
    assert edge_data_db["weight"] == 1
    assert edge_data_db["relationship_types"]["REFERENCE"] == 1

    # Degrees and weights
    auth_node = module_graph.nodes["services/auth.py"]
    assert auth_node["in_degree"] == 1
    assert auth_node["out_degree"] == 1
    assert auth_node["incoming_weight"] == 2
    assert auth_node["outgoing_weight"] == 1
    assert auth_node["symbol_count"] == 2
