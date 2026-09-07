"""
Karuvi Human Explanation & DeepWiki Engine
==========================================

Generates multi-level progressive explanations (Levels 1 to 5) grounded strictly
in deterministic code intelligence, with a modular provider abstraction supporting
both local deterministic templates and optional LLM backends.

Levels:
  Level 1 — Repository Overview & Purpose
  Level 2 — Architecture & Subsystem Interactions
  Level 3 — Module Documentation & Dependencies
  Level 4 — Symbol Documentation & Impact
  Level 5 — Relationship Explanation ("Why does A depend on B?")
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import networkx as nx

from architecture.models import ArchitectureModel, Component, Module


@dataclass
class RelationshipExplanation:
    """Explains why a directed dependency exists between two entities."""
    source: str
    target: str
    summary: str
    imported_symbols: list[str] = field(default_factory=list)
    call_occurrences: list[dict[str, Any]] = field(default_factory=list)
    source_role: str = "MODULE"
    target_role: str = "MODULE"
    architectural_intent: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "summary": self.summary,
            "imported_symbols": self.imported_symbols,
            "call_occurrences": self.call_occurrences,
            "source_role": self.source_role,
            "target_role": self.target_role,
            "architectural_intent": self.architectural_intent,
        }


class ExplanationProvider(ABC):
    """Abstract interface for explanation providers."""

    @abstractmethod
    def explain_repository(self, model: ArchitectureModel, repo_builder: Any) -> str:
        """Generate high-level technical wiki overview of the repository (Level 1)."""
        pass

    @abstractmethod
    def explain_architecture(self, model: ArchitectureModel) -> str:
        """Generate architectural subsystem explanations and communication flows (Level 2)."""
        pass

    @abstractmethod
    def explain_module(self, mod_id: str, model: ArchitectureModel, repo_builder: Any) -> dict[str, Any]:
        """Generate purposeful documentation for a specific module (Level 3)."""
        pass

    @abstractmethod
    def explain_symbol(self, symbol_name: str, mod_id: str, repo_builder: Any) -> dict[str, Any]:
        """Generate symbol impact and contract documentation (Level 4)."""
        pass

    @abstractmethod
    def explain_relationship(
        self,
        source: str,
        target: str,
        model: ArchitectureModel,
        repo_builder: Any,
    ) -> RelationshipExplanation:
        """Explain why source depends on target based on structural evidence (Level 5)."""
        pass


class DeterministicExplanationProvider(ExplanationProvider):
    """
    Default offline provider. Uses deterministic AST symbol analysis, structural
    roles, and dependency graph topology to synthesize human-readable explanations.
    """

    def explain_repository(self, model: ArchitectureModel, repo_builder: Any) -> str:
        repo_name = Path(model.repository_root).name
        num_mods = len(model.modules)
        num_comps = len(model.components)
        
        if repo_builder and hasattr(repo_builder, "cycles"):
            cycles = repo_builder.cycles
        elif model.module_graph is not None:
            try:
                cycles = list(nx.simple_cycles(model.module_graph))
            except Exception:
                cycles = []
        else:
            cycles = []
        num_cycles = len(cycles)
        
        entry_pt_desc = "None detected"
        if model.entry_points:
            top_m = model.entry_points[0]["module"]
            entry_pt_desc = f"`{top_m}` (high reach, minimal inbound coupling)"

        lines = [
            f"# {repo_name} — Technical Architecture Guide",
            "",
            f"**{repo_name}** is a Python codebase comprising **{num_mods} modules** organized into **{num_comps} architectural components**.",
            "",
            "## Executive Summary",
            f"- **Primary Entry Point**: {entry_pt_desc}",
            f"- **Architectural Components**: {', '.join(f'`{c.name}`' for c in model.components.values()) or 'Single monolithic package'}",
            f"- **Circular Dependency Loops**: {'None detected (Clean DAG)' if num_cycles == 0 else f'⚠️ {num_cycles} circular loops present'}",
            "",
            "## Major Subsystems",
        ]

        for comp in model.components.values():
            role_desc = self._describe_component_role(comp)
            lines.append(f"### {comp.name}")
            lines.append(f"- **Role**: {role_desc}")
            lines.append(f"- **Confidence Score**: `{round(comp.confidence * 100, 1)}%` (grounded in directory boundaries & graph clustering)")
            lines.append(f"- **Key Modules**: {', '.join(f'`{Path(m).name}`' for m in comp.modules[:4])}")
            lines.append("")

        if model.flows:
            lines.append("## Core Execution & Architecture Flows")
            for flow in model.flows:
                path_steps = " ➔ ".join(f"`{step}`" for step in flow.path)
                lines.append(f"- {path_steps}")
            lines.append("")

        return "\n".join(lines)

    def explain_architecture(self, model: ArchitectureModel) -> str:
        lines = ["# Architectural Layers & Component Interactions\n"]
        for comp_id, comp in model.components.items():
            deps = [t for s, t in model.component_graph.out_edges(comp_id)]
            dep_by = [s for s, t in model.component_graph.in_edges(comp_id)]
            
            lines.append(f"## Component: {comp.name}")
            lines.append(f"**Functional Role**: {self._describe_component_role(comp)}")
            lines.append(f"- **Confidence**: `{round(comp.confidence * 100, 1)}%`")
            lines.append(f"- **Depends on**: {', '.join(f'`{d}`' for d in deps) or '_None (Leaf layer)_'}")
            lines.append(f"- **Depended on by**: {', '.join(f'`{d}`' for d in dep_by) or '_None (Root / Entry layer)_'}")
            lines.append(f"- **Modules**: {', '.join(f'`{m}`' for m in comp.modules)}")
            lines.append("")
        return "\n".join(lines)

    def explain_module(self, mod_id: str, model: ArchitectureModel, repo_builder: Any) -> dict[str, Any]:
        mod = model.modules.get(mod_id)
        if not mod:
            return {"id": mod_id, "error": "Module not found"}

        role = model.roles.get(mod_id, "MODULE")
        role_explanation = self._describe_module_role(role)
        
        # Discover symbols if parsed
        functions = []
        classes = []
        if repo_builder and hasattr(repo_builder, "parsed") and mod_id in repo_builder.parsed:
            p_mod = repo_builder.parsed[mod_id]
            functions = [f.name for f in p_mod.functions]
            classes = [c.name for c in p_mod.classes]

        # Why this module exists
        purpose = self._synthesize_module_purpose(mod_id, role, classes, functions)

        return {
            "id": mod_id,
            "name": Path(mod_id).name,
            "path": mod.path,
            "role": role,
            "role_description": role_explanation,
            "purpose": purpose,
            "incoming_dependents": list(mod.incoming_modules),
            "outgoing_dependencies": list(mod.outgoing_modules),
            "classes": classes,
            "functions": functions,
        }

    def explain_symbol(self, symbol_name: str, mod_id: str, repo_builder: Any) -> dict[str, Any]:
        callers = []
        decl_line = 1
        sym_type = "symbol"
        uuid_str = None

        if repo_builder and hasattr(repo_builder, "parsed") and mod_id in repo_builder.parsed:
            p_mod = repo_builder.parsed[mod_id]
            for fn in p_mod.functions:
                if fn.name == symbol_name:
                    sym_type = "function"
                    uuid_str = str(fn.uuid) if fn.uuid else None
                    break
            if sym_type == "symbol":
                for cl in p_mod.classes:
                    if cl.name == symbol_name:
                        sym_type = "class"
                        uuid_str = str(cl.uuid) if cl.uuid else None
                        break

        # Check cross-module references
        if repo_builder and hasattr(repo_builder, "cross_references"):
            for xref in repo_builder.cross_references:
                if xref.get("symbol") == symbol_name and xref.get("target_file") == mod_id:
                    callers.append({
                        "file": xref.get("source_file"),
                        "line": xref.get("decl_line"),
                    })

        return {
            "symbol": symbol_name,
            "module": mod_id,
            "type": sym_type,
            "uuid": uuid_str,
            "cross_module_references_count": len(callers),
            "callers": callers[:10],
            "description": f"{sym_type.capitalize()} `{symbol_name}` declared in `{mod_id}`. Used by {len(callers)} external sites across the repository.",
        }

    def explain_relationship(
        self,
        source: str,
        target: str,
        model: ArchitectureModel,
        repo_builder: Any,
    ) -> RelationshipExplanation:
        """
        Synthesizes an exact, grounded explanation for why source imports target.
        """
        src_role = model.roles.get(source, "MODULE")
        tgt_role = model.roles.get(target, "MODULE")

        # Discover imported symbols between source and target
        imported_syms = []
        call_occurrences = []

        if repo_builder and hasattr(repo_builder, "cross_references"):
            for xref in repo_builder.cross_references:
                if xref.get("source_file") == source and xref.get("target_file") == target:
                    sym = xref.get("symbol")
                    if sym and sym not in imported_syms:
                        imported_syms.append(sym)
                    call_occurrences.append({
                        "symbol": sym,
                        "line": xref.get("decl_line"),
                    })

        # Also check direct module imports if symbols are empty
        if not imported_syms and repo_builder and hasattr(repo_builder, "parsed") and source in repo_builder.parsed:
            p_mod = repo_builder.parsed[source]
            for imp in getattr(p_mod.scope, "imports", []):
                if target in imp or Path(target).stem in imp:
                    imported_syms.append(imp)

        # Build natural language summary
        src_name = Path(source).name
        tgt_name = Path(target).name
        
        if imported_syms:
            sym_list = ", ".join(f"`{s}`" for s in imported_syms[:4])
            summary = f"`{src_name}` depends on `{tgt_name}` to utilize symbols: {sym_list}."
        else:
            summary = f"`{src_name}` imports `{tgt_name}` as an architectural dependency."

        intent = self._infer_architectural_intent(source, target, src_role, tgt_role, imported_syms)

        return RelationshipExplanation(
            source=source,
            target=target,
            summary=summary,
            imported_symbols=imported_syms,
            call_occurrences=call_occurrences[:10],
            source_role=src_role,
            target_role=tgt_role,
            architectural_intent=intent,
        )

    def _describe_component_role(self, comp: Component) -> str:
        name_lower = comp.name.lower()
        if any(w in name_lower for w in ["api", "route", "server", "web"]):
            return "Interface Layer: Ingests requests and coordinates protocol input/output."
        elif any(w in name_lower for w in ["service", "core", "domain", "logic"]):
            return "Domain Business Layer: Encapsulates business rules and operational workflows."
        elif any(w in name_lower for w in ["db", "repo", "store", "database", "model"]):
            return "Persistence Layer: Manages database transactions and storage abstractions."
        elif any(w in name_lower for w in ["util", "helper", "common", "base"]):
            return "Utility & Foundation Layer: Provides shared primitives and helper routines."
        elif any(w in name_lower for w in ["auth", "security", "session"]):
            return "Security & Identity: Manages authentication, tokens, and authorization boundaries."
        return "Cohesive Architectural Subsystem."

    def _describe_module_role(self, role: str) -> str:
        roles = {
            "ENTRY_CANDIDATE": "Entry Point: High downstream reach with low incoming coupling. Primary place where execution starts.",
            "HUB": "Central Hub: High connectivity coordinating multiple internal modules.",
            "BRIDGE": "Structural Bridge: Critical bottleneck connecting separate architectural subsystems.",
            "LEAF": "Leaf / Foundation: Pure utility or data model with zero internal outward imports.",
            "MODULE": "Standard internal component module.",
        }
        return roles.get(role, "Internal repository module.")

    def _synthesize_module_purpose(self, mod_id: str, role: str, classes: list[str], functions: list[str]) -> str:
        name = Path(mod_id).stem.replace("_", " ")
        if role == "ENTRY_CANDIDATE":
            return f"Bootstraps and configures the {name} lifecycle, dispatching commands and initiating program workflows."
        elif role == "LEAF":
            return f"Encapsulates self-contained {name} entities, models, or utilities without relying on external business logic."
        elif role == "BRIDGE":
            return f"Mediates communication across subsystems, transforming data structures and routing calls."
        elif role == "HUB":
            return f"Coordinates central operations for {name}, serving as a high-traffic routing junction for multiple services."
        return f"Implements core {name} logic, exposing {len(classes)} classes and {len(functions)} top-level functions."

    def _infer_architectural_intent(
        self,
        source: str,
        target: str,
        src_role: str,
        tgt_role: str,
        symbols: list[str],
    ) -> str:
        tgt_lower = target.lower()
        if any(w in tgt_lower for w in ["model", "schema"]):
            return "Data Model Binding: Consumes shared schemas or entity definitions to ensure type-safe contracts."
        elif any(w in tgt_lower for w in ["db", "repo", "store"]):
            return "Persistence Access: Queries or persists operational state in underlying storage."
        elif any(w in tgt_lower for w in ["util", "helper"]):
            return "Utility Delegation: Reuses shared operational helpers and parsing primitives."
        elif any(w in tgt_lower for w in ["auth", "session"]):
            return "Security Enforcement: Delegates identity validation and session state verification."
        return f"Layered Call Flow: {src_role} delegates work downward to {tgt_role}."


class LLMExplanationProvider(ExplanationProvider):
    """
    Pluggable LLM provider that formats compressed structural context into prompts
    for Ollama, OpenAI-compatible APIs, or Gemini/Claude.
    Falls back gracefully to DeterministicExplanationProvider on any network failure.
    """

    def __init__(self, api_base: str | None = None, model_name: str = "default"):
        self.api_base = api_base
        self.model_name = model_name
        self.fallback = DeterministicExplanationProvider()

    def explain_repository(self, model: ArchitectureModel, repo_builder: Any) -> str:
        # Build compressed prompt context
        context = {
            "repository": Path(model.repository_root).name,
            "modules_count": len(model.modules),
            "components": [c.to_dict() for c in model.components.values()],
            "flows": [f.to_dict() for f in model.flows],
            "entry_points": model.entry_points[:3],
        }
        # For now, default to deterministic generation with LLM prompt envelope
        return self.fallback.explain_repository(model, repo_builder)

    def explain_architecture(self, model: ArchitectureModel) -> str:
        return self.fallback.explain_architecture(model)

    def explain_module(self, mod_id: str, model: ArchitectureModel, repo_builder: Any) -> dict[str, Any]:
        return self.fallback.explain_module(mod_id, model, repo_builder)

    def explain_symbol(self, symbol_name: str, mod_id: str, repo_builder: Any) -> dict[str, Any]:
        return self.fallback.explain_symbol(symbol_name, mod_id, repo_builder)

    def explain_relationship(self, source: str, target: str, model: ArchitectureModel, repo_builder: Any) -> RelationshipExplanation:
        return self.fallback.explain_relationship(source, target, model, repo_builder)


class ExplanationEngine:
    """
    Central coordinator for generating human-readable technical explanations.
    """

    def __init__(self, provider: ExplanationProvider | None = None):
        self.provider = provider or DeterministicExplanationProvider()

    def explain_repository(self, model: ArchitectureModel, repo_builder: Any) -> str:
        return self.provider.explain_repository(model, repo_builder)

    def explain_architecture(self, model: ArchitectureModel) -> str:
        return self.provider.explain_architecture(model)

    def explain_module(self, mod_id: str, model: ArchitectureModel, repo_builder: Any) -> dict[str, Any]:
        return self.provider.explain_module(mod_id, model, repo_builder)

    def explain_symbol(self, symbol_name: str, mod_id: str, repo_builder: Any) -> dict[str, Any]:
        return self.provider.explain_symbol(symbol_name, mod_id, repo_builder)

    def explain_relationship(self, source: str, target: str, model: ArchitectureModel, repo_builder: Any) -> RelationshipExplanation:
        return self.provider.explain_relationship(source, target, model, repo_builder)
