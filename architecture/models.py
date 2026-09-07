"""
Architecture Reconstruction Engine Data Models
==============================================

Explicit dataclass models defining the architectural abstractions:
DeepWiki WikiPage, WikiSection, WikiStructureModel, WikiCacheData,
as well as Modules, Components, Relationships, Flows, and the overall ArchitectureModel.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WikiPage:
    """Represents a single DeepWiki technical documentation page."""
    id: str
    title: str
    content: str = ""
    file_paths: list[str] = field(default_factory=list)
    importance: str = "medium"  # 'high' | 'medium' | 'low'
    related_pages: list[str] = field(default_factory=list)
    parent_section: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "filePaths": self.file_paths,
            "importance": self.importance,
            "relatedPages": self.related_pages,
            "parentSection": self.parent_section,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WikiPage:
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            content=d.get("content", ""),
            file_paths=d.get("filePaths") or d.get("file_paths") or [],
            importance=d.get("importance", "medium"),
            related_pages=d.get("relatedPages") or d.get("related_pages") or [],
            parent_section=d.get("parentSection") or d.get("parent_section"),
        )


@dataclass
class WikiSection:
    """Represents a section in the DeepWiki architecture structure."""
    id: str
    title: str
    pages: list[str] = field(default_factory=list)
    subsections: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "pages": self.pages,
            "subsections": self.subsections,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WikiSection:
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            pages=d.get("pages", []),
            subsections=d.get("subsections"),
        )


@dataclass
class WikiStructureModel:
    """Represents the complete DeepWiki architecture structure."""
    id: str
    title: str
    description: str
    pages: list[WikiPage] = field(default_factory=list)
    sections: list[WikiSection] = field(default_factory=list)
    root_sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "pages": [p.to_dict() for p in self.pages],
            "sections": [s.to_dict() for s in self.sections],
            "rootSections": self.root_sections,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WikiStructureModel:
        return cls(
            id=d.get("id", "root"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            pages=[WikiPage.from_dict(p) for p in d.get("pages", [])],
            sections=[WikiSection.from_dict(s) for s in d.get("sections", [])],
            root_sections=d.get("rootSections") or d.get("root_sections") or [],
        )


@dataclass
class WikiCacheData:
    """Stores the cached architecture wiki for instant loading."""
    wiki_structure: WikiStructureModel
    generated_pages: dict[str, WikiPage]
    provider: str | None = None
    model: str | None = None
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "wiki_structure": self.wiki_structure.to_dict(),
            "generated_pages": {k: v.to_dict() for k, v in self.generated_pages.items()},
            "provider": self.provider,
            "model": self.model,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WikiCacheData:
        ws = WikiStructureModel.from_dict(d.get("wiki_structure", {}))
        gp = {}
        for k, v in (d.get("generated_pages") or {}).items():
            gp[k] = WikiPage.from_dict(v)
        return cls(
            wiki_structure=ws,
            generated_pages=gp,
            provider=d.get("provider"),
            model=d.get("model"),
            timestamp=d.get("timestamp", 0.0),
        )


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
    """Represents an architectural component / subsystem."""
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "path": self.path,
            "evidence": self.evidence,
        }


@dataclass
class ArchitectureConfig:
    """Configuration options for architecture reconstruction and DeepWiki generation."""
    ai_provider: str = "auto"
    ai_model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    comprehensive: bool = True
    language: str = "en"
    use_cache: bool = True
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
    wiki_structure: WikiStructureModel | None = None
    wiki_pages: dict[str, WikiPage] = field(default_factory=dict)
    wiki_cache: WikiCacheData | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from architecture.serialization import serialize_architecture_model
        return serialize_architecture_model(self)
