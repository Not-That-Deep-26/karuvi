"""
Tests for DeepWiki Architecture Engine, Multi-Provider Support, and Interactive Network Integration.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from architecture.deepwiki_engine import (
    DeepWikiEngine,
    read_repo_file_tree,
    parse_wiki_structure,
    post_process_wiki_content,
)
from architecture.deepwiki_prompts import build_structure_prompt, build_page_prompt
from architecture.models import ArchitectureConfig, WikiPage, WikiSection, WikiStructureModel
from architecture.providers import (
    AIProviderConfig,
    generate_completion,
    is_provider_configured,
)
from architecture.analyzer import ArchitectureAnalyzer
from architecture.visualizer import build_unified_payload, generate_atlas_html
from cli import analyze_repository


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


def test_read_repo_file_tree(fixtures_dir):
    repo = fixtures_dir / "simple_layered"
    tree = read_repo_file_tree(repo)
    assert "api" in tree
    assert "main.py" in tree
    assert "services" in tree
    assert "repositories" in tree


def test_parse_wiki_structure_valid_xml():
    xml_response = """
    <wiki_structure>
      <section id="arch-overview" title="Architecture Overview" description="High level system view">
        <page id="system-design" title="System Design" description="Core structural patterns" importance="high">
          <files>api/main.py, services/auth.py</files>
        </page>
      </section>
      <section id="data-layer" title="Data Persistence" description="Database repositories">
        <page id="user-repo" title="User Repository" description="Access layer" importance="medium">
          <files>repositories/users.py</files>
        </page>
      </section>
    </wiki_structure>
    """
    struct = parse_wiki_structure(xml_response)
    assert len(struct.sections) == 2
    assert len(struct.pages) == 2

    assert struct.sections[0].id == "arch-overview"
    assert struct.sections[0].title == "Architecture Overview"
    assert struct.sections[1].id == "data-layer"

    p1 = struct.pages[0]
    assert p1.id == "system-design"
    assert p1.title == "System Design"
    assert p1.parent_section == "arch-overview"
    assert "api/main.py" in p1.file_paths
    assert "services/auth.py" in p1.file_paths
    assert p1.importance == "high"


def test_parse_wiki_structure_fallback_on_malformed_xml():
    malformed = "This is not valid XML at all, just plain text from an LLM."
    struct = parse_wiki_structure(malformed)
    assert len(struct.sections) >= 1
    assert len(struct.pages) >= 1
    assert struct.pages[0].id == "system-overview"


def test_post_process_wiki_content():
    raw_content = """
    ### Security Layer
    Authentication is handled strictly in services.
    
    Sources: [services/auth.py:12-40](file://services/auth.py#L12-L40)
    See also [api/main.py](api/main.py).
    """
    processed = post_process_wiki_content(raw_content)
    assert "#code:services/auth.py:12-40" in processed
    assert "#code:api/main.py" in processed


def test_ai_provider_resolution():
    # 1. Offline provider
    cfg_offline = AIProviderConfig(provider="offline").resolve()
    assert cfg_offline.provider == "offline"

    # 2. Gemini
    cfg_gemini = AIProviderConfig(provider="gemini", api_key="dummy-key", model="gemini-2.5-flash").resolve()
    assert cfg_gemini.model == "gemini-2.5-flash"
    assert cfg_gemini.provider == "gemini"
    assert cfg_gemini.api_key == "dummy-key"

    # 3. OpenAI
    cfg_openai = AIProviderConfig(provider="openai", api_key="sk-test", model="gpt-4o").resolve()
    assert cfg_openai.model == "gpt-4o"
    assert cfg_openai.provider == "openai"

    # 4. OpenRouter
    cfg_openrouter = AIProviderConfig(provider="openrouter", api_key="sk-or-test", model="anthropic/claude-3.5-sonnet").resolve()
    assert cfg_openrouter.provider == "openrouter"
    assert cfg_openrouter.model == "anthropic/claude-3.5-sonnet"

    # 5. Ollama
    cfg_ollama = AIProviderConfig(provider="ollama", model="llama3.1").resolve()
    assert cfg_ollama.provider == "ollama"
    assert cfg_ollama.base_url == "http://localhost:11434"

    # 6. Anthropic
    cfg_anthropic = AIProviderConfig(provider="anthropic", api_key="ant-key", model="claude-3-5-sonnet-20241022").resolve()
    assert cfg_anthropic.provider == "anthropic"

    # 7. Custom
    cfg_custom = AIProviderConfig(provider="custom", base_url="http://localhost:8080/v1", model="my-custom-model").resolve()
    assert cfg_custom.base_url == "http://localhost:8080/v1"


def test_offline_fallback_provider_generation(fixtures_dir):
    repo = fixtures_dir / "simple_layered"
    cfg = AIProviderConfig(provider="offline")
    engine = DeepWikiEngine(repo, provider_config=cfg)
    
    file_tree = read_repo_file_tree(repo)
    structure_xml = engine._generate_fallback_structure(repo.name, file_tree)
    assert "<wiki_structure>" in structure_xml
    assert "</wiki_structure>" in structure_xml

    page = WikiPage(id="test-page", title="API Interfaces", description="HTTP handlers", file_paths=["api/main.py"])
    page_content = engine._generate_fallback_page_content(repo.name, page, file_tree)
    assert "# API Interfaces" in page_content
    assert "Sources:" in page_content


def test_deepwiki_engine_full_run(fixtures_dir, tmp_path):
    repo = fixtures_dir / "simple_layered"
    cfg = AIProviderConfig(provider="offline")
    engine = DeepWikiEngine(repo, provider_config=cfg)

    wiki = engine.generate_wiki(use_cache=False, comprehensive=False)
    assert wiki.repository_name == "simple_layered"
    assert len(wiki.wiki_structure.sections) >= 1
    assert len(wiki.wiki_structure.pages) >= 1
    assert len(wiki.pages) >= 1

    # Check that pages have title and source grounding
    for page in wiki.pages.values():
        assert len(page.title) > 0
        assert len(page.content) > 0

    # Test markdown export
    md_text = engine.export_wiki_markdown(wiki)
    assert "# simple_layered Architecture Wiki" in md_text
    assert "DeepWiki" in md_text


def test_architecture_vis_network_canvas_no_mermaid(fixtures_dir):
    """Verify that architecture graph is rendered on vis.Network canvas without Mermaid."""
    repo = fixtures_dir / "simple_layered"
    _, _, builder = analyze_repository(repo, verbose=False)
    analyzer = ArchitectureAnalyzer(repo, config=ArchitectureConfig(ai_provider="offline"))
    arch_model = analyzer.analyze(builder)

    # Verify DeepWiki integration into ArchitectureModel
    assert arch_model.wiki_structure is not None
    assert len(arch_model.wiki_pages) >= 1

    # Generate Atlas HTML
    html = generate_atlas_html(builder, arch_model)

    # 1. Mermaid must be completely removed
    assert "mermaid" not in html.lower()

    # 2. Vis.Network is used for both modules and architecture
    assert "vis-network" in html
    assert 'id="network-canvas"' in html

    # 3. In Graph Explorer, symbols(deep) is removed
    assert 'data-level="symbols"' not in html
    assert 'data-level="modules"' in html
    assert 'data-level="architecture"' in html

    # 4. DeepWiki Tab is active with provider modal and navigation tree
    assert 'id="deepwiki-tree"' in html
    assert 'id="deepwiki-content"' in html
    assert 'id="provider-config-modal"' in html
    assert 'id="sel-ai-provider"' in html
