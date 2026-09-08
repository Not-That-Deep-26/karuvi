"""
Component Reconstruction and Confidence Scoring
===============================================

Synthesizes structural directory boundaries and graph topological communities
into candidate architectural components with deterministic naming and evidence-backed
confidence scoring.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

from .models import ArchitectureConfig, Component


def calculate_structural_cohesion(modules: list[str], module_to_boundary: dict[str, str]) -> float:
    """Calculates the proportion of modules belonging to the dominant structural boundary."""
    if not modules:
        return 0.0
    boundary_counts: dict[str, int] = defaultdict(int)
    for m in modules:
        boundary_counts[module_to_boundary.get(m, "root")] += 1
    max_count = max(boundary_counts.values())
    return max_count / len(modules)


def calculate_graph_cohesion(
    modules: list[str],
    module_graph: nx.DiGraph,
) -> tuple[float, int, int]:
    """
    Calculates internal edge weight / (internal + external edge weight) for the component.
    Returns:
        (cohesion_ratio, internal_weight, external_weight)
    """
    mod_set = set(modules)
    internal_weight = 0
    external_weight = 0

    for m in modules:
        if m not in module_graph:
            continue
        # Outgoing edges
        for _, target, data in module_graph.out_edges(m, data=True):
            w = data.get("weight", 1)
            if target in mod_set:
                internal_weight += w
            else:
                external_weight += w
        # Incoming edges from outside the component
        for src, _, data in module_graph.in_edges(m, data=True):
            w = data.get("weight", 1)
            if src not in mod_set:
                external_weight += w

    total_weight = internal_weight + external_weight
    if total_weight == 0:
        # No edges: no structural evidence either way — score as neutral,
        # not maximally certain (a lone file is not proof of strong cohesion).
        return 0.5, 0, 0

    ratio = internal_weight / total_weight
    return ratio, internal_weight, external_weight


def calculate_agreement(
    modules: list[str],
    module_to_boundary: dict[str, str],
    module_to_community: dict[str, int],
) -> float:
    """
    Measures the degree of agreement between structural boundary and graph community
    among modules in this component.
    """
    if not modules:
        return 0.0
    if len(modules) == 1:
        return 1.0

    boundaries = {module_to_boundary.get(m) for m in modules}
    communities = {module_to_community.get(m) for m in modules}

    # If all modules share exactly one boundary and one community: complete agreement (1.0)
    if len(boundaries) == 1 and len(communities) == 1:
        return 1.0
    # If either boundary or community is unified: partial agreement (0.5)
    elif len(boundaries) == 1 or len(communities) == 1:
        return 0.5
    else:
        return 0.2


def _derive_component_label(
    modules: list[str],
    community_id: int | None,
    used_labels: set[str],
) -> str:
    """
    Derives a deterministic, human-readable distinguishing label for a component
    whose name collides with other components (e.g. folder-splitting can produce
    several components all named after the same boundary directory).

    Priority: first N module stems -> first N module stems (wider) -> a unique
    community fallback. Always returns a label unique within ``used_labels``.
    """
    stems = [Path(m).stem for m in modules]
    candidates = []
    if stems:
        candidates.append(", ".join(stems[:3]))
        candidates.append(", ".join(stems[:8]))
    if community_id is not None:
        candidates.append(f"community {community_id}")
    for cand in candidates:
        if cand and cand not in used_labels:
            return cand
    base = "community" if community_id is None else f"community {community_id}"
    counter = 1
    while f"{base} ({counter})" in used_labels:
        counter += 1
    return f"{base} ({counter})"


def derive_component_name(
    modules: list[str],
    module_to_boundary: dict[str, str],
    community_id: int | None = None,
) -> str:
    """
    Deterministically names a component using priority:
    1. Shared meaningful boundary name
    2. Combined distinct boundary names
    3. Shared path prefix
    4. community-N
    """
    boundaries = sorted(list({module_to_boundary.get(m, "root") for m in modules}))

    if len(boundaries) == 1 and boundaries[0] != "root":
        return boundaries[0]

    # Multiple boundaries: combine if 2-3 boundaries (e.g. auth-sessions)
    meaningful = [b for b in boundaries if b != "root"]
    if 1 <= len(meaningful) <= 2:
        return "-".join(meaningful)

    # Check shared directory prefix across module paths
    if modules:
        parts_list = [Path(m).parent.parts for m in modules]
        common = []
        for elems in zip(*parts_list):
            if len(set(elems)) == 1 and elems[0] not in (".", "", "src", "lib"):
                common.append(elems[0])
            else:
                break
        if common:
            return "/".join(common)

    if community_id is not None:
        return f"community-{community_id}"

    return "core" if "root" in boundaries else "-".join(boundaries[:2])


def reconstruct_components(
    module_graph: nx.DiGraph,
    module_to_boundary: dict[str, str],
    module_to_community: dict[str, int],
    config: ArchitectureConfig | None = None,
) -> dict[str, Component]:
    """
    Reconstructs architectural components by synthesizing boundary and community evidence.
    
    Supports:
    - Boundary + Community agreement
    - Folder splitting (when community diverges within folder)
    - Cross-folder merging (when strong community bridges folders)
    """
    cfg = config or ArchitectureConfig()
    modules = list(module_graph.nodes)

    if not modules:
        return {}

    # 1. Group modules by (boundary, community) pair
    clusters: dict[tuple[str, int], list[str]] = defaultdict(list)
    for m in modules:
        b = module_to_boundary.get(m, "root")
        c = module_to_community.get(m, 0)
        clusters[(b, c)].append(m)

    # 2. Check for potential cross-folder merges where a single community strongly dominates
    #    multiple boundaries
    community_to_boundaries: dict[int, set[str]] = defaultdict(set)
    for (b, c) in clusters:
        community_to_boundaries[c].add(b)

    # Initial component groupings: group_key -> list of modules
    component_groups: dict[str, list[str]] = {}
    discovery_methods: dict[str, list[str]] = {}

    # Determine if any community should merge distinct boundaries:
    # Merge if the community has strong internal connectivity across the boundaries
    merged_communities: set[int] = set()
    for c, b_set in community_to_boundaries.items():
        if len(b_set) > 1 and len(b_set) <= 3:
            # Check edge density between these boundaries within community c
            comm_modules = [m for m in modules if module_to_community.get(m) == c]
            if len(comm_modules) >= 2:
                # Calculate internal edges between differing boundaries
                cross_edges = 0
                for u in comm_modules:
                    for v in comm_modules:
                        if u != v and module_to_boundary.get(u) != module_to_boundary.get(v):
                            if module_graph.has_edge(u, v):
                                cross_edges += 1
                if cross_edges >= 1:
                    merged_communities.add(c)
                    group_id = f"merged-comm-{c}"
                    component_groups[group_id] = comm_modules
                    discovery_methods[group_id] = ["GRAPH_COMMUNITY"]

    # For modules not part of a merged community, group by (boundary, community)
    for (b, c), cluster_mods in clusters.items():
        if c in merged_communities:
            continue
        # Count how many communities this boundary was split into
        comm_count_for_boundary = len([
            other_c for (other_b, other_c) in clusters if other_b == b
        ])

        if comm_count_for_boundary > 1:
            # Folder splitting
            group_id = f"{b}-{c}"
            method = "GRAPH_COMMUNITY"
        elif len(cluster_mods) == 1:
            group_id = b
            method = "SINGLETON" if len(modules) == 1 else "STRUCTURAL_BOUNDARY"
        else:
            group_id = b
            method = "BOUNDARY_AND_COMMUNITY"

        if group_id not in component_groups:
            component_groups[group_id] = []
            discovery_methods[group_id] = []
        component_groups[group_id].extend(cluster_mods)
        if method not in discovery_methods[group_id]:
            discovery_methods[group_id].append(method)

    # 3. Create Component dataclass instances and compute confidence
    components: dict[str, Component] = {}

    for group_id, comp_mods in sorted(component_groups.items()):
        # Deterministic sorting
        comp_mods = sorted(comp_mods)
        first_comm = module_to_community.get(comp_mods[0], 0) if comp_mods else 0
        name = derive_component_name(comp_mods, module_to_boundary, first_comm)
        
        # Clean up ID to be URL-safe / deterministic
        comp_id = name.lower().replace("/", "_").replace(" ", "_").replace("-", "_")

        # If duplicate ID, disambiguate
        base_id = comp_id
        counter = 1
        while comp_id in components:
            comp_id = f"{base_id}_{counter}"
            counter += 1

        # Calculate confidence factors
        struct_cohesion = calculate_structural_cohesion(comp_mods, module_to_boundary)
        graph_cohesion, int_w, ext_w = calculate_graph_cohesion(comp_mods, module_graph)
        agreement = calculate_agreement(comp_mods, module_to_boundary, module_to_community)

        confidence = (
            cfg.cohesion_structural_weight * struct_cohesion
            + cfg.cohesion_graph_weight * graph_cohesion
            + cfg.cohesion_agreement_weight * agreement
        )
        confidence = max(0.0, min(1.0, confidence))

        methods = discovery_methods.get(group_id, ["STRUCTURAL_BOUNDARY"])

        components[comp_id] = Component(
            id=comp_id,
            name=name,
            modules=comp_mods,
            discovery_methods=methods,
            confidence=confidence,
            metadata={
                "internal_weight": int_w,
                "external_weight": ext_w,
                "structural_cohesion": round(struct_cohesion, 3),
                "graph_cohesion": round(graph_cohesion, 3),
                "agreement": round(agreement, 3),
                "module_count": len(comp_mods),
                "community_id": first_comm,
            },
        )

    # Post-pass: when several components share the same name (folder splitting),
    # stamp each with a human-readable distinguishing label so the UI can tell
    # them apart without exposing raw internal IDs.
    name_groups: dict[str, list[str]] = defaultdict(list)
    for comp_id, comp in components.items():
        name_groups[comp.name].append(comp_id)

    for _name, comp_ids in name_groups.items():
        if len(comp_ids) <= 1:
            continue
        used_labels: set[str] = set()
        for comp_id in comp_ids:
            comp = components[comp_id]
            community_id = comp.metadata.get("community_id")
            label = _derive_component_label(comp.modules, community_id, used_labels)
            used_labels.add(label)
            comp.metadata["distinguishing_label"] = label

    return components
