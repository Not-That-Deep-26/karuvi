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
    "export_architecture_json",
    "generate_architecture_markdown",
    "serialize_architecture_model",
]
