"""
Karuvi Living Codebase Atlas — Unified Web Visualizer & Architecture Cartography
================================================================================

Generates a standalone, interactive, dark-mode Single Page Web Application
embodying Karuvi's core developer-focused modes:
1. ◉ Overview: Executive codebase dashboard, vital metrics, and circular loop radar.
2. 🏛️ Architecture: Discovered components, architectural flows, and AI architecture guide.
3. 🕸️ Graph Explorer: Module and architecture graphs on interactive vis.Network canvas with dynamic role filters.
4. 📁 Code Explorer: Sourcetrail-grade 3-pane view with file tree, full Code Dependency Tree,
                     and syntax-highlighted source code with line jumping.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from architecture.analyzer import ArchitectureAnalyzer
from architecture.documentation import generate_architecture_markdown
from architecture.explanation import ArchitectureExplanationEngine
from architecture.models import ArchitectureModel


def build_unified_payload(
    repo_builder: Any,
    arch_model: ArchitectureModel | None = None,
) -> dict[str, Any]:
    """
    Assembles a unified data contract combining Stage 1 (AST, symbols, references, cycles)
    and Stage 2 (components, module graph, metrics, roles, entrypoints, flows, architecture summary).
    """
    repo_root = Path(repo_builder.project_root).resolve()
    if arch_model is None:
        arch_model = ArchitectureAnalyzer(repo_root).analyze(repo_builder)

    # 1. Components
    components_list = []
    for comp in arch_model.components.values():
        c_dict = comp.to_dict()
        c_dict["evidence"] = comp.discovery_methods
        c_dict["role"] = comp.metadata.get("role", "COMPONENT")
        components_list.append(c_dict)

    # 2. Precompute cross-module references index for Code Dependency Trees
    cross_refs = getattr(repo_builder, "cross_references", [])
    cycles = getattr(repo_builder, "cycles", [])

    # Map file -> inbound and outbound references
    inbound_refs_by_target: dict[str, list[dict[str, Any]]] = {}
    outbound_refs_by_source: dict[str, list[dict[str, Any]]] = {}
    for xr in cross_refs:
        src = xr.get("source_file")
        tgt = xr.get("target_file")
        if tgt:
            inbound_refs_by_target.setdefault(tgt, []).append(xr)
        if src:
            outbound_refs_by_source.setdefault(src, []).append(xr)

    # 3. Module list with enhanced architectural metadata and source code
    modules_list = []
    for mod_id, mod in arch_model.modules.items():
        node_raw = repo_builder.nodes.get(mod_id) if repo_builder else None
        line_count = node_raw.line_count if node_raw else 0
        fn_count = node_raw.function_count if node_raw else 0
        cls_count = node_raw.class_count if node_raw else 0
        var_count = node_raw.variable_count if node_raw else 0

        # Component membership
        comp_id = "core"
        comp_name = "Core"
        for c in arch_model.components.values():
            if mod_id in c.modules:
                comp_id = c.id
                comp_name = c.name
                break

        # Code flow & scope from parsed modules
        code_flow = None
        functions_data = []
        classes_data = []
        if repo_builder and hasattr(repo_builder, "parsed") and mod_id in repo_builder.parsed:
            m_parsed = repo_builder.parsed[mod_id]
            from returns import deptree_to_dict
            code_flow = deptree_to_dict(m_parsed.code_flow)
            for f in m_parsed.functions:
                functions_data.append({
                    "name": f.name,
                    "signature": getattr(f, "signature", ""),
                    "uuid": str(getattr(f, "uuid", "")) if getattr(f, "uuid", None) else None,
                })
            for c in m_parsed.classes:
                cls_methods = [
                    {
                        "name": m.name,
                        "signature": getattr(m, "signature", ""),
                        "uuid": str(getattr(m, "uuid", "")) if getattr(m, "uuid", None) else None,
                    }
                    for m in c.functions
                ]
                classes_data.append({
                    "name": c.name,
                    "uuid": str(getattr(c, "uuid", "")) if getattr(c, "uuid", None) else None,
                    "methods": cls_methods,
                })

        role = arch_model.roles.get(mod_id, "MODULE")

        # Read source code from disk (up to 250KB)
        source_code = ""
        try:
            full_p = Path(mod.path)
            if not full_p.is_absolute():
                full_p = repo_root / full_p
            if full_p.exists() and full_p.is_file() and full_p.stat().st_size <= 250_000:
                source_code = full_p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            source_code = ""

        # Build Inbound Dependents & Outbound Dependencies Tree for this module
        inbound_map: dict[str, dict[str, Any]] = {}
        outbound_map: dict[str, dict[str, Any]] = {}

        for xr in inbound_refs_by_target.get(mod_id, []):
            src_m = xr.get("source_file")
            if src_m and src_m != mod_id:
                if src_m not in inbound_map:
                    inbound_map[src_m] = {"module": src_m, "symbols": set(), "calls": []}
                sym = xr.get("symbol")
                if sym:
                    inbound_map[src_m]["symbols"].add(sym)
                inbound_map[src_m]["calls"].append({
                    "symbol": sym,
                    "line": xr.get("decl_line", 1),
                    "scope": xr.get("scope", "caller"),
                })

        for xr in outbound_refs_by_source.get(mod_id, []):
            tgt_m = xr.get("target_file")
            if tgt_m and tgt_m != mod_id:
                if tgt_m not in outbound_map:
                    outbound_map[tgt_m] = {"module": tgt_m, "symbols": set(), "calls": []}
                sym = xr.get("symbol")
                if sym:
                    outbound_map[tgt_m]["symbols"].add(sym)
                outbound_map[tgt_m]["calls"].append({
                    "symbol": sym,
                    "line": xr.get("decl_line", 1),
                    "scope": xr.get("scope", "call"),
                })

        # Ensure direct imports from module graph are also reflected
        for inc_m in mod.incoming_modules:
            if inc_m != mod_id and inc_m not in inbound_map:
                inbound_map[inc_m] = {"module": inc_m, "symbols": set(), "calls": []}
        for out_m in mod.outgoing_modules:
            if out_m != mod_id and out_m not in outbound_map:
                outbound_map[out_m] = {"module": out_m, "symbols": set(), "calls": []}

        inbound_list = [
            {
                "module": v["module"],
                "symbols": sorted(list(v["symbols"])),
                "calls": v["calls"][:25],
            }
            for v in inbound_map.values()
        ]
        outbound_list = [
            {
                "module": v["module"],
                "symbols": sorted(list(v["symbols"])),
                "calls": v["calls"][:25],
            }
            for v in outbound_map.values()
        ]

        modules_list.append({
            "id": mod_id,
            "path": mod.path,
            "name": Path(mod.path).name,
            "stem": Path(mod.path).stem,
            "component_id": comp_id,
            "component_name": comp_name,
            "role": role,
            "line_count": line_count,
            "function_count": fn_count,
            "class_count": cls_count,
            "variable_count": var_count,
            "in_degree": mod.metadata.get("metrics", {}).get("in_degree", len(mod.incoming_modules)),
            "out_degree": mod.metadata.get("metrics", {}).get("out_degree", len(mod.outgoing_modules)),
            "incoming_weight": mod.incoming_weight,
            "outgoing_weight": mod.outgoing_weight,
            "incoming_modules": mod.incoming_modules,
            "outgoing_modules": mod.outgoing_modules,
            "internal_relationships": mod.metadata.get("internal_relationship_count", 0),
            "betweenness": round(mod.metadata.get("metrics", {}).get("betweenness_centrality", 0.0), 3),
            "pagerank": round(mod.metadata.get("metrics", {}).get("pagerank", 0.0), 4),
            "reachable_descendants": mod.metadata.get("metrics", {}).get("reachable_descendant_count", 0),
            "functions": functions_data,
            "classes": classes_data,
            "code_flow": code_flow,
            "source_code": source_code,
            "inbound_dependents": inbound_list,
            "outbound_dependencies": outbound_list,
        })

    # 4. Component Graph Edges
    comp_edges = []
    if arch_model.component_graph is not None:
        for u, v, d in arch_model.component_graph.edges(data=True):
            comp_edges.append({
                "source": str(u),
                "target": str(v),
                "weight": d.get("weight", 1),
                "relationship_types": d.get("relationship_types", {}),
            })

    # 5. Module Graph Edges
    mod_edges = []
    if arch_model.module_graph is not None:
        for u, v, d in arch_model.module_graph.edges(data=True):
            mod_edges.append({
                "source": str(u),
                "target": str(v),
                "weight": d.get("weight", 1),
                "relationship_types": d.get("relationship_types", {}),
                "symbol_edges": d.get("symbol_edges", [])[:15],
            })

    # 6. Overall Stats
    stats = {
        "total_modules": len(modules_list),
        "total_components": len(components_list),
        "total_symbols": sum(m["function_count"] + m["class_count"] + m["variable_count"] for m in modules_list),
        "total_lines": sum(m["line_count"] for m in modules_list),
        "total_module_edges": len(mod_edges),
        "total_component_edges": len(comp_edges),
        "total_edges": len(mod_edges),
        "total_cross_references": len(cross_refs),
        "total_cycles": len(cycles),
        "circular_dependencies": len(cycles),
    }

    # 7. AI Model Architecture Summaries (Levels 1 to 3)
    explanation_engine = ArchitectureExplanationEngine()
    repo_explanation = explanation_engine.explain_repository(arch_model, repo_builder)
    arch_explanation = explanation_engine.explain_architecture(arch_model)
    mod_explanations = {
        m: explanation_engine.explain_module(m, arch_model, repo_builder)
        for m in arch_model.modules
    }

    # 8. Precomputed Markdown Documentation
    doc_markdown = generate_architecture_markdown(arch_model)

    # 9. DeepWiki Architecture Structure & Pages
    wiki_structure_dict = arch_model.wiki_structure.to_dict() if getattr(arch_model, "wiki_structure", None) else None
    wiki_pages_dict = (
        {k: v.to_dict() for k, v in arch_model.wiki_pages.items()}
        if getattr(arch_model, "wiki_pages", None)
        else {}
    )
    ai_provider = arch_model.metadata.get("provider", "gemini") if hasattr(arch_model, "metadata") else "gemini"
    ai_model_name = arch_model.metadata.get("model", "gemini-2.5-flash") if hasattr(arch_model, "metadata") else "gemini-2.5-flash"

    return {
        "project_name": repo_root.name,
        "project_root": str(repo_root),
        "stats": stats,
        "summary": stats,
        "components": components_list,
        "modules": modules_list,
        "component_edges": comp_edges,
        "module_edges": mod_edges,
        "cross_references": cross_refs[:200],
        "cycles": cycles,
        "entry_points": arch_model.entry_points,
        "entrypoints": arch_model.entry_points,
        "flows": [f.to_dict() for f in arch_model.flows],
        "documentation_md": doc_markdown,
        "wiki_structure": wiki_structure_dict,
        "wiki_pages": wiki_pages_dict,
        "ai_provider": ai_provider,
        "ai_model": ai_model_name,
        "architecture_summary": {
            "repository": repo_explanation,
            "architecture": arch_explanation,
            "modules": mod_explanations,
        },
    }


def generate_atlas_html(
    repo_builder: Any,
    arch_model: ArchitectureModel | None = None,
) -> str:
    """
    Renders the complete Living Codebase Atlas Single Page Application HTML.
    """
    payload = build_unified_payload(repo_builder, arch_model)
    payload_json = json.dumps(payload, ensure_ascii=False)
    safe_payload_json = payload_json.replace("</script>", "<\\/script>")
    return HTML_TEMPLATE.replace("__KARUVI_PAYLOAD__", safe_payload_json)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Karuvi — Living Codebase Atlas</title>
  <!-- Google Fonts & Vis-Network -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {
      --bg-base: #050811;
      --bg-surface: #0b1120;
      --bg-card: #0f172a;
      --bg-card-hover: #17223b;
      --border: #1e293b;
      --border-highlight: #334155;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-blue: #38bdf8;
      --accent-cyan: #22d3ee;
      --accent-purple: #c084fc;
      --accent-amber: #f59e0b;
      --accent-green: #10b981;
      --accent-rose: #f43f5e;
      
      --role-entry: #22d3ee;
      --role-hub: #c084fc;
      --role-bridge: #f59e0b;
      --role-leaf: #10b981;
      --role-cycle: #f43f5e;
      --role-module: #38bdf8;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-base);
      color: var(--text-primary);
      min-height: 100vh;
      overflow-x: hidden;
      display: flex;
      flex-direction: column;
    }

    /* Top Navigation Header */
    header.topbar {
      height: 64px;
      background: rgba(11, 17, 32, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .topbar-left {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .logo-badge {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: #fff;
    }

    .logo-icon {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 16px;
      color: #fff;
      box-shadow: 0 0 16px rgba(56, 189, 248, 0.35);
    }

    .logo-text {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .logo-tag {
      font-size: 10px;
      font-weight: 600;
      color: var(--accent-cyan);
      background: rgba(34, 211, 238, 0.1);
      border: 1px solid rgba(34, 211, 238, 0.2);
      padding: 2px 8px;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .search-btn {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .search-btn:hover {
      border-color: var(--accent-blue);
      color: var(--text-primary);
    }

    kbd {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      font-family: 'Fira Code', monospace;
    }

    /* App Body Layout */
    .app-container {
      display: flex;
      flex: 1;
      height: calc(100vh - 64px);
    }

    /* Navigation Sidebar */
    nav.sidebar {
      width: 240px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      padding: 16px 12px;
      gap: 6px;
    }

    .nav-section-label {
      font-size: 10px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 8px 12px 4px 12px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-radius: 8px;
      color: var(--text-secondary);
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      transition: all 0.15s ease;
      user-select: none;
    }

    .nav-item:hover {
      background: var(--bg-card);
      color: var(--text-primary);
    }

    .nav-item.active {
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent-blue);
      font-weight: 600;
      border: 1px solid rgba(56, 189, 248, 0.25);
    }

    .nav-item .icon {
      font-size: 16px;
    }

    .sidebar-footer {
      margin-top: auto;
      padding: 14px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    /* Main Workspace */
    main.workspace {
      flex: 1;
      overflow-y: auto;
      background: var(--bg-base);
      position: relative;
    }

    .tab-view {
      display: none;
      min-height: 100%;
    }

    .tab-view.active {
      display: block;
    }

    /* Common Components */
    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      font-family: 'Fira Code', monospace;
    }

    .role-badge {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
      font-family: 'Fira Code', monospace;
    }

    .btn-primary {
      background: linear-gradient(135deg, #0284c7, #0ea5e9);
      color: #fff;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
    }
    .btn-primary:hover {
      background: linear-gradient(135deg, #0369a1, #0284c7);
      box-shadow: 0 0 12px rgba(14, 165, 233, 0.4);
    }

    .btn-secondary {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-primary);
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
    }
    .btn-secondary:hover {
      background: var(--bg-card-hover);
      border-color: var(--border-highlight);
    }

    /* ============================================================== */
    /* VIEW 1: OVERVIEW HERO & METRICS                                */
    /* ============================================================== */
    #tab-overview {
      padding: 32px 40px;
    }

    .overview-hero {
      margin-bottom: 32px;
    }

    .overview-hero h1 {
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
      background: linear-gradient(to right, #fff, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .overview-hero p {
      color: var(--text-secondary);
      font-size: 14px;
      max-width: 700px;
      line-height: 1.6;
    }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .stat-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
      transition: all 0.15s ease;
    }

    .stat-card:hover {
      border-color: var(--border-highlight);
      transform: translateY(-2px);
    }

    .stat-val {
      font-size: 26px;
      font-weight: 800;
      color: #fff;
      font-family: 'Fira Code', monospace;
      margin-bottom: 4px;
    }

    .stat-lbl {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .banner-entrypoint {
      background: linear-gradient(135deg, rgba(34, 211, 238, 0.08), rgba(56, 189, 248, 0.04));
      border: 1px solid rgba(34, 211, 238, 0.3);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .banner-content h3 {
      font-size: 16px;
      font-weight: 700;
      color: var(--accent-cyan);
      margin-bottom: 6px;
    }

    .banner-content .mod-title {
      font-family: 'Fira Code', monospace;
      font-size: 18px;
      color: #fff;
      font-weight: 600;
      margin-bottom: 6px;
    }

    .banner-content p {
      font-size: 13px;
      color: var(--text-secondary);
      max-width: 600px;
    }

    /* Radar / Cycles Warning */
    .radar-container {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 32px;
    }

    .radar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .cycle-item {
      background: rgba(244, 63, 94, 0.06);
      border: 1px solid rgba(244, 63, 94, 0.2);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 8px;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      color: #fecdd3;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    /* ============================================================== */
    /* VIEW 2: ARCHITECTURE                                           */
    /* ============================================================== */
    #tab-architecture {
      padding: 32px 40px;
    }

    .comp-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
      margin-bottom: 40px;
    }

    .comp-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      transition: all 0.2s ease;
    }

    .comp-card:hover {
      border-color: var(--accent-blue);
      transform: translateY(-2px);
    }

    .comp-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .comp-name {
      font-size: 17px;
      font-weight: 700;
      color: #fff;
    }

    .comp-confidence {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 6px;
      font-family: 'Fira Code', monospace;
      font-weight: 600;
      background: rgba(16, 185, 129, 0.1);
      color: var(--accent-green);
      border: 1px solid rgba(16, 185, 129, 0.2);
    }

    .comp-modules-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-family: 'Fira Code', monospace;
      font-size: 11px;
      color: var(--text-secondary);
      max-height: 120px;
      overflow-y: auto;
    }

    .flows-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 36px;
    }

    .flow-row {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      overflow-x: auto;
    }

    .flow-step {
      background: var(--bg-card);
      border: 1px solid var(--border-highlight);
      padding: 4px 10px;
      border-radius: 6px;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      color: #fff;
      white-space: nowrap;
    }

    .flow-arrow {
      color: var(--accent-blue);
      font-weight: 700;
    }

    .arch-doc-container {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 32px;
      line-height: 1.7;
    }

    /* ============================================================== */
    /* VIEW 3: GRAPH EXPLORER                                         */
    /* ============================================================== */
    #tab-graph {
      height: 100%;
      display: none;
      flex-direction: column;
      overflow: hidden;
    }

    #tab-graph.active {
      display: flex;
    }

    .graph-layout {
      display: flex;
      height: 100%;
      width: 100%;
      position: relative;
      overflow: hidden;
    }

    .graph-canvas-container {
      flex: 1;
      height: 100%;
      width: 100%;
      position: relative;
      background: #070b14;
      overflow: hidden;
    }

    #network-canvas {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      height: 100%;
    }

    /* DeepWiki Architecture Wiki & Toolbar */
    .deepwiki-toolbar {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 24px;
    }

    .deepwiki-toolbar-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .deepwiki-badge {
      font-size: 11px;
      font-weight: 700;
      color: var(--accent-cyan);
      background: rgba(34, 211, 238, 0.1);
      border: 1px solid rgba(34, 211, 238, 0.25);
      padding: 4px 10px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .deepwiki-provider-info {
      font-size: 12px;
      color: var(--text-secondary);
      font-family: 'Fira Code', monospace;
    }

    .deepwiki-layout {
      display: flex;
      gap: 20px;
      min-height: 520px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 32px;
    }

    .deepwiki-sidebar {
      width: 280px;
      background: #090e1a;
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }

    .deepwiki-sidebar-header {
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #fff;
    }

    .deepwiki-nav-tree {
      padding: 12px 10px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 4px;
      max-height: 580px;
    }

    .deepwiki-nav-section-title {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      padding: 10px 10px 4px 10px;
    }

    .deepwiki-nav-item {
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      color: var(--text-secondary);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.15s ease;
      user-select: none;
    }

    .deepwiki-nav-item:hover {
      background: var(--bg-card);
      color: var(--text-primary);
    }

    .deepwiki-nav-item.active {
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent-blue);
      font-weight: 600;
      border-left: 3px solid var(--accent-blue);
    }

    .deepwiki-pill-high {
      font-size: 9px;
      font-weight: 700;
      color: #f59e0b;
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.25);
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .deepwiki-content-area {
      flex: 1;
      padding: 32px 40px;
      overflow-y: auto;
      max-height: 620px;
      line-height: 1.7;
    }

    .deepwiki-page-view details {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 24px;
    }

    .deepwiki-page-view details summary {
      cursor: pointer;
      font-weight: 600;
      color: var(--accent-cyan);
      outline: none;
      user-select: none;
    }

    .deepwiki-page-view table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      font-size: 12px;
    }

    .deepwiki-page-view th, .deepwiki-page-view td {
      border: 1px solid var(--border);
      padding: 8px 12px;
      text-align: left;
    }

    .deepwiki-page-view th {
      background: rgba(15, 23, 42, 0.9);
      color: #fff;
    }

    /* Modal Backdrop and Card */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-card {
      background: #0f172a;
      border: 1px solid var(--border-highlight);
      border-radius: 12px;
      width: 90%;
      max-width: 520px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
      overflow: hidden;
    }

    .modal-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-close {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
    }

    .modal-close:hover {
      color: #fff;
    }

    .modal-body {
      padding: 20px;
    }

    .form-group {
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-lbl {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .form-input {
      background: #090e1a;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 9px 12px;
      font-size: 12px;
      color: #fff;
      font-family: inherit;
    }

    .form-input:focus {
      outline: none;
      border-color: var(--accent-blue);
    }

    .modal-footer {
      padding: 14px 20px;
      border-top: 1px solid var(--border);
      background: rgba(11, 17, 32, 0.6);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }

    .graph-floating-controls {
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 10;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .pill-group {
      background: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 4px;
      display: flex;
      gap: 4px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }

    .pill-opt {
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      cursor: pointer;
      user-select: none;
      transition: all 0.15s ease;
    }

    .pill-opt:hover {
      color: var(--text-primary);
    }

    .pill-opt.active {
      background: var(--accent-blue);
      color: #050811;
      font-weight: 700;
    }

    /* Role Filter Group */
    .role-filter-group {
      background: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 4px 8px;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }

    .role-filter-lbl {
      font-size: 10px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      padding-right: 4px;
    }

    .role-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-secondary);
      font-size: 11px;
      font-weight: 600;
      padding: 4px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-family: 'Fira Code', monospace;
      transition: all 0.15s ease;
    }

    .role-btn:hover {
      color: #fff;
      border-color: var(--border-highlight);
    }

    .role-btn.active {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
      border-color: currentColor;
    }

    .graph-inspector {
      width: 320px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      overflow-y: auto;
    }

    .inspector-title {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }

    .inspector-sub {
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'Fira Code', monospace;
    }

    .inspector-prop {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      padding: 6px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    .inspector-prop .lbl { color: var(--text-muted); }
    .inspector-prop .val { font-weight: 600; color: #fff; font-family: 'Fira Code', monospace; }

    /* ============================================================== */
    /* VIEW 4: SOURCETRAIL CODE EXPLORER & CODE DEPENDENCY TREE       */
    /* ============================================================== */
    #tab-code {
      height: 100%;
      display: none;
      overflow: hidden;
    }

    #tab-code.active {
      display: block;
    }

    .code-layout {
      display: grid;
      grid-template-columns: 240px 340px 1fr;
      height: 100%;
      background: var(--bg-card);
      overflow: hidden;
    }

    /* Left Pane: File Tree */
    .file-tree-pane {
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .file-tree-item {
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-family: 'Fira Code', monospace;
      color: var(--text-secondary);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      user-select: none;
      transition: all 0.1s ease;
    }

    .file-tree-item:hover {
      background: var(--bg-card);
      color: #fff;
    }

    .file-tree-item.active {
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent-blue);
      font-weight: 600;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }

    /* Middle Pane: Code Dependency Tree */
    .code-deptree-pane {
      background: #090e1a;
      border-right: 1px solid var(--border);
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    .deptree-header {
      padding: 14px 16px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .deptree-title {
      font-size: 12px;
      font-weight: 700;
      color: #fff;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .deptree-content {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .deptree-section {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .deptree-section-title {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .deptree-node {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 11px;
      font-family: 'Fira Code', monospace;
      color: var(--text-primary);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 4px;
      transition: all 0.15s ease;
    }

    .deptree-node:hover {
      border-color: var(--accent-blue);
      background: var(--bg-card);
    }

    .deptree-node-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .deptree-node-symbols {
      color: var(--accent-cyan);
      font-size: 10px;
      padding-left: 12px;
      line-height: 1.5;
    }

    .deptree-call-item {
      color: var(--text-secondary);
      font-size: 10px;
      padding-left: 12px;
    }

    /* Right Pane: Code Viewer */
    .code-viewer-pane {
      background: var(--bg-base);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .code-viewer-header {
      padding: 12px 20px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .code-viewer-content {
      flex: 1;
      overflow: auto;
      padding: 16px 20px;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      line-height: 1.6;
    }

    .code-table {
      width: 100%;
      border-collapse: collapse;
    }

    .code-line-num {
      width: 44px;
      color: var(--text-muted);
      text-align: right;
      padding-right: 16px;
      user-select: none;
      border-right: 1px solid var(--border);
    }

    .code-line-text {
      padding-left: 16px;
      white-space: pre;
      color: #e2e8f0;
    }

    .code-line-highlight {
      background: rgba(56, 189, 248, 0.12);
    }

    /* Syntax highlight colors */
    .syntax-kw { color: #f43f5e; font-weight: 600; }
    .syntax-fn { color: #38bdf8; font-weight: 600; }
    .syntax-cls { color: #c084fc; font-weight: 600; }
    .syntax-str { color: #10b981; }
    .syntax-cmt { color: #64748b; font-style: italic; }

    /* Global Search Modal */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(5, 8, 17, 0.8);
      backdrop-filter: blur(8px);
      z-index: 100;
      align-items: center;
      justify-content: center;
    }

    .modal-overlay.active {
      display: flex;
    }

    .search-modal {
      width: 580px;
      max-width: 90vw;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
      overflow: hidden;
    }

    .search-input-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
    }

    .search-input-wrap input {
      flex: 1;
      background: transparent;
      border: none;
      color: #fff;
      font-size: 15px;
      outline: none;
      font-family: inherit;
    }

    .search-results {
      max-height: 380px;
      overflow-y: auto;
      padding: 8px;
    }

    .search-item {
      padding: 10px 14px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: all 0.1s ease;
    }

    .search-item:hover {
      background: var(--bg-card);
    }
  </style>
</head>
<body>

  <!-- Top Bar -->
  <header class="topbar">
    <div class="topbar-left">
      <a href="#" class="logo-badge">
        <div class="logo-icon">K</div>
        <div class="logo-text">KARUVI</div>
      </a>
      <span class="logo-tag">Living Atlas</span>
      <span style="color: var(--text-muted); font-size: 13px;" id="header-project-name">Loading...</span>
    </div>
    <div class="topbar-right">
      <button class="search-btn" id="btn-open-search">
        <span>Search Codebase</span>
        <kbd>⌘K</kbd>
      </button>
    </div>
  </header>

  <!-- App Body Layout -->
  <div class="app-container">
    <!-- Navigation Sidebar -->
    <nav class="sidebar">
      <div class="nav-section-label">Cartography</div>
      <div class="nav-item active" data-tab="overview">
        <span class="icon">◉</span>
        <span>Overview</span>
      </div>
      <div class="nav-item" data-tab="architecture">
        <span class="icon">🏛️</span>
        <span>Architecture</span>
      </div>
      <div class="nav-item" data-tab="graph">
        <span class="icon">🕸️</span>
        <span>Graph Explorer</span>
      </div>
      <div class="nav-item" data-tab="code">
        <span class="icon">📁</span>
        <span>Code Explorer</span>
      </div>

      <div class="sidebar-footer">
        <span>Deterministic Intelligence</span>
        <span style="opacity: 0.6;">Karuvi v0.2.0</span>
      </div>
    </nav>

    <!-- Main Workspace -->
    <main class="workspace">

      <!-- VIEW 1: OVERVIEW -->
      <div class="tab-view active" id="tab-overview">
        <div class="overview-hero">
          <h1>Codebase Intelligence & Cartography</h1>
          <p>Deterministic architecture reconstruction, topological graph analysis, and code dependency trees.</p>
        </div>

        <div class="stat-grid" id="stats-container"></div>

        <!-- Start Here Entry Point Banner -->
        <div class="banner-entrypoint" id="entry-point-banner">
          <div class="banner-content">
            <h3>🚪 Recommended Starting Point</h3>
            <div class="mod-title" id="entry-mod-name">analyzing...</div>
            <p id="entry-mod-desc">This module sits structurally high and can reach major portions of the repository.</p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn-primary" onclick="window.switchTab('graph')">Explore Module Graph ➔</button>
            <button class="btn-secondary" id="btn-jump-code">View Code</button>
          </div>
        </div>

        <!-- Circular Dependencies Radar -->
        <div class="radar-container" id="radar-container">
          <div class="radar-header">
            <div class="section-title" style="margin-bottom: 0;">⚠️ Circular Dependency Radar</div>
            <span class="badge" id="cycles-badge" style="background: rgba(244, 63, 94, 0.1); color: var(--accent-rose);">0 loops detected</span>
          </div>
          <div id="cycles-list"></div>
        </div>
      </div>

      <!-- VIEW 2: ARCHITECTURE (DeepWiki Architecture Cartography & Wiki) -->
      <div class="tab-view" id="tab-architecture">
        <!-- DeepWiki AI Provider & Model Toolbar -->
        <div class="deepwiki-toolbar">
          <div class="deepwiki-toolbar-left">
            <span class="deepwiki-badge">📖 DeepWiki Architecture Engine</span>
            <span class="deepwiki-provider-info" id="deepwiki-current-model">AI Provider: Gemini (gemini-2.5-flash)</span>
          </div>
          <div class="deepwiki-toolbar-right">
            <button class="btn-secondary" id="btn-open-provider-modal">⚙️ AI Model & Provider</button>
          </div>
        </div>

        <div class="deepwiki-layout">
          <!-- DeepWiki Wiki Navigation Sidebar -->
          <div class="deepwiki-sidebar" id="deepwiki-sidebar">
            <div class="deepwiki-sidebar-header">Architecture Wiki</div>
            <div class="deepwiki-nav-tree" id="deepwiki-nav-tree"></div>
          </div>

          <!-- DeepWiki Main Wiki Content Area -->
          <div class="deepwiki-content-area">
            <div id="deepwiki-page-view" class="deepwiki-page-view"></div>
          </div>
        </div>

        <div class="section-title" style="margin-top: 36px;">🏛️ Discovered Subsystems & Components</div>
        <div class="comp-grid" id="arch-components-grid"></div>

        <div class="section-title">🌊 High-Level Architectural Flows</div>
        <div class="flows-container" id="arch-flows-container"></div>
      </div>

      <!-- VIEW 3: GRAPH EXPLORER (Modules & Architecture Graph on Vis.Network) -->
      <div class="tab-view" id="tab-graph">
        <div class="graph-layout">
          <div class="graph-canvas-container">
            <div class="graph-floating-controls">
              <!-- Modules and Architecture Graph only (no symbols) -->
              <div class="pill-group" id="graph-level-pills">
                <div class="pill-opt active" data-level="modules">Modules</div>
                <div class="pill-opt" data-level="architecture">Architecture Graph</div>
              </div>
              <!-- Role Filter Buttons -->
              <div class="role-filter-group" id="role-filter-group">
                <span class="role-filter-lbl">Role:</span>
                <button class="role-btn active" data-role="ALL">All</button>
                <button class="role-btn" data-role="ENTRY_CANDIDATE" style="color: var(--role-entry);">Entry</button>
                <button class="role-btn" data-role="HUB" style="color: var(--role-hub);">Hub</button>
                <button class="role-btn" data-role="BRIDGE" style="color: var(--role-bridge);">Bridge</button>
                <button class="role-btn" data-role="LEAF" style="color: var(--role-leaf);">Leaf</button>
                <button class="role-btn" data-role="CYCLE_MEMBER" style="color: var(--role-cycle);">Cycle</button>
              </div>
              <div class="pill-group" id="graph-edge-filters" style="padding: 2px 8px; font-size: 11px;">
                <label style="display:flex; align-items:center; gap:4px; margin-right:8px;"><input type="checkbox" id="chk-filter-calls" checked> Calls</label>
                <label style="display:flex; align-items:center; gap:4px; margin-right:8px;"><input type="checkbox" id="chk-filter-imports" checked> Imports</label>
                <label style="display:flex; align-items:center; gap:4px;"><input type="checkbox" id="chk-filter-refs" checked> Refs</label>
              </div>
            </div>

            <!-- Vis Network Canvas for Modules and Architecture Components -->
            <div id="network-canvas"></div>
          </div>

          <!-- Inspector Panel -->
          <div class="graph-inspector" id="graph-inspector">
            <div class="inspector-title" id="insp-title">Select a Node</div>
            <div class="inspector-sub" id="insp-sub">Click any module or component to inspect its relationships. Double-click to jump to Code Explorer.</div>
            <div id="insp-body"></div>
          </div>
        </div>
      </div>

      <!-- VIEW 4: SOURCETRAIL CODE EXPLORER & CODE DEPENDENCY TREE -->
      <div class="tab-view" id="tab-code">
        <div class="code-layout">
          <!-- 1. File Tree -->
          <div class="file-tree-pane" id="code-file-tree"></div>

          <!-- 2. Code Dependency Tree Pane -->
          <div class="code-deptree-pane" id="code-deptree-pane">
            <div class="deptree-header">
              <span class="deptree-title">🌿 Code Dependency Tree</span>
              <span class="badge" id="deptree-stats-badge" style="background: rgba(56, 189, 248, 0.1); color: var(--accent-blue);">0 In / 0 Out</span>
            </div>
            <div class="deptree-content" id="deptree-content">
              <div style="color: var(--text-muted); font-size: 12px; line-height: 1.6;">
                Select a module on the left to inspect its inbound callers, outbound imports, and symbol call hierarchy.
              </div>
            </div>
          </div>

          <!-- 3. Code Viewer Pane -->
          <div class="code-viewer-pane" id="code-viewer-pane">
            <div class="code-viewer-header" id="code-viewer-header">
              <div style="font-family: 'Fira Code', monospace; font-size: 13px; font-weight: 600; color: #fff;" id="code-file-path">Select a file from the tree</div>
              <div id="code-header-actions"></div>
            </div>
            <div class="code-viewer-content" id="code-viewer-content">
              <div style="color: var(--text-muted); font-size: 13px; padding: 20px;">
                Select a file to inspect its syntax-highlighted source code, AST hierarchy, and symbol bindings.
              </div>
            </div>
          </div>
        </div>
      </div>

    </main>
  </div>

  <!-- Global Search Modal (Cmd+K) -->
  <div class="modal-overlay" id="search-modal-overlay">
    <div class="search-modal">
      <div class="search-input-wrap">
        <span>🔍</span>
        <input type="text" id="global-search-input" placeholder="Search components, modules, symbols, or roles... (Esc to close)">
      </div>
      <div class="search-results" id="search-results-list"></div>
    </div>
  </div>

  <!-- Embedded Payload -->
  <script>
    window.KARUVI_DATA = __KARUVI_PAYLOAD__;
    window.__KARUVI_DATA__ = window.KARUVI_DATA;

    document.addEventListener('DOMContentLoaded', function() {
      const data = window.KARUVI_DATA;
      if (!data) return;

      // Header Project Name
      const headerTitleEl = document.getElementById('header-project-name');
      if (headerTitleEl) {
        headerTitleEl.textContent = `${data.project_name} (${data.stats.total_modules} modules • ${data.stats.total_components} components)`;
      }

      // -------------------------------------------------------------
      // Tab Navigation
      // -------------------------------------------------------------
      const navItems = document.querySelectorAll('.sidebar .nav-item');
      const tabViews = document.querySelectorAll('.tab-view');

      window.switchTab = function(tabId) {
        navItems.forEach(n => n.classList.toggle('active', n.dataset.tab === tabId));
        tabViews.forEach(v => v.classList.toggle('active', v.id === `tab-${tabId}`));

        if (tabId === 'graph') {
          setTimeout(() => {
            initOrFitNetwork();
            if (network) {
              network.setSize('100%', '100%');
              network.redraw();
              network.fit({ animation: { duration: 250 } });
            }
          }, 60);
        }
      };

      navItems.forEach(item => {
        item.addEventListener('click', () => {
          switchTab(item.dataset.tab);
        });
      });

      // -------------------------------------------------------------
      // 1. Overview Dashboard
      // -------------------------------------------------------------
      const statsContainer = document.getElementById('stats-container');
      const st = data.stats;
      statsContainer.innerHTML = `
        <div class="stat-card">
          <div class="stat-val">${st.total_modules}</div>
          <div class="stat-lbl">Python Modules</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">${st.total_components}</div>
          <div class="stat-lbl">Architectural Layers</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">${st.total_symbols}</div>
          <div class="stat-lbl">Symbols & Callables</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">${st.total_lines}</div>
          <div class="stat-lbl">Lines of Code</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">${st.total_module_edges}</div>
          <div class="stat-lbl">Dependency Edges</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" style="color: ${st.circular_dependencies > 0 ? 'var(--accent-rose)' : 'var(--accent-green)'}">
            ${st.circular_dependencies}
          </div>
          <div class="stat-lbl">Circular Loops</div>
        </div>
      `;

      // Entrypoint Banner
      const topEntry = (data.entry_points || [])[0];
      if (topEntry) {
        document.getElementById('entry-mod-name').textContent = topEntry.module;
        let entryEvidence = '';
        if (Array.isArray(topEntry.evidence)) {
          entryEvidence = topEntry.evidence.join(', ');
        } else if (topEntry.evidence && typeof topEntry.evidence === 'object') {
          entryEvidence = Object.entries(topEntry.evidence)
            .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
            .join(', ');
        } else {
          entryEvidence = String(topEntry.evidence || '');
        }
        document.getElementById('entry-mod-desc').textContent = 
          `Identified with reach score ${topEntry.entry_score}. Evidence: ${entryEvidence || 'Low inbound coupling, high reachable hierarchy.'}`;
        
        document.getElementById('btn-jump-code').onclick = () => {
          window.selectModule(topEntry.module, true);
        };
      }

      // Circular Dependencies Radar
      const cyclesListEl = document.getElementById('cycles-list');
      const cycles = data.cycles || [];
      const badge = document.getElementById('cycles-badge');
      if (cycles.length === 0) {
        badge.textContent = 'Clean DAG (0 loops)';
        badge.style.background = 'rgba(16, 185, 129, 0.1)';
        badge.style.color = 'var(--accent-green)';
        cyclesListEl.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No circular dependencies detected. Architecture flows acyclically.</div>';
      } else {
        badge.textContent = `${cycles.length} circular loops detected`;
        cyclesListEl.innerHTML = cycles.map(c => `
          <div class="cycle-item">
            <span>⚠️ Loop:</span>
            <span>${Array.isArray(c) ? c.join(' ➔ ') : String(c)}</span>
          </div>
        `).join('');
      }

      // -------------------------------------------------------------
      // 2. Architecture View
      // -------------------------------------------------------------
      const compGrid = document.getElementById('arch-components-grid');
      compGrid.innerHTML = (data.components || []).map(c => `
        <div class="comp-card">
          <div class="comp-header">
            <div>
              <div class="comp-name">${c.name}</div>
              <span class="role-badge" style="color: var(--accent-blue); background: rgba(56, 189, 248, 0.1);">${c.role}</span>
            </div>
            <div class="comp-confidence">${Math.round(c.confidence * 100)}% Match</div>
          </div>
          <div style="font-size: 11px; color: var(--text-muted);">${(c.modules || []).length} modules:</div>
          <div class="comp-modules-list">
            ${(c.modules || []).map(m => `<div>• ${m}</div>`).join('')}
          </div>
          <button class="btn-secondary" style="padding: 4px 10px; font-size: 11px; justify-content: center; margin-top: auto;" onclick="window.inspectComponent('${c.id}')">
            View in Graph Explorer ➔
          </button>
        </div>
      `).join('');

      const flowsContainer = document.getElementById('arch-flows-container');
      if ((data.flows || []).length === 0) {
        flowsContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No multi-stage flows detected.</div>';
      } else {
        flowsContainer.innerHTML = (data.flows || []).map(f => `
          <div class="flow-row">
            <span class="badge" style="background: rgba(56, 189, 248, 0.1); color: var(--accent-blue);">${f.flow_type || 'FLOW'}</span>
            ${f.path.map((step, idx) => `
              <span class="flow-step">${step}</span>
              ${idx < f.path.length - 1 ? '<span class="flow-arrow">➔</span>' : ''}
            `).join('')}
          </div>
        `).join('');
      }

      // Render DeepWiki Architecture View
      renderDeepWikiView();

      // -------------------------------------------------------------
      // 3. File Tree & Code Explorer
      // -------------------------------------------------------------
      const treeContainer = document.getElementById('code-file-tree');
      treeContainer.innerHTML = (data.modules || []).map(m => {
        let roleBadgeColor = 'var(--role-module)';
        if (m.role === 'ENTRY_CANDIDATE') roleBadgeColor = 'var(--role-entry)';
        else if (m.role === 'HUB') roleBadgeColor = 'var(--role-hub)';
        else if (m.role === 'BRIDGE') roleBadgeColor = 'var(--role-bridge)';
        else if (m.role === 'LEAF') roleBadgeColor = 'var(--role-leaf)';
        return `
          <div class="file-tree-item" id="tree-item-${m.id.replace(/[^a-zA-Z0-9]/g, '_')}" onclick="window.selectModule('${m.id}')">
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${m.path}</span>
            <span class="role-badge" style="color: ${roleBadgeColor}; border: 1px solid rgba(255,255,255,0.1);">${m.role}</span>
          </div>
        `;
      }).join('');

      function highlightPythonSyntax(rawText) {
        if (!rawText) return '<em>(Source code empty or file not on disk)</em>';
        const lines = rawText.split('\\n');
        return lines.map((line, idx) => {
          let escaped = line
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

          escaped = escaped.replace(/(#.*$)/g, '<span class="syntax-cmt">$1</span>');
          escaped = escaped.replace(/\\b(def)\\s+([a-zA-Z0-9_]+)/g, '<span class="syntax-kw">$1</span> <span class="syntax-fn">$2</span>');
          escaped = escaped.replace(/\\b(class)\\s+([a-zA-Z0-9_]+)/g, '<span class="syntax-kw">$1</span> <span class="syntax-cls">$2</span>');
          escaped = escaped.replace(/\\b(from|import|return|if|else|elif|for|while|try|except|finally|with|as|in|is|not|and|or|None|True|False)\\b/g, '<span class="syntax-kw">$1</span>');
          escaped = escaped.replace(/(".*?"|'.*?')/g, '<span class="syntax-str">$1</span>');

          return `
            <tr id="line-tr-${idx + 1}">
              <td class="code-line-num">${idx + 1}</td>
              <td class="code-line-text">${escaped}</td>
            </tr>
          `;
        }).join('');
      }

      window.jumpToCodeLine = function(lineNum) {
        document.querySelectorAll('.code-line-highlight').forEach(el => el.classList.remove('code-line-highlight'));
        const row = document.getElementById(`line-tr-${lineNum}`);
        if (row) {
          row.classList.add('code-line-highlight');
          row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      };

      // -------------------------------------------------------------
      // 4. Code Dependency Tree Renderer
      // -------------------------------------------------------------
      function renderCodeDependencyTree(mod) {
        const deptreeContent = document.getElementById('deptree-content');
        const badgeEl = document.getElementById('deptree-stats-badge');

        const inDeps = mod.inbound_dependents || [];
        const outDeps = mod.outbound_dependencies || [];
        const fns = mod.functions || [];
        const classes = mod.classes || [];

        badgeEl.textContent = `${inDeps.length} In / ${outDeps.length} Out`;

        let html = '';

        // Section 1: Inbound Dependents (Who calls/imports this file)
        html += `
          <div class="deptree-section">
            <div class="deptree-section-title">
              <span>📥 Inbound Dependents (${inDeps.length})</span>
            </div>
        `;
        if (inDeps.length === 0) {
          html += `<div style="color: var(--text-muted); font-size: 11px; padding-left: 8px;">No external modules import this file. (Root / Entry Candidate)</div>`;
        } else {
          inDeps.forEach(dep => {
            const symList = (dep.symbols && dep.symbols.length > 0)
              ? `Symbols: ${dep.symbols.join(', ')}`
              : 'Direct module import';
            
            const callLinks = (dep.calls || []).slice(0, 4).map(c => `
              <div class="deptree-call-item" onclick="event.stopPropagation(); window.selectModule('${dep.module}'); setTimeout(() => window.jumpToCodeLine(${c.line}), 150);">
                ➔ line ${c.line}: <code>${c.scope}()</code> calls <strong>${c.symbol || 'import'}</strong>
              </div>
            `).join('');

            html += `
              <div class="deptree-node" onclick="window.selectModule('${dep.module}')">
                <div class="deptree-node-top">
                  <span>📄 ${dep.module}</span>
                  <span style="color: var(--accent-blue); font-size: 10px;">Inspect ➔</span>
                </div>
                <div class="deptree-node-symbols">${symList}</div>
                ${callLinks}
              </div>
            `;
          });
        }
        html += `</div>`;

        // Section 2: Outbound Dependencies (Who this file imports)
        html += `
          <div class="deptree-section">
            <div class="deptree-section-title">
              <span>📤 Outbound Dependencies (${outDeps.length})</span>
            </div>
        `;
        if (outDeps.length === 0) {
          html += `<div style="color: var(--text-muted); font-size: 11px; padding-left: 8px;">Zero internal imports. (Pure Leaf Utility)</div>`;
        } else {
          outDeps.forEach(dep => {
            const symList = (dep.symbols && dep.symbols.length > 0)
              ? `Uses: ${dep.symbols.join(', ')}`
              : 'Direct module import';

            html += `
              <div class="deptree-node" onclick="window.selectModule('${dep.module}')">
                <div class="deptree-node-top">
                  <span>📄 ${dep.module}</span>
                  <span style="color: var(--accent-cyan); font-size: 10px;">Inspect ➔</span>
                </div>
                <div class="deptree-node-symbols">${symList}</div>
              </div>
            `;
          });
        }
        html += `</div>`;

        // Section 3: Intra-file Symbols & Hierarchy
        html += `
          <div class="deptree-section">
            <div class="deptree-section-title">
              <span>⚡ Declared Symbols & Methods (${fns.length + classes.length})</span>
            </div>
        `;
        if (classes.length > 0) {
          classes.forEach(c => {
            html += `
              <div style="font-family: 'Fira Code', monospace; font-size: 11px; color: var(--accent-purple); padding: 4px 8px; background: rgba(192, 132, 252, 0.08); border-radius: 4px; margin-bottom: 4px;">
                🏛️ class <strong>${c.name}</strong>
                ${(c.methods || []).map(m => `
                  <div style="padding-left: 14px; color: var(--text-secondary); font-size: 10px;">
                    • def ${m.name}${m.signature || '()'}
                  </div>
                `).join('')}
              </div>
            `;
          });
        }
        if (fns.length > 0) {
          fns.forEach(f => {
            html += `
              <div style="font-family: 'Fira Code', monospace; font-size: 11px; color: var(--accent-blue); padding: 4px 8px; background: rgba(56, 189, 248, 0.05); border-radius: 4px; margin-bottom: 2px;">
                ⚡ def <strong>${f.name}</strong>${f.signature || '()'}
              </div>
            `;
          });
        }
        if (classes.length === 0 && fns.length === 0) {
          html += `<div style="color: var(--text-muted); font-size: 11px; padding-left: 8px;">No top-level functions or classes declared.</div>`;
        }
        html += `</div>`;

        deptreeContent.innerHTML = html;
      }

      window.selectModule = function(modId, shouldSwitchTab = true) {
        if (shouldSwitchTab) {
          switchTab('code');
        }
        const mod = (data.modules || []).find(m => m.id === modId);
        if (!mod) return;

        // Tree active highlight
        document.querySelectorAll('.file-tree-item').forEach(el => el.classList.remove('active'));
        const activeTreeEl = document.getElementById(`tree-item-${modId.replace(/[^a-zA-Z0-9]/g, '_')}`);
        if (activeTreeEl) {
          activeTreeEl.classList.add('active');
          activeTreeEl.scrollIntoView({ block: 'nearest' });
        }

        document.getElementById('code-file-path').textContent = `${mod.path} (${mod.line_count} LOC • ${mod.role})`;
        document.getElementById('code-header-actions').innerHTML = `
          <button class="btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="window.jumpToGraphNode('${mod.id}')">View in Graph ➔</button>
        `;

        // Render middle pane: Code Dependency Tree
        renderCodeDependencyTree(mod);

        // Render right pane: Syntax Highlighted Code
        const codeContentEl = document.getElementById('code-viewer-content');
        if (mod.source_code) {
          codeContentEl.innerHTML = `<table class="code-table">${highlightPythonSyntax(mod.source_code)}</table>`;
        } else {
          codeContentEl.innerHTML = `
            <div style="padding: 20px;">
              <h3 style="color: #fff; margin-bottom: 12px;">Module Inspection: ${mod.path}</h3>
              <div class="stat-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 20px;">
                <div class="stat-card"><div class="stat-val">${mod.line_count}</div><div class="stat-lbl">Lines</div></div>
                <div class="stat-card"><div class="stat-val">${mod.function_count}</div><div class="stat-lbl">Functions</div></div>
                <div class="stat-card"><div class="stat-val">${mod.class_count}</div><div class="stat-lbl">Classes</div></div>
              </div>
            </div>
          `;
        }
      };

      // -------------------------------------------------------------
      // 5. Graph Explorer: Modules & Architecture Graph (vis.Network)
      // -------------------------------------------------------------
      let network = null;
      let currentLevel = 'modules';
      let activeRoleFilter = 'ALL';
      let selectedNodeId = null;

      const networkContainer = document.getElementById('network-canvas');
      const roleFilterGroup = document.getElementById('role-filter-group');

      function getNodeBorderColor(role) {
        if (role === 'BRIDGE') return '#f59e0b';
        if (role === 'HUB') return '#c084fc';
        if (role === 'LEAF') return '#10b981';
        if (role === 'CYCLE_MEMBER') return '#f43f5e';
        if (role === 'ENTRY_CANDIDATE') return '#22d3ee';
        return '#38bdf8';
      }

      function buildGraphDataSet(level) {
        const nodes = [];
        const edges = [];
        const filterCalls = document.getElementById('chk-filter-calls').checked;
        const filterImports = document.getElementById('chk-filter-imports').checked;
        const filterRefs = document.getElementById('chk-filter-refs').checked;

        if (level === 'modules') {
          (data.modules || []).forEach(m => {
            const isMatch = (activeRoleFilter === 'ALL' || m.role === activeRoleFilter);
            const bColor = getNodeBorderColor(m.role);

            nodes.push({
              id: `mod:${m.id}`,
              label: m.path.split('/').pop(),
              role: m.role,
              shape: 'box',
              color: isMatch ? {
                background: '#0f172a',
                border: bColor,
                highlight: { background: '#1e293b', border: '#fff' }
              } : {
                background: '#070c18',
                border: 'rgba(51, 65, 85, 0.25)',
                highlight: { background: '#0f172a', border: '#64748b' }
              },
              opacity: isMatch ? 1.0 : 0.14,
              font: {
                color: isMatch ? '#f8fafc' : 'rgba(100, 116, 139, 0.3)',
                face: 'Fira Code',
                size: 12
              },
              margin: 8,
              borderWidth: isMatch ? 1.8 : 1,
            });
          });

          (data.module_edges || []).forEach(e => {
            const types = e.relationship_types || {};
            const isCall = Boolean(types.CALL);
            const isImport = Boolean(types.IMPORT);
            const isRef = Boolean(types.REFERENCE);

            if ((isCall && filterCalls) || (isImport && filterImports) || (isRef && filterRefs) || (!isCall && !isImport && !isRef)) {
              const srcMod = (data.modules || []).find(m => m.id === e.source);
              const tgtMod = (data.modules || []).find(m => m.id === e.target);
              const edgeActive = (activeRoleFilter === 'ALL' || (srcMod && srcMod.role === activeRoleFilter) || (tgtMod && tgtMod.role === activeRoleFilter));

              edges.push({
                from: `mod:${e.source}`,
                to: `mod:${e.target}`,
                arrows: 'to',
                color: {
                  color: edgeActive ? 'rgba(56, 189, 248, 0.4)' : 'rgba(51, 65, 85, 0.08)',
                  highlight: '#38bdf8'
                },
                width: edgeActive ? Math.min(5, Math.max(1, e.weight || 1)) : 1,
              });
            }
          });

        } else if (level === 'architecture') {
          // Architecture Graph on vis.Network (same way as modules!)
          (data.components || []).forEach(c => {
            const modCount = (c.modules || []).length;
            nodes.push({
              id: `comp:${c.id}`,
              label: `🏛️ ${c.name}\n${modCount} module${modCount === 1 ? '' : 's'}`,
              shape: 'box',
              color: {
                background: '#0f172a',
                border: '#38bdf8',
                highlight: { background: '#1e293b', border: '#fff' }
              },
              font: {
                color: '#f8fafc',
                face: 'Fira Code',
                size: 13,
                bold: true
              },
              margin: 14,
              borderWidth: 2,
              shadow: {
                enabled: true,
                color: 'rgba(56, 189, 248, 0.25)',
                size: 10,
                x: 0,
                y: 2
              }
            });
          });

          (data.component_edges || []).forEach(e => {
            edges.push({
              from: `comp:${e.source}`,
              to: `comp:${e.target}`,
              arrows: 'to',
              label: e.weight > 1 ? `${e.weight} calls` : '',
              font: { color: '#94a3b8', size: 10, face: 'Fira Code' },
              color: {
                color: 'rgba(56, 189, 248, 0.45)',
                highlight: '#38bdf8'
              },
              width: Math.min(6, Math.max(1.5, Math.log2(e.weight + 1) * 2)),
              smooth: { type: 'cubicBezier', roundness: 0.2 }
            });
          });
        }

        return { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
      }

      function initOrFitNetwork() {
        networkContainer.style.display = 'block';
        roleFilterGroup.style.display = (currentLevel === 'modules') ? 'flex' : 'none';

        if (!network) {
          const graphData = buildGraphDataSet(currentLevel);
          const options = {
            physics: {
              solver: 'forceAtlas2Based',
              forceAtlas2Based: {
                gravitationalConstant: -42,
                centralGravity: 0.01,
                springLength: 100,
                springConstant: 0.08,
              },
              stabilization: { iterations: 100 },
            },
            interaction: {
              hover: true,
              tooltipDelay: 100,
              zoomView: true,
              dragView: true,
            },
          };
          network = new vis.Network(networkContainer, graphData, options);
          setTimeout(() => {
            if (network) {
              network.setSize('100%', '100%');
              network.redraw();
              network.fit();
            }
          }, 80);

          // Click: Unrelated node greying
          network.on('click', function(params) {
            if (params.nodes.length > 0) {
              const clickedId = params.nodes[0];
              selectedNodeId = clickedId;
              applyUnrelatedNodeGreying(clickedId);
              onCanvasNodeSelected(clickedId);
            } else {
              selectedNodeId = null;
              if (currentLevel === 'modules') {
                applyRoleFilter(activeRoleFilter);
              } else {
                updateNetworkData();
              }
            }
          });

          // Double Click: Jump to source tree or inspect component!
          network.on('doubleClick', function(params) {
            if (params.nodes.length > 0) {
              const clickedId = params.nodes[0];
              if (clickedId.startsWith('mod:')) {
                const modId = clickedId.replace('mod:', '');
                window.selectModule(modId);
              } else if (clickedId.startsWith('comp:')) {
                const compId = clickedId.replace('comp:', '');
                const comp = (data.components || []).find(c => c.id === compId);
                if (comp && comp.modules && comp.modules.length > 0) {
                  window.selectModule(comp.modules[0]);
                }
              }
            }
          });
        } else {
          updateNetworkData();
          network.setSize('100%', '100%');
          network.redraw();
          network.fit({ animation: { duration: 300 } });
        }
      }

      function updateNetworkData() {
        if (!network) return;
        const gd = buildGraphDataSet(currentLevel);
        network.setData(gd);
      }

      // Role filter with dynamic greying out
      function applyRoleFilter(role) {
        activeRoleFilter = role;
        document.querySelectorAll('#role-filter-group .role-btn').forEach(btn => {
          btn.classList.toggle('active', btn.dataset.role === role);
        });
        updateNetworkData();
      }

      document.querySelectorAll('#role-filter-group .role-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          applyRoleFilter(this.dataset.role);
        });
      });

      function applyUnrelatedNodeGreying(focusNodeId) {
        if (!network) return;
        const connectedNodes = new Set(network.getConnectedNodes(focusNodeId));
        connectedNodes.add(focusNodeId);

        const allNodes = network.body.data.nodes.get();
        const updates = allNodes.map(n => {
          if (connectedNodes.has(n.id)) {
            return { id: n.id, opacity: 1.0 };
          } else {
            return { id: n.id, opacity: 0.12 };
          }
        });
        network.body.data.nodes.update(updates);
      }

      function onCanvasNodeSelected(nodeId) {
        const inspTitle = document.getElementById('insp-title');
        const inspSub = document.getElementById('insp-sub');
        const inspBody = document.getElementById('insp-body');

        if (nodeId.startsWith('mod:')) {
          const mId = nodeId.replace('mod:', '');
          const mod = (data.modules || []).find(m => m.id === mId);
          if (!mod) return;

          inspTitle.textContent = `📄 ${mod.name}`;
          inspSub.textContent = mod.path;
          inspBody.innerHTML = `
            <div class="inspector-prop"><span class="lbl">Component</span><span class="val">${mod.component_name}</span></div>
            <div class="inspector-prop"><span class="lbl">Role</span><span class="val">${mod.role}</span></div>
            <div class="inspector-prop"><span class="lbl">Lines</span><span class="val">${mod.line_count}</span></div>
            <div class="inspector-prop"><span class="lbl">Inbound / Outbound</span><span class="val">${(mod.inbound_dependents || []).length} / ${(mod.outbound_dependencies || []).length}</span></div>
            <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 8px;">
              <button class="btn-primary" style="width: 100%; justify-content: center;" onclick="window.selectModule('${mId}')">Explore Source Code ➔</button>
            </div>
          `;
        } else if (nodeId.startsWith('comp:')) {
          const cId = nodeId.replace('comp:', '');
          const comp = (data.components || []).find(c => c.id === cId);
          if (!comp) return;

          inspTitle.textContent = `🏛️ ${comp.name}`;
          inspSub.textContent = `Architectural Subsystem • ${(comp.modules || []).length} Modules`;

          let modHtml = (comp.modules || []).map(m => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0; border-bottom:1px solid rgba(51,65,85,0.2);">
              <span style="font-family:'Fira Code'; font-size:11px; color:#e2e8f0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">${m.split('/').pop()}</span>
              <button class="btn-secondary" style="padding:2px 6px; font-size:10px;" onclick="window.selectModule('${m}')">Code ➔</button>
            </div>
          `).join('');

          inspBody.innerHTML = `
            <div class="inspector-prop"><span class="lbl">Subsystem ID</span><span class="val">${comp.id}</span></div>
            <div class="inspector-prop"><span class="lbl">Confidence</span><span class="val">${Math.round((comp.confidence || 0.9) * 100)}%</span></div>
            <div class="inspector-prop"><span class="lbl">Discovery</span><span class="val">${(comp.evidence || []).join(', ') || 'DeepWiki'}</span></div>
            <div style="margin-top:14px; margin-bottom:6px; font-size:11px; font-weight:700; color:var(--accent-blue); text-transform:uppercase;">Constituent Modules (${(comp.modules || []).length})</div>
            <div style="max-height:160px; overflow-y:auto; margin-bottom:14px; padding-right:4px;">${modHtml || '<div style="color:var(--text-muted); font-size:11px;">None</div>'}</div>
            <div style="display:flex; flex-direction:column; gap:8px;">
              <button class="btn-primary" style="width:100%; justify-content:center;" onclick="window.filterModulesToComponent('${comp.id}')">Filter Module Graph ➔</button>
            </div>
          `;
        }
      }

      window.filterModulesToComponent = function(compId) {
        currentLevel = 'modules';
        document.querySelectorAll('#graph-level-pills .pill-opt').forEach(p => p.classList.toggle('active', p.dataset.level === 'modules'));
        roleFilterGroup.style.display = 'flex';
        updateNetworkData();
        const comp = (data.components || []).find(c => c.id === compId);
        if (comp && comp.modules && comp.modules.length > 0) {
          setTimeout(() => {
            if (network) {
              const nodeIds = comp.modules.map(m => `mod:${m}`);
              network.fit({ nodes: nodeIds, animation: { duration: 300 } });
            }
          }, 100);
        }
      };

      // Graph Explorer Level Switcher
      document.querySelectorAll('#graph-level-pills .pill-opt').forEach(pill => {
        pill.addEventListener('click', function() {
          document.querySelectorAll('#graph-level-pills .pill-opt').forEach(p => p.classList.remove('active'));
          this.classList.add('active');
          currentLevel = this.dataset.level;
          initOrFitNetwork();
        });
      });

      // Checkbox edge filters
      ['chk-filter-calls', 'chk-filter-imports', 'chk-filter-refs'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
          updateNetworkData();
        });
      });

      window.jumpToGraphNode = function(modId) {
        switchTab('graph');
        currentLevel = 'modules';
        document.querySelectorAll('#graph-level-pills .pill-opt').forEach(p => p.classList.toggle('active', p.dataset.level === 'modules'));
        roleFilterGroup.style.display = 'flex';
        initOrFitNetwork();
        setTimeout(() => {
          if (network) {
            network.focus(`mod:${modId}`, { scale: 1.2, animation: { duration: 400 } });
            network.selectNodes([`mod:${modId}`]);
            applyUnrelatedNodeGreying(`mod:${modId}`);
            onCanvasNodeSelected(`mod:${modId}`);
          }
        }, 200);
      };

      window.inspectComponent = function(compId) {
        switchTab('graph');
        currentLevel = 'architecture';
        document.querySelectorAll('#graph-level-pills .pill-opt').forEach(p => p.classList.toggle('active', p.dataset.level === 'architecture'));
        initOrFitNetwork();
        setTimeout(() => {
          if (network) {
            const nodeId = `comp:${compId}`;
            network.focus(nodeId, { scale: 1.2, animation: { duration: 400 } });
            network.selectNodes([nodeId]);
            applyUnrelatedNodeGreying(nodeId);
            onCanvasNodeSelected(nodeId);
          }
        }, 200);
      };

      // -------------------------------------------------------------
      // DeepWiki Architecture Wiki Viewer & Provider Config
      // -------------------------------------------------------------
      function renderDeepWikiView() {
        const currentModelEl = document.getElementById('deepwiki-current-model');
        const providerName = data.ai_provider || 'Gemini';
        const modelName = data.ai_model || 'gemini-2.5-flash';
        if (currentModelEl) {
          currentModelEl.textContent = `AI Provider: ${providerName.toUpperCase()} (${modelName})`;
        }

        const navTreeEl = document.getElementById('deepwiki-nav-tree');
        const pageViewEl = document.getElementById('deepwiki-page-view');
        const structure = data.wiki_structure || null;
        const pages = data.wiki_pages || {};

        if (!structure || !structure.pages || structure.pages.length === 0) {
          if (pageViewEl) {
            pageViewEl.innerHTML = renderMarkdown(data.documentation_md || '# Architecture Documentation');
          }
          if (navTreeEl) {
            navTreeEl.innerHTML = '<div style="padding:10px; color:var(--text-muted); font-size:12px;">Architecture Guide</div>';
          }
          return;
        }

        let navHtml = '';
        const sections = structure.sections || [];
        const renderedPageIds = new Set();

        sections.forEach(sec => {
          navHtml += `<div class="deepwiki-nav-section-title">${sec.title}</div>`;
          (sec.pages || []).forEach(pid => {
            renderedPageIds.add(pid);
            const page = pages[pid] || structure.pages.find(p => p.id === pid);
            if (page) {
              navHtml += `
                <div class="deepwiki-nav-item" data-page-id="${page.id}" id="nav-item-${page.id}">
                  <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">${page.title}</span>
                  ${page.importance === 'high' ? '<span class="deepwiki-pill-high">Core</span>' : ''}
                </div>
              `;
            }
          });
        });

        (structure.pages || []).forEach(page => {
          if (!renderedPageIds.has(page.id)) {
            navHtml += `
              <div class="deepwiki-nav-item" data-page-id="${page.id}" id="nav-item-${page.id}">
                <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">${page.title}</span>
              </div>
            `;
          }
        });

        navTreeEl.innerHTML = navHtml;

        window.selectDeepWikiPage = function(pageId) {
          document.querySelectorAll('.deepwiki-nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.pageId === pageId);
          });
          const page = pages[pageId] || structure.pages.find(p => p.id === pageId);
          if (page) {
            pageViewEl.innerHTML = renderMarkdown(page.content || `# ${page.title}\n*(Content empty)*`);
            pageViewEl.scrollTop = 0;
          }
        };

        document.querySelectorAll('.deepwiki-nav-item').forEach(item => {
          item.addEventListener('click', function() {
            window.selectDeepWikiPage(this.dataset.pageId);
          });
        });

        if (structure.pages.length > 0) {
          window.selectDeepWikiPage(structure.pages[0].id);
        }
      }

      // Handle interactive code citation jumps: #code:path:line
      document.addEventListener('click', function(e) {
        const link = e.target.closest('a');
        if (link && link.getAttribute('href')) {
          const href = link.getAttribute('href');
          if (href.startsWith('#code:')) {
            e.preventDefault();
            const rest = href.replace('#code:', '');
            const parts = rest.split(':');
            const path = parts[0];
            const lineRange = parts[1] || '';
            const startLine = parseInt(lineRange.split('-')[0], 10);

            // Switch to Code tab
            switchTab('code');

            const matchedMod = (data.modules || []).find(m => m.path === path || m.path.endsWith(path) || path.endsWith(m.path));
            if (matchedMod) {
              window.selectModule(matchedMod.id);
              if (!isNaN(startLine)) {
                setTimeout(() => window.jumpToCodeLine(startLine), 180);
              }
            }
          }
        }
      });

      // Provider Config Modal Controls
      const providerModal = document.getElementById('provider-modal');
      const btnOpenModal = document.getElementById('btn-open-provider-modal');
      const btnCloseModal = document.getElementById('btn-close-modal');
      const btnCancelModal = document.getElementById('btn-cancel-modal');
      const btnSaveModal = document.getElementById('btn-save-modal');

      if (btnOpenModal) {
        btnOpenModal.addEventListener('click', () => {
          if (providerModal) providerModal.style.display = 'flex';
        });
      }
      if (btnCloseModal) {
        btnCloseModal.addEventListener('click', () => {
          if (providerModal) providerModal.style.display = 'none';
        });
      }
      if (btnCancelModal) {
        btnCancelModal.addEventListener('click', () => {
          if (providerModal) providerModal.style.display = 'none';
        });
      }
      if (btnSaveModal) {
        btnSaveModal.addEventListener('click', () => {
          const p = document.getElementById('cfg-provider-select').value;
          const m = document.getElementById('cfg-model-input').value;
          const k = document.getElementById('cfg-apikey-input').value;
          const b = document.getElementById('cfg-baseurl-input').value;
          alert(`Configuration saved for ${p.toUpperCase()} (${m || 'default'}). You can re-run 'karuvi <repo> --architecture --provider ${p}' to regenerate.`);
          if (providerModal) providerModal.style.display = 'none';
        });
      }

      // -------------------------------------------------------------
      // Global Search Modal (Cmd+K)
      // -------------------------------------------------------------
      const searchModal = document.getElementById('search-modal-overlay');
      const searchInput = document.getElementById('global-search-input');
      const searchResultsList = document.getElementById('search-results-list');

      function openSearch() {
        searchModal.classList.add('active');
        searchInput.value = '';
        searchInput.focus();
        runSearch('');
      }

      function closeSearch() {
        searchModal.classList.remove('active');
      }

      document.getElementById('btn-open-search').addEventListener('click', openSearch);
      searchModal.addEventListener('click', e => {
        if (e.target === searchModal) closeSearch();
      });

      window.addEventListener('keydown', e => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          openSearch();
        } else if (e.key === 'Escape') {
          closeSearch();
        }
      });

      searchInput.addEventListener('input', e => runSearch(e.target.value));

      function runSearch(query) {
        const q = query.trim().toLowerCase();
        const results = [];

        (data.components || []).forEach(c => {
          if (!q || c.name.toLowerCase().includes(q)) {
            results.push({
              type: 'Component',
              label: `🏛️ ${c.name}`,
              sub: `${c.modules.length} modules (${c.role})`,
              action: () => { closeSearch(); window.inspectComponent(c.id); }
            });
          }
        });

        (data.modules || []).forEach(m => {
          if (!q || m.path.toLowerCase().includes(q) || m.role.toLowerCase().includes(q)) {
            results.push({
              type: 'Module',
              label: `📄 ${m.name}`,
              sub: `${m.path} (${m.role})`,
              action: () => { closeSearch(); window.selectModule(m.id); }
            });
          }
          (m.functions || []).forEach(f => {
            if (q && f.name.toLowerCase().includes(q)) {
              results.push({
                type: 'Function',
                label: `⚡ ${f.name}()`,
                sub: `in ${m.path}`,
                action: () => { closeSearch(); window.selectModule(m.id); }
              });
            }
          });
        });

        if (results.length === 0) {
          searchResultsList.innerHTML = `<div style="padding: 16px; color: var(--text-muted); font-size: 13px;">No results found for "${query}"</div>`;
          return;
        }

        searchResultsList.innerHTML = results.slice(0, 15).map((r, i) => `
          <div class="search-item" id="search-res-${i}">
            <div>
              <div style="font-size: 13px; font-weight: 600; color: #fff;">${r.label}</div>
              <div style="font-size: 11px; color: var(--text-muted); font-family: 'Fira Code', monospace;">${r.sub}</div>
            </div>
            <span class="badge" style="background: rgba(255, 255, 255, 0.08);">${r.type}</span>
          </div>
        `).join('');

        results.slice(0, 15).forEach((r, i) => {
          document.getElementById(`search-res-${i}`).onclick = r.action;
        });
      }

      function renderMarkdown(md) {
        if (!md) return '';
        // 1. Protect details blocks
        const detailsBlocks = [];
        let text = md.replace(/<details[\s\S]*?<\/details>/gi, match => {
          detailsBlocks.push(match);
          return `%%DETAILS_${detailsBlocks.length - 1}%%`;
        });

        // 2. Protect multi-line code blocks
        const codeBlocks = [];
        text = text.replace(/```([a-zA-Z0-9_\-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
          codeBlocks.push(`<pre style="background:#070c18; border:1px solid #1e293b; padding:12px; border-radius:6px; overflow-x:auto; font-family:'Fira Code', monospace; font-size:12px; color:#38bdf8; margin: 12px 0;"><code>${code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`);
          return `%%CODEBLOCK_${codeBlocks.length - 1}%%`;
        });

        // 3. Convert markdown tables
        text = text.replace(/(?:^|\n)(\|.+?\|\n\|[-: |]+\|\n(?:\|.+?\|\n?)+)/g, match => {
          const lines = match.trim().split('\n');
          if (lines.length < 3) return match;
          const headers = lines[0].split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
          const rows = lines.slice(2).map(r => {
            const cells = r.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('');
            return `<tr>${cells}</tr>`;
          }).join('');
          return `\n<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>\n`;
        });

        // 4. Escape general HTML except recognized tags
        let escaped = text
          .replace(/&(?!amp;|lt;|gt;|quot;|apos;|#)/g, '&amp;')
          .replace(/<(?!\/?(table|thead|tbody|tr|th|td|pre|code|details|summary|span|div|a|h1|h2|h3|h4|strong|em|li|br|ul)\b)/gi, '&lt;');

        escaped = escaped.replace(/^#### (.*$)/gim, '<h4 style="color: var(--text-primary); font-size: 13px; margin: 14px 0 6px 0; font-weight:700;">$1</h4>');
        escaped = escaped.replace(/^### (.*$)/gim, '<h3 style="color: var(--accent-cyan); font-size: 15px; margin: 18px 0 8px 0;">$1</h3>');
        escaped = escaped.replace(/^## (.*$)/gim, '<h2 style="color: #fff; font-size: 18px; margin: 24px 0 12px 0; border-bottom: 1px solid var(--border); padding-bottom: 6px;">$1</h2>');
        escaped = escaped.replace(/^# (.*$)/gim, '<h1 style="color: #fff; font-size: 24px; margin-bottom: 16px;">$1</h1>');
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        escaped = escaped.replace(/`([^`]+)`/g, '<code style="background: var(--bg-card); color: var(--accent-cyan); padding: 2px 6px; border-radius: 4px; font-family: \'Fira Code\', monospace; font-size: 12px;">$1</code>');
        escaped = escaped.replace(/^- (.*$)/gim, '<li style="margin-left: 20px; color: var(--text-secondary); margin-bottom: 4px;">$1</li>');
        
        // Markdown Links: [label](url)
        escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color: var(--accent-blue); text-decoration: none; border-bottom: 1px dashed var(--accent-blue); font-weight: 500;">$1</a>');

        // Restore protected blocks
        codeBlocks.forEach((b, i) => {
          escaped = escaped.replace(`%%CODEBLOCK_${i}%%`, b);
        });
        detailsBlocks.forEach((d, i) => {
          escaped = escaped.replace(`%%DETAILS_${i}%%`, d);
        });

        escaped = escaped.replace(/\n\n/g, '<br><br>');
        return escaped;
      }

      // Initial Selection: First module in tree
      if ((data.modules || []).length > 0) {
        const initialMod = (data.entry_points && data.entry_points.length > 0)
          ? data.entry_points[0].module
          : data.modules[0].id;
        window.selectModule(initialMod, false);
      }
    });
  </script>

  <!-- AI Provider & Model Config Modal -->
  <div id="provider-modal" class="modal-backdrop" style="display: none;">
    <div class="modal-card">
      <div class="modal-header">
        <span style="font-weight: 700; font-size: 14px; color: #fff;">⚙️ DeepWiki AI Provider Configuration</span>
        <button class="modal-close" id="btn-close-modal">&times;</button>
      </div>
      <div class="modal-body">
        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 16px; line-height: 1.5;">
          Configure your AI model and provider of choice to generate architecture documentation for this local repository.
        </div>
        <div class="form-group">
          <label class="form-lbl">AI Provider</label>
          <select id="cfg-provider-select" class="form-input">
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI</option>
            <option value="openrouter">OpenRouter</option>
            <option value="ollama">Ollama (Local Offline)</option>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="custom">Custom (OpenAI-compatible / vLLM)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-lbl">Model Name</label>
          <input type="text" id="cfg-model-input" class="form-input" placeholder="e.g. gemini-2.5-flash, gpt-4o, llama3.1">
        </div>
        <div class="form-group" id="grp-api-key">
          <label class="form-lbl">API Key (optional if set in environment)</label>
          <input type="password" id="cfg-apikey-input" class="form-input" placeholder="Enter API Key">
        </div>
        <div class="form-group" id="grp-base-url">
          <label class="form-lbl">Endpoint URL (for Ollama / custom)</label>
          <input type="text" id="cfg-baseurl-input" class="form-input" placeholder="e.g. http://localhost:11434">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" id="btn-cancel-modal">Cancel</button>
        <button class="btn-primary" id="btn-save-modal">Save & Close</button>
      </div>
    </div>
  </div>
</body>
</html>
"""
