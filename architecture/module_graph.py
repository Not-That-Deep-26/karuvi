"""
Module Graph Construction and Path Normalization
================================================

Constructs a weighted directed module graph from low-level symbol relationships.
Every node represents a source module, and edges aggregate low-level symbol
references and imports, preserving full traceability to the underlying evidence.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import networkx as nx

from architecture.exceptions import GraphValidationError


def normalize_module_path(file_path: str | Path, repository_root: Path | str) -> str:
    """
    Normalizes a file path relative to the repository root.
    
    Ensures consistent POSIX formatting (forward slashes), strips redundant prefixes,
    and returns a deterministic relative path.
    """
    clean_str = str(file_path).replace("\\", "/")
    repo_root = Path(repository_root).resolve()
    path_obj = Path(clean_str)

    # Resolve absolute paths or relative to repository root
    if path_obj.is_absolute():
        try:
            rel = path_obj.resolve().relative_to(repo_root)
        except ValueError:
            # Not a subpath of repo_root (e.g. external or fixture)
            rel = path_obj
    else:
        # Check if already relative or prepended with repo_root name
        full = (repo_root / path_obj).resolve()
        try:
            rel = full.relative_to(repo_root)
        except ValueError:
            rel = path_obj

    # Convert to POSIX representation and clean up
    normalized = rel.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def build_symbol_graph_from_builder(
    repo_builder: Any, repository_root: Path | str
) -> nx.DiGraph:
    """
    Constructs a NetworkX DiGraph representing resolved symbols and relationships
    from Karuvi's RepoGraphBuilder, parsed_modules, and global index.
    """
    G = nx.DiGraph()
    repo_root = Path(repository_root).resolve()

    parsed = getattr(repo_builder, "parsed", {})

    # 1. Register symbol nodes for each internal module
    for rel_key, mod in parsed.items():
        norm_mod_path = normalize_module_path(rel_key, repo_root)
        mod_node_id = f"mod:{norm_mod_path}"
        G.add_node(
            mod_node_id,
            id=mod_node_id,
            name=getattr(mod, "name", "") or Path(norm_mod_path).stem,
            file=norm_mod_path,
            kind="module",
            uuid=None,
            line=1,
        )

        # Functions
        for fn in getattr(mod, "functions", []):
            fn_id = fn.uuid or f"{norm_mod_path}:{fn.name}"
            G.add_node(
                fn_id,
                id=fn_id,
                name=fn.name,
                file=norm_mod_path,
                kind="function",
                signature=getattr(fn, "signature", ""),
                uuid=fn.uuid,
                line=None,
            )

        # Classes
        for cls in getattr(mod, "classes", []):
            cls_id = cls.uuid or f"{norm_mod_path}:{cls.name}"
            G.add_node(
                cls_id,
                id=cls_id,
                name=cls.name,
                file=norm_mod_path,
                kind="class",
                uuid=cls.uuid,
                line=None,
            )

        # Variables
        for var_name, var in getattr(mod, "variables", {}).items():
            if var.uuid and not var.is_reference:
                var_id = var.uuid
                decl_line = var.decl_reference[1] if var.decl_reference else None
                G.add_node(
                    var_id,
                    id=var_id,
                    name=var_name,
                    file=norm_mod_path,
                    kind="variable",
                    uuid=var.uuid,
                    line=decl_line,
                )

    # 2. Add edges from cross references
    cross_refs = getattr(repo_builder, "cross_references", [])
    for xref in cross_refs:
        src_file = normalize_module_path(xref.get("source_file", ""), repo_root)
        tgt_file = normalize_module_path(xref.get("target_file", ""), repo_root)
        sym_name = xref.get("symbol", "")
        uuid = xref.get("uuid")

        src_node = f"mod:{src_file}"
        tgt_node = uuid if uuid and uuid in G else f"mod:{tgt_file}"

        G.add_edge(
            src_node,
            tgt_node,
            type="CALL" if xref.get("scope") in ("function", "call") else "REFERENCE",
            symbol=sym_name,
            use_line=xref.get("use_line"),
            decl_line=xref.get("decl_line"),
            source_file=src_file,
            target_file=tgt_file,
        )

    # 3. Add edges from imports in repo_builder
    edges = getattr(repo_builder, "edges", [])
    for edge in edges:
        if edge.type == "import" and not edge.target.startswith("ext:"):
            src_file = normalize_module_path(edge.source, repo_root)
            tgt_file = normalize_module_path(edge.target, repo_root)
            src_node = f"mod:{src_file}"
            tgt_node = f"mod:{tgt_file}"
            if src_file != tgt_file:
                G.add_edge(
                    src_node,
                    tgt_node,
                    type="IMPORT",
                    symbol=getattr(edge, "symbol", None),
                    details=getattr(edge, "details", ""),
                    source_file=src_file,
                    target_file=tgt_file,
                )

    return G


def build_module_graph(
    symbol_graph: nx.DiGraph | Any,
    repository_root: Path | str,
) -> nx.DiGraph:
    """
    Transforms a symbol graph (or RepoGraphBuilder) into a weighted directed module graph.

    Aggregates multi-symbol relationships into weighted edges, tracks intra-module
    relationships in metadata, and computes module degrees and weights.
    """
    repo_root = Path(repository_root).resolve()

    # If passed a RepoGraphBuilder directly, convert to symbol graph first
    if not isinstance(symbol_graph, nx.DiGraph):
        if hasattr(symbol_graph, "parsed") or hasattr(symbol_graph, "edges"):
            symbol_graph = build_symbol_graph_from_builder(symbol_graph, repo_root)
        else:
            raise GraphValidationError(
                f"Unsupported input type for build_module_graph: {type(symbol_graph)}"
            )

    module_graph = nx.DiGraph()

    # 1. Collect all modules and their associated symbols
    module_symbols: dict[str, list[str]] = {}

    for node_id, node_data in symbol_graph.nodes(data=True):
        file_path = node_data.get("file")
        if not file_path:
            continue
        norm_path = normalize_module_path(file_path, repo_root)
        if norm_path not in module_symbols:
            module_symbols[norm_path] = []
        if node_data.get("kind") != "module":
            module_symbols[norm_path].append(str(node_id))

    # Also register nodes that may only exist as module nodes
    for node_id, node_data in symbol_graph.nodes(data=True):
        file_path = node_data.get("file")
        if file_path:
            norm_path = normalize_module_path(file_path, repo_root)
            if norm_path not in module_graph:
                module_graph.add_node(
                    norm_path,
                    id=norm_path,
                    path=norm_path,
                    name=Path(norm_path).stem,
                    symbols=module_symbols.get(norm_path, []),
                    symbol_count=len(module_symbols.get(norm_path, [])),
                    internal_relationship_count=0,
                    incoming_weight=0,
                    outgoing_weight=0,
                    in_degree=0,
                    out_degree=0,
                    incoming_modules=[],
                    outgoing_modules=[],
                    metadata={},
                )

    # 2. Process all symbol graph edges and aggregate into module edges
    for u, v, edge_data in symbol_graph.edges(data=True):
        u_data = symbol_graph.nodes.get(u, {})
        v_data = symbol_graph.nodes.get(v, {})

        src_file = edge_data.get("source_file") or u_data.get("file")
        tgt_file = edge_data.get("target_file") or v_data.get("file")

        if not src_file or not tgt_file:
            continue

        src_mod = normalize_module_path(src_file, repo_root)
        tgt_mod = normalize_module_path(tgt_file, repo_root)

        # Ensure both module nodes exist
        for m in (src_mod, tgt_mod):
            if m not in module_graph:
                module_graph.add_node(
                    m,
                    id=m,
                    path=m,
                    name=Path(m).stem,
                    symbols=module_symbols.get(m, []),
                    symbol_count=len(module_symbols.get(m, [])),
                    internal_relationship_count=0,
                    incoming_weight=0,
                    outgoing_weight=0,
                    in_degree=0,
                    out_degree=0,
                    incoming_modules=[],
                    outgoing_modules=[],
                    metadata={},
                )

        rel_type = edge_data.get("type", "REFERENCE").upper()
        symbol_evidence = {
            "source_symbol": str(u),
            "target_symbol": str(v),
            "type": rel_type,
            "symbol": edge_data.get("symbol"),
            "use_line": edge_data.get("use_line"),
            "decl_line": edge_data.get("decl_line"),
        }

        if src_mod == tgt_mod:
            # Intra-module relationship: track internal connectivity metadata, no self-edge
            module_graph.nodes[src_mod]["internal_relationship_count"] += 1
        else:
            # Inter-module relationship: aggregate into weighted edge
            if module_graph.has_edge(src_mod, tgt_mod):
                edge_meta = module_graph[src_mod][tgt_mod]
                edge_meta["weight"] += 1
                edge_meta["relationship_types"][rel_type] = (
                    edge_meta["relationship_types"].get(rel_type, 0) + 1
                )
                # Keep up to 50 symbol references to avoid memory bloat
                if len(edge_meta["symbol_edges"]) < 50:
                    edge_meta["symbol_edges"].append(symbol_evidence)
            else:
                module_graph.add_edge(
                    src_mod,
                    tgt_mod,
                    weight=1,
                    relationship_types={rel_type: 1},
                    symbol_edges=[symbol_evidence],
                )

    # 3. Calculate module metadata
    for node in module_graph.nodes:
        in_edges = list(module_graph.in_edges(node, data=True))
        out_edges = list(module_graph.out_edges(node, data=True))

        in_weight = sum(d.get("weight", 1) for _, _, d in in_edges)
        out_weight = sum(d.get("weight", 1) for _, _, d in out_edges)

        in_mods = sorted([src for src, _, _ in in_edges])
        out_mods = sorted([tgt for _, tgt, _ in out_edges])

        node_dict = module_graph.nodes[node]
        node_dict["incoming_weight"] = in_weight
        node_dict["outgoing_weight"] = out_weight
        node_dict["in_degree"] = len(in_mods)
        node_dict["out_degree"] = len(out_mods)
        node_dict["incoming_modules"] = in_mods
        node_dict["outgoing_modules"] = out_mods

    return module_graph
