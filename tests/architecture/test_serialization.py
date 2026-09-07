"""Tests for JSON serialization and Markdown documentation."""
import json
from pathlib import Path
import networkx as nx
import pytest

from architecture.documentation import generate_architecture_markdown
from architecture.models import (
    ArchitectureFlow,
    ArchitectureModel,
    Component,
    Module,
)
from architecture.serialization import (
    export_architecture_json,
    serialize_architecture_model,
)


def test_serialization_and_documentation(tmp_path):
    MG = nx.DiGraph()
    MG.add_node("api/main.py", path="api/main.py", symbol_count=2, in_degree=0, out_degree=1)
    MG.add_node("services/auth.py", path="services/auth.py", symbol_count=3, in_degree=1, out_degree=0)
    MG.add_edge("api/main.py", "services/auth.py", weight=2, relationship_types={"CALL": 2})

    CG = nx.DiGraph()
    CG.add_node("api", name="api", module_count=1, confidence=0.9)
    CG.add_node("services", name="services", module_count=1, confidence=0.85)
    CG.add_edge("api", "services", weight=2, relationship_types={"CALL": 2})

    modules = {
        "api/main.py": Module(id="api/main.py", path="api/main.py", symbol_count=2),
        "services/auth.py": Module(id="services/auth.py", path="services/auth.py", symbol_count=3),
    }
    components = {
        "api": Component(id="api", name="api", modules=["api/main.py"], confidence=0.9),
        "services": Component(id="services", name="services", modules=["services/auth.py"], confidence=0.85),
    }

    flows = [ArchitectureFlow(source="api", target="services", path=["api", "services"])]
    entry_points = [{
        "module": "api/main.py",
        "entry_score": 0.95,
        "evidence": {"incoming_dependencies": 0, "reachable_modules": 1, "reachable_components": 1}
    }]

    model = ArchitectureModel(
        repository_root=str(tmp_path),
        modules=modules,
        components=components,
        module_graph=MG,
        component_graph=CG,
        entry_points=entry_points,
        roles={"api/main.py": "ENTRY_CANDIDATE", "services/auth.py": "LEAF"},
        flows=flows,
        metadata={"statistics": {}},
    )

    # Test serialization
    data = serialize_architecture_model(model)
    assert data["repository"] == str(tmp_path)
    assert data["statistics"]["modules"] == 2
    assert data["statistics"]["components"] == 2
    assert len(data["flows"]) == 1
    assert data["flows"][0]["path"] == ["api", "services"]

    # Test JSON file export
    json_path = tmp_path / "architecture.json"
    export_architecture_json(model, json_path)
    assert json_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["statistics"]["modules"] == 2

    # Test documentation generation
    md = generate_architecture_markdown(model)
    assert "# Repository Architecture" in md
    assert "api/main.py" in md
    assert "Component: api" in md
    assert "Component: services" in md
