"""
JSON Serialization for Architecture Models
==========================================

Serializes the in-memory ArchitectureModel and its underlying NetworkX graphs
into a clean, deterministic, JSON-compliant structure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from architecture.models import ArchitectureModel


def serialize_architecture_model(model: ArchitectureModel) -> dict[str, Any]:
    """
    Serializes an ArchitectureModel into a JSON-compliant dictionary.
    
    Transforms NetworkX graphs into explicit nodes and edges lists.
    """
    # Serialize components
    comps_serialized = [comp.to_dict() for comp in model.components.values()]

    # Serialize module graph
    module_graph_data: dict[str, Any] = {"nodes": [], "edges": []}
    total_symbols = 0
    if model.module_graph is not None:
        for node, data in model.module_graph.nodes(data=True):
            sym_count = data.get("symbol_count", 0)
            total_symbols += sym_count
            module_graph_data["nodes"].append({
                "id": str(node),
                "path": data.get("path", str(node)),
                "name": data.get("name", ""),
                "symbol_count": sym_count,
                "internal_relationship_count": data.get("internal_relationship_count", 0),
                "in_degree": data.get("in_degree", 0),
                "out_degree": data.get("out_degree", 0),
                "incoming_weight": data.get("incoming_weight", 0),
                "outgoing_weight": data.get("outgoing_weight", 0),
            })
        for u, v, data in model.module_graph.edges(data=True):
            module_graph_data["edges"].append({
                "source": str(u),
                "target": str(v),
                "weight": data.get("weight", 1),
                "relationship_types": data.get("relationship_types", {}),
                "symbol_edge_count": len(data.get("symbol_edges", [])),
            })

    # Serialize component graph
    component_graph_data: dict[str, Any] = {"nodes": [], "edges": []}
    if model.component_graph is not None:
        for node, data in model.component_graph.nodes(data=True):
            component_graph_data["nodes"].append({
                "id": str(node),
                "name": data.get("name", ""),
                "module_count": data.get("module_count", 0),
                "confidence": round(data.get("confidence", 0.0), 3),
                "discovery_methods": data.get("discovery_methods", []),
                "metadata": data.get("metadata", {}),
            })
        for u, v, data in model.component_graph.edges(data=True):
            component_graph_data["edges"].append({
                "source": str(u),
                "target": str(v),
                "weight": data.get("weight", 1),
                "relationship_types": data.get("relationship_types", {}),
            })

    # Serialize flows
    flows_serialized = [flow.to_dict() for flow in model.flows]

    # Overall statistics
    stats = {
        "symbols": total_symbols,
        "modules": len(module_graph_data["nodes"]),
        "components": len(comps_serialized),
        "module_relationships": len(module_graph_data["edges"]),
        "component_relationships": len(component_graph_data["edges"]),
    }

    # DeepWiki data
    wiki_struct_data = model.wiki_structure.to_dict() if model.wiki_structure else None
    wiki_pages_data = {k: v.to_dict() for k, v in model.wiki_pages.items()}
    wiki_cache_data = model.wiki_cache.to_dict() if model.wiki_cache else None

    return {
        "repository": str(model.repository_root),
        "statistics": stats,
        "components": comps_serialized,
        "module_graph": module_graph_data,
        "component_graph": component_graph_data,
        "entry_points": model.entry_points,
        "roles": model.roles,
        "flows": flows_serialized,
        "wiki_structure": wiki_struct_data,
        "wiki_pages": wiki_pages_data,
        "wiki_cache": wiki_cache_data,
        "metadata": model.metadata,
    }


def export_architecture_json(
    model: ArchitectureModel,
    output_path: str | Path,
    indent: int = 2,
) -> None:
    """Exports the serialized architecture model to a JSON file."""
    data = serialize_architecture_model(model)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(data, indent=indent), encoding="utf-8")
