"""Tests for structural boundary detection."""
from pathlib import Path
import networkx as nx
import pytest

from karuvi.architecture.boundaries import (
    detect_boundaries,
    extract_module_boundary,
)
from karuvi.architecture.models import ArchitectureConfig


def test_extract_module_boundary():
    config = ArchitectureConfig()
    ignored = config.ignored_boundaries

    # Strips src
    assert extract_module_boundary("src/api/users.py", ignored) == "api"

    # Deep nesting preserves secondary if meaningful
    assert extract_module_boundary("src/backend/auth/login.py", ignored) == "backend/auth"

    # Direct top-level module
    assert extract_module_boundary("services/auth.py", ignored) == "services"

    # Root module
    assert extract_module_boundary("main.py", ignored) == "root"
    assert extract_module_boundary("src/main.py", ignored) == "root"


def test_detect_boundaries():
    repo = Path("/repo")
    G = nx.DiGraph()
    G.add_node("src/api/users.py", path="src/api/users.py")
    G.add_node("src/api/auth.py", path="src/api/auth.py")
    G.add_node("src/services/billing.py", path="src/services/billing.py")
    G.add_node("cli.py", path="cli.py")

    boundaries = detect_boundaries(G, repo)
    assert boundaries["src/api/users.py"] == "api"
    assert boundaries["src/api/auth.py"] == "api"
    assert boundaries["src/services/billing.py"] == "services"
    assert boundaries["cli.py"] == "root"
