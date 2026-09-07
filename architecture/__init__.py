"""
Karuvi Architecture Reconstruction Engine & DeepWiki Integration
================================================================

Reconstructs repository architecture completely identical to DeepWiki:
- Multi-provider AI connectivity (Gemini, OpenAI, OpenRouter, Ollama, Anthropic)
- Source-grounded architecture structure & wiki generation
- Interactive vis.Network architecture graphs & living codebase cartography
"""
from __future__ import annotations

from architecture.analyzer import ArchitectureAnalyzer
from architecture.deepwiki_engine import DeepWikiEngine
from architecture.documentation import generate_architecture_markdown
from architecture.exceptions import (
    ArchitectureError,
    ComponentResolutionError,
    GraphValidationError,
    MissingDependencyError,
)
from architecture.models import (
    ArchitectureConfig,
    ArchitectureFlow,
    ArchitectureModel,
    ArchitectureRelationship,
    Component,
    Module,
    WikiCacheData,
    WikiPage,
    WikiSection,
    WikiStructureModel,
)
from architecture.providers import (
    AIProviderConfig,
    generate_completion,
    is_provider_configured,
)
from architecture.serialization import (
    export_architecture_json,
    serialize_architecture_model,
)
from architecture.visualizer import (
    build_unified_payload,
    generate_atlas_html,
)

__all__ = [
    "AIProviderConfig",
    "ArchitectureAnalyzer",
    "ArchitectureConfig",
    "ArchitectureError",
    "ArchitectureFlow",
    "ArchitectureModel",
    "ArchitectureRelationship",
    "Component",
    "ComponentResolutionError",
    "DeepWikiEngine",
    "GraphValidationError",
    "MissingDependencyError",
    "Module",
    "WikiCacheData",
    "WikiPage",
    "WikiSection",
    "WikiStructureModel",
    "build_unified_payload",
    "export_architecture_json",
    "generate_architecture_markdown",
    "generate_atlas_html",
    "generate_completion",
    "is_provider_configured",
    "serialize_architecture_model",
]
