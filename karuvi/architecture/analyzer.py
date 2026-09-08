"""
Main Architecture Analyzer Pipeline
===================================

Orchestrates the complete 15-step deterministic architecture reconstruction pipeline:
Consumes resolved symbol relationships -> weighted module graph -> boundaries + communities
-> components -> component graph -> metrics & roles -> entry points -> flows -> ArchitectureModel.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import networkx as nx

from .boundaries import detect_boundaries
from .communities import detect_communities
from .component_graph import build_component_graph
from .components import reconstruct_components
from .entrypoints import detect_entry_points
from .flows import detect_flows
from .metrics import calculate_metrics
from .models import (
    ArchitectureConfig,
    ArchitectureModel,
    Component,
    Module,
)
from .module_graph import build_module_graph, normalize_module_path
from .roles import detect_roles

logger = logging.getLogger("karuvi.architecture")


class ArchitectureAnalyzer:
    """
    Analyzes a Python codebase to reconstruct its structural and topological architecture.
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
        Executes the full architecture reconstruction pipeline.

        If symbol_graph_or_builder is None, runs Karuvi's existing repository parser.
        """
        repo_root = self.repository_root
        cfg = self.config

        # 1. Obtain input if not provided
        if symbol_graph_or_builder is None:
            from ..cli import analyze_repository
            _, _, repo_builder = analyze_repository(repo_root, verbose=False)
            symbol_graph_or_builder = repo_builder

        logger.info("[architecture] Building module graph...")
        # 2. Build weighted directed module graph
        module_graph = build_module_graph(symbol_graph_or_builder, repo_root)
        logger.info(f"[architecture] {module_graph.number_of_nodes()} modules discovered.")
        logger.info(f"[architecture] {module_graph.number_of_edges()} inter-module relationships discovered.")

        # 3. Detect structural boundaries
        logger.info("[architecture] Detecting structural boundaries...")
        boundaries = detect_boundaries(module_graph, repo_root, cfg)

        # 4. Detect graph communities
        logger.info("[architecture] Running community detection...")
        communities = detect_communities(module_graph, cfg)

        # 5. Reconstruct components & calculate confidence
        logger.info("[architecture] Building component model...")
        components = reconstruct_components(module_graph, boundaries, communities, cfg)
        logger.info(f"[architecture] {len(components)} candidate components created.")

        # 6. Build component dependency graph
        component_graph = build_component_graph(module_graph, components)

        # 7. Calculate graph metrics
        logger.info("[architecture] Calculating graph metrics...")
        metrics = calculate_metrics(module_graph)

        # 8. Detect structural roles
        roles = detect_roles(module_graph, metrics)

        # 9. Detect structural entry points
        logger.info("[architecture] Detecting structural entry points...")
        entry_points = detect_entry_points(module_graph, metrics, components)
        logger.info(f"[architecture] {len(entry_points)} entry candidates identified.")

        # 10. Detect architectural flows
        flows = detect_flows(component_graph, entry_points, components, max_flows=cfg.max_flows)

        # 11. Populate Module dataclass dictionary
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
                    "internal_relationship_count": nd.get("internal_relationship_count", 0),
                    "boundary": boundaries.get(node, "root"),
                    "community": communities.get(node, 0),
                    "role": roles.get(node, "MODULE"),
                    "metrics": metrics.get(node, {}),
                },
            )

        logger.info("[architecture] Architecture analysis complete.")

        return ArchitectureModel(
            repository_root=str(repo_root),
            modules=modules_dict,
            components=components,
            module_graph=module_graph,
            component_graph=component_graph,
            entry_points=entry_points,
            roles=roles,
            flows=flows,
            metadata={
                "boundary_count": len(set(boundaries.values())),
                "community_count": len(set(communities.values())) if communities else 0,
            },
        )
