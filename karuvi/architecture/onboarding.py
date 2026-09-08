"""
Karuvi Codebase Onboarding Engine
=================================

Computes the optimal, progressive reading order for a new engineer exploring
an unfamiliar repository.

Minimizes forward references by ordering concepts so prerequisites are
introduced before the modules that depend on them, while grouping circular
dependencies (SCCs) into unified conceptual units.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import networkx as nx

from .models import ArchitectureModel, Component, Module


@dataclass
class OnboardingStep:
    """Represents a discrete milestone in the codebase learning path."""
    step_number: int
    title: str
    concept: str
    target_modules: list[str]
    component_id: str | None = None
    component_name: str | None = None
    key_symbols: list[dict[str, str]] = field(default_factory=list)
    why_now: str = ""
    prerequisites_covered: list[str] = field(default_factory=list)
    next_unlocks: list[str] = field(default_factory=list)
    is_cycle_group: bool = False
    cycle_modules: list[str] = field(default_factory=list)
    beginner_summary: str = ""
    intermediate_summary: str = ""
    advanced_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "title": self.title,
            "concept": self.concept,
            "target_modules": self.target_modules,
            "component_id": self.component_id,
            "component_name": self.component_name,
            "key_symbols": self.key_symbols,
            "why_now": self.why_now,
            "prerequisites_covered": self.prerequisites_covered,
            "next_unlocks": self.next_unlocks,
            "is_cycle_group": self.is_cycle_group,
            "cycle_modules": self.cycle_modules,
            "beginner_summary": self.beginner_summary,
            "intermediate_summary": self.intermediate_summary,
            "advanced_summary": self.advanced_summary,
        }


@dataclass
class OnboardingPlan:
    """The complete curated reading plan for the codebase."""
    total_steps: int
    steps: list[OnboardingStep]
    estimated_read_time_minutes: int
    entry_point_module: str | None = None
    core_abstractions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_steps": self.total_steps,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_read_time_minutes": self.estimated_read_time_minutes,
            "entry_point_module": self.entry_point_module,
            "core_abstractions": self.core_abstractions,
        }


class CodebaseOnboardingEngine:
    """
    Constructs an optimal learning order across all modules in the repository.
    """

    def __init__(self, arch_model: ArchitectureModel, repo_builder: Any | None = None):
        self.arch_model = arch_model
        self.repo_builder = repo_builder
        self.module_graph: nx.DiGraph = arch_model.module_graph
        self.component_graph: nx.DiGraph = arch_model.component_graph

    def build_plan(self) -> OnboardingPlan:
        """
        Executes the reading order optimization algorithm.
        """
        modules = self.arch_model.modules
        if not modules:
            return OnboardingPlan(
                total_steps=0,
                steps=[],
                estimated_read_time_minutes=0,
            )

        # 1. Detect strongly connected components (SCCs) to handle cycles as single steps
        sccs = list(nx.strongly_connected_components(self.module_graph))
        multi_node_sccs = [scc for scc in sccs if len(scc) > 1]
        
        # Map each module to its SCC group if in a multi-node cycle
        scc_map: dict[str, set[str]] = {}
        for scc in multi_node_sccs:
            for m in scc:
                scc_map[m] = scc

        # 2. Categorize modules into conceptual learning tiers
        # Tier 0: Foundation / Models / Schemas / Utilities (leaves, lowest out-degree to business logic)
        # Tier 1: Storage / Persistence / Repositories
        # Tier 2: Core Domain Logic / Services / Engines (Bridges & Hubs)
        # Tier 3: API / Routing / Presentation / Auth
        # Tier 4: Orchestration / Main Entry Points / CLI runners
        tier_assignments: dict[str, int] = {}
        for mod_id, mod in modules.items():
            tier_assignments[mod_id] = self._classify_module_tier(mod_id, mod)

        # 3. Form learning units (either single module or SCC cycle cluster)
        visited_units: set[str] = set()
        units: list[dict[str, Any]] = []

        # Sort modules by:
        # a) Conceptual Tier (Foundation -> Storage -> Core -> API -> Entrypoint)
        # b) Out-degree (modules that depend on fewer things come first)
        # c) In-degree (modules depended on by more things come first)
        sorted_mod_ids = sorted(
            modules.keys(),
            key=lambda m: (
                tier_assignments.get(m, 2),
                len(modules[m].outgoing_modules),
                -len(modules[m].incoming_modules),
                m,
            ),
        )

        for mod_id in sorted_mod_ids:
            if mod_id in visited_units:
                continue

            if mod_id in scc_map:
                cycle_scc = scc_map[mod_id]
                cycle_list = sorted(list(cycle_scc))
                for m in cycle_list:
                    visited_units.add(m)
                
                # Minimum tier among cycle members
                min_tier = min(tier_assignments.get(m, 2) for m in cycle_list)
                units.append({
                    "is_cycle": True,
                    "modules": cycle_list,
                    "tier": min_tier,
                })
            else:
                visited_units.add(mod_id)
                units.append({
                    "is_cycle": False,
                    "modules": [mod_id],
                    "tier": tier_assignments.get(mod_id, 2),
                })

        # Sort units by tier, then by number of forward references
        units.sort(key=lambda u: (u["tier"], len(u["modules"])))

        # 4. Synthesize steps with progressive prerequisite tracking
        steps: list[OnboardingStep] = []
        concepts_mastered: list[str] = []
        total_loc = 0

        for idx, unit in enumerate(units, start=1):
            unit_mods = unit["modules"]
            is_cycle = unit["is_cycle"]
            
            # Identify primary component
            primary_comp_id = None
            primary_comp_name = None
            for m in unit_mods:
                for comp in self.arch_model.components.values():
                    if m in comp.modules:
                        primary_comp_id = comp.id
                        primary_comp_name = comp.name
                        break
                if primary_comp_id:
                    break

            # Collect key symbols
            key_symbols = []
            for m in unit_mods:
                node = self.repo_builder.nodes.get(m) if self.repo_builder else None
                if node:
                    total_loc += node.line_count
                if m in getattr(self.repo_builder, "parsed", {}):
                    p_mod = self.repo_builder.parsed[m]
                    for c in p_mod.classes[:2]:
                        key_symbols.append({"name": c.name, "type": "class", "module": m})
                    for f in p_mod.functions[:3]:
                        key_symbols.append({"name": f.name, "type": "function", "module": m})

            # Determine title & concept
            concept, title = self._determine_step_concept_and_title(unit_mods, unit["tier"], is_cycle)
            why_now = self._generate_why_now_explanation(unit_mods, unit["tier"], is_cycle, concepts_mastered)
            
            # Generate summaries for the 3 complexity levels
            b_sum, i_sum, a_sum = self._generate_multilevel_summaries(
                unit_mods, concept, is_cycle, key_symbols
            )

            # Determine what concepts this step unlocks for upcoming steps
            next_unlocks = self._determine_next_unlocks(unit["tier"])

            step = OnboardingStep(
                step_number=idx,
                title=title,
                concept=concept,
                target_modules=unit_mods,
                component_id=primary_comp_id,
                component_name=primary_comp_name,
                key_symbols=key_symbols[:6],
                why_now=why_now,
                prerequisites_covered=list(concepts_mastered),
                next_unlocks=next_unlocks,
                is_cycle_group=is_cycle,
                cycle_modules=unit_mods if is_cycle else [],
                beginner_summary=b_sum,
                intermediate_summary=i_sum,
                advanced_summary=a_sum,
            )
            steps.append(step)
            concepts_mastered.append(concept)

        # Estimate reading time (approx 150 LOC per 2 minutes + 1 minute concept reading per step)
        est_minutes = max(5, int((total_loc / 150) * 2 + len(steps) * 1.5))

        # Identify top entry point
        top_entry = None
        if self.arch_model.entry_points:
            top_entry = self.arch_model.entry_points[0].get("module")

        # Key core abstractions (classes with highest connectivity)
        abstractions = self._find_core_abstractions()

        return OnboardingPlan(
            total_steps=len(steps),
            steps=steps,
            estimated_read_time_minutes=est_minutes,
            entry_point_module=top_entry,
            core_abstractions=abstractions,
        )

    def _classify_module_tier(self, mod_id: str, mod: Module) -> int:
        """Classifies a module into a conceptual prerequisite tier (0 to 4)."""
        path_lower = mod_id.lower()
        role = self.arch_model.roles.get(mod_id, "MODULE")

        # Tier 0: Foundation / Types / Models / Enums / Constants
        if any(term in path_lower for term in ["model", "schema", "type", "constant", "enum", "util", "helper", "error", "exception"]):
            return 0
        if role == "LEAF" and len(mod.outgoing_modules) == 0:
            return 0

        # Tier 1: Storage / Persistence / Database / Adapters / Repositories
        if any(term in path_lower for term in ["db", "database", "repo", "store", "storage", "crud", "client", "adapter"]):
            return 1

        # Tier 4: Primary Entrypoints / CLI / Application runners
        if role == "ENTRY_CANDIDATE" or any(term in path_lower for term in ["main.py", "cli.py", "__main__.py", "app.py", "run.py", "server.py"]):
            return 4

        # Tier 3: API / Routes / Endpoints / Protocols / Auth
        if any(term in path_lower for term in ["api", "route", "router", "endpoint", "view", "auth", "session", "controller"]):
            return 3

        # Tier 2: Core Domain Logic / Services / Engines
        return 2

    def _determine_step_concept_and_title(
        self,
        modules: list[str],
        tier: int,
        is_cycle: bool,
    ) -> tuple[str, str]:
        """Generates clear, human-oriented title and concept descriptor."""
        first_mod = Path(modules[0]).stem.replace("_", " ").title()
        
        if is_cycle:
            concept = f"{first_mod} Cyclic State Loop"
            title = f"Interdependent State Loop ({len(modules)} Modules)"
            return concept, title

        if tier == 0:
            concept = f"{first_mod} Foundation & Data Models"
            title = f"Understanding Foundation: {Path(modules[0]).name}"
        elif tier == 1:
            concept = f"{first_mod} Persistence & Storage"
            title = f"Understanding Storage: {Path(modules[0]).name}"
        elif tier == 2:
            concept = f"{first_mod} Core Business Logic"
            title = f"Understanding Domain Logic: {Path(modules[0]).name}"
        elif tier == 3:
            concept = f"{first_mod} Interface & Routing"
            title = f"Understanding Interface Layer: {Path(modules[0]).name}"
        else:
            concept = f"{first_mod} Orchestration & Entrypoint"
            title = f"Application Orchestration: {Path(modules[0]).name}"

        return concept, title

    def _generate_why_now_explanation(
        self,
        modules: list[str],
        tier: int,
        is_cycle: bool,
        prerequisites: list[str],
    ) -> str:
        """Explains why this step is sequenced at this exact location."""
        mod_names = ", ".join(f"`{Path(m).name}`" for m in modules)
        
        if is_cycle:
            return (
                f"These modules ({mod_names}) form a circular dependency loop. "
                "Instead of reading them in isolation, understanding them together as a single "
                "coordinated unit prevents confusion about chicken-and-egg dependencies."
            )

        if tier == 0:
            return (
                f"{mod_names} contains foundational data types and utility functions with minimal "
                "outward dependencies. Reading this first establishes the vocabulary and structures "
                "used throughout the rest of the codebase."
            )
        elif tier == 1:
            return (
                f"{mod_names} manages persistent storage and data access. "
                "Higher-level domain services depend heavily on these persistence abstractions."
            )
        elif tier == 2:
            return (
                f"{mod_names} coordinates core business logic. Now that foundational data structures "
                "are familiar, you can see how domain operations are executed."
            )
        elif tier == 3:
            return (
                f"{mod_names} exposes public interfaces, handles protocols, and routes requests. "
                "It converts external incoming events into internal domain actions."
            )
        else:
            return (
                f"{mod_names} acts as the primary orchestrator and entry point. Having mastered "
                "the underlying domain, storage, and interfaces, you can now appreciate the complete "
                "application bootstrap and runtime lifecycle."
            )

    def _generate_multilevel_summaries(
        self,
        modules: list[str],
        concept: str,
        is_cycle: bool,
        symbols: list[dict[str, str]],
    ) -> tuple[str, str, str]:
        """Generates progressive explanations tailored for Beginner, Intermediate, and Advanced readers."""
        mod_names = ", ".join(f"`{Path(m).name}`" for m in modules)
        sym_names = ", ".join(f"`{s['name']}`" for s in symbols[:3]) if symbols else "primary constructs"

        # 1. Beginner: Mental models, analogies, plain language
        beginner = (
            f"Think of this step ({concept}) as establishing the basic building blocks ({mod_names}). "
            f"You will learn about {sym_names} without worrying about internal implementation details."
        )

        # 2. Intermediate: Architecture, responsibilities, input/output flow
        intermediate = (
            f"Examines architectural responsibilities of {mod_names}. Focus on how {sym_names} "
            "manages data flow, encapsulates side effects, and provides APIs consumed by upstream layers."
        )

        # 3. Advanced: AST, coupling metrics, invariants, cycles, blast radius
        if is_cycle:
            advanced = (
                f"Tightly-coupled strongly connected component across {mod_names}. Inspect shared state, "
                "circular import mitigation strategies, and evaluate opportunities for dependency inversion."
            )
        else:
            advanced = (
                f"Detailed AST inspection of {mod_names}. Traces symbol declarations ({sym_names}), "
                "in-degree/out-degree ratios, call hierarchies, and blast radius across dependent modules."
            )

        return beginner, intermediate, advanced

    def _determine_next_unlocks(self, tier: int) -> list[str]:
        """Predicts which subsequent concepts become readable once this step is mastered."""
        if tier == 0:
            return ["Persistent Storage", "Domain Services", "Request Context"]
        elif tier == 1:
            return ["Business Logic", "Service Handlers", "Authentication Operations"]
        elif tier == 2:
            return ["HTTP Routing", "API Controllers", "Application Middleware"]
        elif tier == 3:
            return ["Application Lifecycle", "CLI Runner", "Server Bootstrap"]
        else:
            return ["Full System Mastery", "Extension Points", "Refactoring Opportunities"]

    def _find_core_abstractions(self) -> list[str]:
        """Identifies key class abstractions that form the spine of the repository."""
        abstractions = []
        if not self.repo_builder or not hasattr(self.repo_builder, "parsed"):
            return abstractions

        # Rank classes by reference counts
        for mod_id, p_mod in self.repo_builder.parsed.items():
            for c in p_mod.classes:
                abstractions.append(f"{c.name} ({Path(mod_id).name})")
        return abstractions[:8]
