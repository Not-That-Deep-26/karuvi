"""
Karuvi Architecture Reconstruction Engine
=========================================

Deterministic architecture reconstruction layer for Python codebases.
"""
from __future__ import annotations

from architecture.analyzer import ArchitectureAnalyzer
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
    "ArchitectureAnalyzer",
    "ArchitectureConfig",
    "ArchitectureError",
    "ArchitectureFlow",
    "ArchitectureModel",
    "ArchitectureRelationship",
    "Component",
    "ComponentResolutionError",
    "GraphValidationError",
    "MissingDependencyError",
    "Module",
    "build_unified_payload",
    "export_architecture_json",
    "generate_architecture_markdown",
    "generate_atlas_html",
    "serialize_architecture_model",
]
