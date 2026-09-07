"""
DeepWiki Architecture Analyzer Pipeline
=======================================

Orchestrates repository architecture reconstruction completely identical to DeepWiki:
1. Builds weighted directed module graph from resolved symbol relationships.
2. Runs DeepWiki engine to determine architecture structure (sections, pages, source files)
   using user's chosen AI provider (Gemini, OpenAI, OpenRouter, Ollama, Anthropic) or deterministic fallback.
3. Generates source-grounded DeepWiki technical pages with interactive citations.
4. Maps architectural subsystems and components directly from DeepWiki structure and code relationships.
5. Assembles component dependency graph, entry candidates, architectural flows, and ArchitectureModel.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import networkx as nx

from architecture.deepwiki_engine import DeepWikiEngine
from architecture.models import (
    ArchitectureConfig,
    ArchitectureFlow,
    ArchitectureModel,
    Component,
    Module,
    WikiCacheData,
)
from architecture.module_graph import build_module_graph, normalize_module_path
from architecture.providers import AIProviderConfig

logger = logging.getLogger("karuvi.architecture")


class ArchitectureAnalyzer:
    """
    Analyzes a Python codebase to reconstruct its architecture using DeepWiki.
    """

    def __init__(
        self,
        repository_root: Path | str,
        config: ArchitectureConfig | None = None,
    ):
        self.repository_root = Path(repository_root).resolve()
        self.config = config or ArchitectureConfig()

    def analyze(
        self,
        symbol_graph_or_builder: nx.DiGraph | Any = None,
    ) -> ArchitectureModel:
        """
        Executes the DeepWiki architecture reconstruction pipeline.
        """
        repo_root = self.repository_root
        cfg = self.config

        # 1. Obtain symbol graph / repo builder
        if symbol_graph_or_builder is None:
            from cli import analyze_repository
            _, _, repo_builder = analyze_repository(repo_root, verbose=False)
            symbol_graph_or_builder = repo_builder

        logger.info("[architecture] Building module dependency graph...")
        module_graph = build_module_graph(symbol_graph_or_builder, repo_root)

        # 2. Run DeepWiki Architecture Engine
        provider_cfg = AIProviderConfig(
            provider=cfg.ai_provider,
            model=cfg.ai_model,
            api_key=cfg.api_key,
            base_url=cfg.base_url,
        )
        engine = DeepWikiEngine(repo_root, provider_config=provider_cfg)

        logger.info(f"[architecture] Running DeepWiki architecture engine ({provider_cfg.provider})...")
        wiki_cache = engine.generate_wiki(
            use_cache=cfg.use_cache,
            comprehensive=cfg.comprehensive,
            language=cfg.language,
        )

        # 3. Construct Components from DeepWiki Subsystems & Module Relationships
        components: dict[str, Component] = {}
        module_to_comp: dict[str, str] = {}

        # Primary: Group modules by DeepWiki pages / sections
        for page in wiki_cache.wiki_structure.pages:
            c_id = page.id
            c_name = page.title
            comp_modules = [m for m in page.file_paths if m in module_graph]
            if comp_modules:
                components[c_id] = Component(
                    id=c_id,
                    name=c_name,
                    modules=comp_modules,
                    discovery_methods=["deepwiki_structure", "source_grounding"],
                    confidence=0.95 if page.importance == "high" else 0.85,
                    metadata={"importance": page.importance, "section": page.parent_section},
                )
                for m in comp_modules:
                    module_to_comp[m] = c_id

        # Fallback: assign any unassigned modules by directory / package
        unassigned = [m for m in module_graph.nodes if m not in module_to_comp]
        if unassigned:
            for m in unassigned:
                parts = m.split("/")
                dir_group = parts[0] if len(parts) > 1 else "root"
                group_id = f"subsystem-{dir_group}"
                if group_id not in components:
                    components[group_id] = Component(
                        id=group_id,
                        name=f"{dir_group.title()} Subsystem",
                        modules=[],
                        discovery_methods=["directory_topology"],
                        confidence=0.80,
                        metadata={"importance": "medium"},
                    )
                components[group_id].modules.append(m)
                module_to_comp[m] = group_id

        # 4. Build Component Graph from Module Graph
        component_graph = nx.DiGraph()
        for c in components.values():
            component_graph.add_node(c.id, name=c.name, modules=c.modules)

        for u, v, d in module_graph.edges(data=True):
            src_c = module_to_comp.get(u)
            tgt_c = module_to_comp.get(v)
            if src_c and tgt_c and src_c != tgt_c:
                if component_graph.has_edge(src_c, tgt_c):
                    component_graph[src_c][tgt_c]["weight"] += d.get("weight", 1)
                else:
                    component_graph.add_edge(src_c, tgt_c, weight=d.get("weight", 1))

        # 5. Detect Roles & Metrics
        cycles = list(nx.simple_cycles(module_graph))
        cycle_nodes = set()
        for c in cycles:
            cycle_nodes.update(c)

        roles: dict[str, str] = {}
        for n in module_graph.nodes:
            if n in cycle_nodes:
                roles[n] = "CYCLE_MEMBER"
                continue
            in_deg = module_graph.in_degree(n)
            out_deg = module_graph.out_degree(n)
            if in_deg == 0 and out_deg > 0:
                roles[n] = "ENTRY_CANDIDATE"
            elif in_deg > 3 and out_deg > 3:
                roles[n] = "HUB"
            elif out_deg == 0 and in_deg > 0:
                roles[n] = "LEAF"
            elif in_deg > 0 and out_deg > 0:
                roles[n] = "BRIDGE"
            else:
                roles[n] = "MODULE"

        # 6. Entry Points
        entry_points = []
        for n, r in roles.items():
            if r == "ENTRY_CANDIDATE":
                desc_mods = len(nx.descendants(module_graph, n)) if module_graph.has_node(n) else 0
                reachable_comps = set(module_to_comp.get(m) for m in nx.descendants(module_graph, n)) if module_graph.has_node(n) else set()
                reachable_comps.discard(None)
                entry_points.append({
                    "id": n,
                    "module": n,
                    "path": n,
                    "role": r,
                    "entry_score": 1.0 + (desc_mods * 0.1),
                    "component": module_to_comp.get(n, "core"),
                    "evidence": {
                        "reachable_modules": desc_mods,
                        "reachable_components": len(reachable_comps),
                    },
                })
        entry_points.sort(key=lambda x: x.get("entry_score", 0), reverse=True)
        if not entry_points and module_graph.nodes:
            sorted_by_flow = sorted(
                module_graph.nodes,
                key=lambda x: (module_graph.in_degree(x), -module_graph.out_degree(x)),
            )
            top_node = sorted_by_flow[0]
            desc_mods = len(nx.descendants(module_graph, top_node)) if module_graph.has_node(top_node) else 0
            reachable_comps = set(module_to_comp.get(m) for m in nx.descendants(module_graph, top_node)) if module_graph.has_node(top_node) else set()
            reachable_comps.discard(None)
            entry_points.append({
                "id": top_node,
                "module": top_node,
                "path": top_node,
                "role": roles.get(top_node, "MODULE"),
                "entry_score": 0.5 + (desc_mods * 0.1),
                "component": module_to_comp.get(top_node, "core"),
                "evidence": {
                    "reachable_modules": desc_mods,
                    "reachable_components": len(reachable_comps),
                },
            })

        # 7. High-level flows across components
        flows: list[ArchitectureFlow] = []
        for u, v, d in component_graph.edges(data=True):
            flows.append(ArchitectureFlow(
                source=u,
                target=v,
                path=[u, v],
                evidence={"weight": d.get("weight", 1)},
            ))

        # 8. Module dataclass objects
        modules_dict: dict[str, Module] = {}
        for node in module_graph.nodes:
            nd = module_graph.nodes[node]
            modules_dict[node] = Module(
                id=node,
                path=nd.get("path", node),
                symbols=nd.get("symbols", []),
                symbol_count=nd.get("symbol_count", 0),
                incoming_modules=nd.get("incoming_modules", []),
                outgoing_modules=nd.get("outgoing_modules", []),
                incoming_weight=nd.get("incoming_weight", 0),
                outgoing_weight=nd.get("outgoing_weight", 0),
                metadata={
                    "component": module_to_comp.get(node, "core"),
                    "role": roles.get(node, "MODULE"),
                    "internal_relationship_count": nd.get("internal_relationship_count", 0),
                },
            )

        logger.info("[architecture] DeepWiki architecture analysis complete.")

        return ArchitectureModel(
            repository_root=str(repo_root),
            modules=modules_dict,
            components=components,
            module_graph=module_graph,
            component_graph=component_graph,
            entry_points=entry_points,
            roles=roles,
            flows=flows,
            wiki_structure=wiki_cache.wiki_structure,
            wiki_pages=wiki_cache.generated_pages,
            wiki_cache=wiki_cache,
            metadata={
                "provider": wiki_cache.provider,
                "model": wiki_cache.model,
                "pages_count": len(wiki_cache.generated_pages),
            },
        )
