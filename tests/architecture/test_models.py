"""Tests for architecture data models."""
import pytest
from architecture.models import (
    Module,
    Component,
    ArchitectureRelationship,
    ArchitectureFlow,
    ArchitectureConfig,
    ArchitectureModel,
)
from architecture.exceptions import (
    ArchitectureError,
    GraphValidationError,
    ComponentResolutionError,
    MissingDependencyError,
)


def test_module_model():
    mod = Module(
        id="services/auth.py",
        path="services/auth.py",
        symbols=["uuid-1", "uuid-2"],
        symbol_count=2,
        incoming_modules=["api/login.py"],
        outgoing_modules=["db/users.py"],
        incoming_weight=3,
        outgoing_weight=2,
        metadata={"internal_relationship_count": 1},
    )
    assert mod.id == "services/auth.py"
    assert mod.symbol_count == 2
    d = mod.to_dict()
    assert d["id"] == "services/auth.py"
    assert d["symbol_count"] == 2
    assert d["incoming_weight"] == 3


def test_component_model():
    comp = Component(
        id="services",
        name="services",
        modules=["services/auth.py", "services/token.py"],
        discovery_methods=["BOUNDARY_AND_COMMUNITY"],
        confidence=0.85,
        metadata={"internal_weight": 5},
    )
    assert comp.id == "services"
    assert len(comp.modules) == 2
    assert comp.confidence == 0.85
    d = comp.to_dict()
    assert d["name"] == "services"
    assert d["confidence"] == 0.85


def test_relationship_and_flow():
    rel = ArchitectureRelationship(
        source="api",
        target="services",
        weight=47,
        relationship_types={"CALL": 31, "IMPORT": 16},
    )
    assert rel.weight == 47
    d_rel = rel.to_dict()
    assert d_rel["relationship_types"]["CALL"] == 31

    flow = ArchitectureFlow(
        source="api",
        target="persistence",
        path=["api", "services", "persistence"],
        evidence={"shortest_path_length": 2},
    )
    assert len(flow.path) == 3
    d_flow = flow.to_dict()
    assert d_flow["path"] == ["api", "services", "persistence"]


def test_architecture_model_and_config():
    config = ArchitectureConfig()
    assert "src" in config.ignored_boundaries
    assert config.max_flows == 10

    model = ArchitectureModel(
        repository_root="/path/to/repo",
        modules={},
        components={},
    )
    assert model.repository_root == "/path/to/repo"
    assert model.modules == {}


def test_exceptions_hierarchy():
    assert issubclass(GraphValidationError, ArchitectureError)
    assert issubclass(ComponentResolutionError, ArchitectureError)
    assert issubclass(MissingDependencyError, ArchitectureError)
