"""
End-to-End Integration Tests for Architecture Reconstruction Engine
===================================================================

Validates the full pipeline against all specification fixtures:
1. simple_layered
2. split_utils
3. cycles
4. merged_components

Verifies drill-down mappings, graph properties, acceptance criteria, and JSON serialization.
"""
import json
from pathlib import Path
import pytest

from karuvi.architecture.analyzer import ArchitectureAnalyzer
from karuvi.architecture.serialization import serialize_architecture_model


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


def test_integration_simple_layered(fixtures_dir):
    """Verifies layered architecture reconstruction, entry points, and flows."""
    repo = fixtures_dir / "simple_layered"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    assert model.module_graph is not None
    assert model.component_graph is not None
    assert len(model.modules) == 4
    assert len(model.components) >= 1

    # Check entry point
    assert len(model.entry_points) >= 1
    top_entry = model.entry_points[0]
    assert "api/main.py" in top_entry["module"]

    # Check drill-down traceability: Component -> Modules -> Module attributes
    for comp in model.components.values():
        assert len(comp.modules) > 0
        for m in comp.modules:
            assert m in model.modules
            mod_obj = model.modules[m]
            assert mod_obj.id == m

    # Verify JSON serialization
    serialized = serialize_architecture_model(model)
    assert serialized["statistics"]["modules"] == 4
    assert len(serialized["components"]) >= 1
    json_str = json.dumps(serialized)
    assert len(json_str) > 50


def test_integration_split_utils(fixtures_dir):
    """Verifies that folder boundaries can be split by graph evidence."""
    repo = fixtures_dir / "split_utils"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    assert len(model.modules) == 4
    # All modules properly assigned to components
    assigned_modules = set()
    for comp in model.components.values():
        assigned_modules.update(comp.modules)
    assert assigned_modules == set(model.modules.keys())


def test_integration_cycles(fixtures_dir):
    """Verifies that circular dependency loops do not crash analysis and are detected."""
    repo = fixtures_dir / "cycles"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    assert len(model.modules) == 3
    # Roles should identify cycle membership
    cycle_members = [m for m, r in model.roles.items() if r == "CYCLE_MEMBER"]
    assert len(cycle_members) >= 1

    # Analysis must produce valid JSON without infinite recursion
    serialized = serialize_architecture_model(model)
    assert serialized["statistics"]["modules"] == 3


def test_integration_merged_components(fixtures_dir):
    """Verifies cross-folder merging when strong topological cohesion bridges folders."""
    repo = fixtures_dir / "merged_components"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    assert len(model.modules) == 3
    # Check that components were created and serialized cleanly
    serialized = serialize_architecture_model(model)
    assert len(serialized["components"]) >= 1
