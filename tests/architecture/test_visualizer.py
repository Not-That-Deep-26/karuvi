"""
Tests for Karuvi Living Codebase Atlas Web Visualizer
=====================================================

Validates:
1. Unified payload generation (`build_unified_payload`) combining Stage 1 & Stage 2 models.
2. Complete standalone HTML generation (`generate_atlas_html`) with embedded JSON.
3. Integration with `RepoGraphBuilder.render_html()`.
"""
import json
from pathlib import Path
import pytest

from architecture.analyzer import ArchitectureAnalyzer
from architecture.visualizer import build_unified_payload, generate_atlas_html
from cli import analyze_repository


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


def test_build_unified_payload(fixtures_dir):
    """Verify build_unified_payload creates a comprehensive, correctly structured payload."""
    repo = fixtures_dir / "simple_layered"
    _, _, builder = analyze_repository(repo, verbose=False)
    analyzer = ArchitectureAnalyzer(repo)
    arch_model = analyzer.analyze(builder)

    payload = build_unified_payload(builder, arch_model)

    # 1. Top-level keys
    assert "summary" in payload
    assert "components" in payload
    assert "modules" in payload
    assert "module_edges" in payload
    assert "component_edges" in payload
    assert "entrypoints" in payload
    assert "flows" in payload
    assert "documentation_md" in payload

    # 2. Summary stats
    summary = payload["summary"]
    assert summary["total_modules"] == 4
    assert summary["total_components"] >= 1
    assert summary["total_edges"] >= 3
    assert "total_lines" in summary
    assert "circular_dependencies" in summary

    # 3. Component details
    components = payload["components"]
    assert len(components) >= 1
    for c in components:
        assert "id" in c
        assert "name" in c
        assert "modules" in c
        assert "confidence" in c
        assert "evidence" in c
        assert "role" in c

    # 4. Module details
    modules = payload["modules"]
    assert len(modules) == 4
    for m in modules:
        assert "id" in m
        assert "path" in m
        assert "name" in m
        assert "component_id" in m
        assert "role" in m
        assert "in_degree" in m
        assert "out_degree" in m

    # 5. Entry points and flows
    assert len(payload["entrypoints"]) >= 1
    top_entry = payload["entrypoints"][0]
    assert "module" in top_entry
    assert "entry_score" in top_entry
    assert "evidence" in top_entry

    # 6. Documentation
    assert len(payload["documentation_md"]) > 100
    assert "# Repository Architecture" in payload["documentation_md"]


def test_generate_atlas_html(fixtures_dir):
    """Verify generate_atlas_html produces complete, standalone, zero-dependency HTML."""
    repo = fixtures_dir / "simple_layered"
    _, _, builder = analyze_repository(repo, verbose=False)
    analyzer = ArchitectureAnalyzer(repo)
    arch_model = analyzer.analyze(builder)

    html = generate_atlas_html(builder, arch_model)

    # Basic HTML checks
    assert html.startswith("<!DOCTYPE html>")
    assert "<title>Karuvi — Living Codebase Atlas</title>" in html
    assert "vis-network" in html
    assert "Inter" in html

    # Verify embedded payload JSON is valid and loadable
    marker = "window.KARUVI_DATA = "
    assert marker in html
    start_idx = html.find(marker) + len(marker)
    end_idx = html.find(";\n", start_idx)
    raw_json = html[start_idx:end_idx]
    data = json.loads(raw_json)

    assert data["summary"]["total_modules"] == 4
    assert len(data["components"]) >= 1
    assert len(data["modules"]) == 4

    # Verify UI sections and view IDs are present
    assert 'id="tab-overview"' in html
    assert 'id="tab-architecture"' in html
    assert 'id="tab-graph"' in html
    assert 'id="tab-code"' in html
    assert 'id="tab-docs"' in html
    assert 'id="search-modal-overlay"' in html
    assert 'id="global-search-input"' in html
    assert 'id="network-canvas"' in html
    assert 'switchTab(' in html
    assert 'window.switchView' in html
    assert 'toggleUnfold(' in html
    assert 'unfoldedComponents' in html


def test_builder_render_html_integration(fixtures_dir):
    """Verify RepoGraphBuilder.render_html() invokes the Atlas generator seamlessly."""
    repo = fixtures_dir / "simple_layered"
    _, _, builder = analyze_repository(repo, verbose=False)

    # Calling render_html directly on builder
    html = builder.render_html()
    assert "<!DOCTYPE html>" in html
    assert "<title>Karuvi — Living Codebase Atlas</title>" in html
    assert "window.__KARUVI_DATA__" in html
