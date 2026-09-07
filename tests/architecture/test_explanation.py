"""
Unit and Integration Tests for Human Explanation & DeepWiki Engine
==================================================================
"""
from pathlib import Path
import pytest

from architecture.analyzer import ArchitectureAnalyzer
from architecture.explanation import (
    DeterministicExplanationProvider,
    ExplanationEngine,
    LLMExplanationProvider,
    RelationshipExplanation,
)


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


def test_explanation_levels_simple_layered(fixtures_dir):
    repo = fixtures_dir / "simple_layered"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    engine = ExplanationEngine()

    # Level 1: Repository Overview
    repo_doc = engine.explain_repository(model, None)
    assert "Technical Architecture Guide" in repo_doc
    assert "simple_layered" in repo_doc
    assert "Executive Summary" in repo_doc
    assert "Major Subsystems" in repo_doc

    # Level 2: Architecture & Interactions
    arch_doc = engine.explain_architecture(model)
    assert "Architectural Layers & Component Interactions" in arch_doc
    assert "Component:" in arch_doc

    # Level 3: Module Documentation
    mod_doc = engine.explain_module("api/main.py", model, None)
    assert mod_doc["id"] == "api/main.py"
    assert "role" in mod_doc
    assert "purpose" in mod_doc
    assert len(mod_doc["purpose"]) > 0

    # Level 4: Symbol Documentation
    sym_doc = engine.explain_symbol("main", "api/main.py", None)
    assert sym_doc["symbol"] == "main"
    assert sym_doc["module"] == "api/main.py"

    # Level 5: Relationship Explanation ("Why does A depend on B?")
    rel_doc = engine.explain_relationship("api/main.py", "services/auth.py", model, None)
    assert isinstance(rel_doc, RelationshipExplanation)
    assert rel_doc.source == "api/main.py"
    assert rel_doc.target == "services/auth.py"
    assert len(rel_doc.summary) > 0
    assert len(rel_doc.architectural_intent) > 0

    rel_dict = rel_doc.to_dict()
    assert rel_dict["source"] == "api/main.py"
    assert rel_dict["target"] == "services/auth.py"


def test_llm_provider_fallback(fixtures_dir):
    repo = fixtures_dir / "simple_layered"
    analyzer = ArchitectureAnalyzer(repo)
    model = analyzer.analyze()

    llm_provider = LLMExplanationProvider(model_name="test-model")
    engine = ExplanationEngine(provider=llm_provider)

    repo_doc = engine.explain_repository(model, None)
    assert "Technical Architecture Guide" in repo_doc

    rel_doc = engine.explain_relationship("api/main.py", "services/auth.py", model, None)
    assert rel_doc.source == "api/main.py"
