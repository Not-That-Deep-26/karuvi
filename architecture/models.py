"""
Architecture Reconstruction Engine Data Models
==============================================

Explicit dataclass models defining the architectural abstractions:
Modules, Components, Relationships, Flows, and the overall ArchitectureModel.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Module:
    """Represents a source module (file) in the architecture layer."""
    id: str
    path: str
    symbols: list[str] = field(default_factory=list)
    symbol_count: int = 0
    incoming_modules: list[str] = field(default_factory=list)
    outgoing_modules: list[str] = field(default_factory=list)
    incoming_weight: int = 0
    outgoing_weight: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "symbols": self.symbols,
            "symbol_count": self.symbol_count,
            "incoming_modules": self.incoming_modules,
            "outgoing_modules": self.outgoing_modules,
            "incoming_weight": self.incoming_weight,
            "outgoing_weight": self.outgoing_weight,
            "metadata": self.metadata,
        }


@dataclass
class Component:
    """Represents an architectural component derived from structural and graph evidence."""
    id: str
    name: str
    modules: list[str] = field(default_factory=list)
    discovery_methods: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "modules": self.modules,
            "discovery_methods": self.discovery_methods,
            "confidence": round(self.confidence, 3),
            "metadata": self.metadata,
        }


@dataclass
class ArchitectureRelationship:
    """Represents an aggregated directed dependency relationship between entities."""
    source: str
    target: str
    weight: int = 1
    relationship_types: dict[str, int] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "relationship_types": self.relationship_types,
            "evidence": self.evidence,
        }


@dataclass
class ArchitectureFlow:
    """Represents a high-level architectural path through components."""
    source: str
    target: str
    path: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    path_names: list[str] = field(default_factory=list)
    start_role: str = ""
    end_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "path": self.path,
            "evidence": self.evidence,
            "path_names": self.path_names,
            "start_role": self.start_role,
            "end_role": self.end_role,
        }


@dataclass
class ArchitectureConfig:
    """Configuration options for architecture reconstruction."""
    ignored_boundaries: set[str] = field(
        default_factory=lambda: {
            "src",
            "lib",
            "tests",
            "test",
            "__pycache__",
            "build",
            "dist",
            "site-packages",
            ".venv",
            "venv",
        }
    )
    max_flows: int = 10
    community_seed: int = 42
    strict_validation: bool = False
    cohesion_structural_weight: float = 0.4
    cohesion_graph_weight: float = 0.4
    cohesion_agreement_weight: float = 0.2


@dataclass
class ArchitectureModel:
    """Complete root model for the reconstructed repository architecture."""
    repository_root: str
    modules: dict[str, Module] = field(default_factory=dict)
    components: dict[str, Component] = field(default_factory=dict)
    module_graph: Any = None
    component_graph: Any = None
    entry_points: list[dict[str, Any]] = field(default_factory=list)
    roles: dict[str, str] = field(default_factory=dict)
    flows: list[ArchitectureFlow] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
