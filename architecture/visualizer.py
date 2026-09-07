"""
Karuvi Living Codebase Atlas — Unified Web Visualizer
========================================================================

Generates a standalone, interactive, dark-mode Single Page Web Application
embodying Karuvi's 6 core modes:
1. Overview: Executive codebase dashboard, vital metrics, and circular loop radar.
3. Architecture: Discovered components, confidence scores, and architectural flows.
4. Graph Explorer: Progressive graph disclosure, relation filters, and unrelated node greying.
5. Code Explorer: Sourcetrail-grade side-by-side file tree and syntax-highlighted code viewer.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from architecture.analyzer import ArchitectureAnalyzer
from architecture.documentation import generate_architecture_markdown
from architecture.models import ArchitectureModel
from architecture.module_graph import normalize_module_path


def build_unified_payload(
    repo_builder: Any,
    arch_model: ArchitectureModel | None = None,
) -> dict[str, Any]:
    """
    Assembles a unified data contract combining Stage 1 (AST, symbols, references, cycles)
    and Stage 2 (components, module graph, metrics, roles, entrypoints, flows, onboarding).
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

    # 2. Module list with enhanced architectural metadata and source code
    raw_nodes = getattr(repo_builder, "nodes", {}) or {}
    normalized_nodes = {
        normalize_module_path(k, repo_root): v for k, v in raw_nodes.items()
    }

    modules_list = []
    for mod_id, mod in arch_model.modules.items():
        node_raw = normalized_nodes.get(mod_id)
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

        # Read source code from disk (up to 200KB)
        source_code = ""
        try:
            full_p = Path(mod.path)
            if not full_p.is_absolute():
                full_p = repo_root / full_p
            if full_p.exists() and full_p.is_file() and full_p.stat().st_size <= 250_000:
                source_code = full_p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            source_code = ""

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
        })

    # 3. Component Graph Edges
    comp_edges = []
    if arch_model.component_graph is not None:
        for u, v, d in arch_model.component_graph.edges(data=True):
            comp_edges.append({
                "source": str(u),
                "target": str(v),
                "weight": d.get("weight", 1),
                "relationship_types": d.get("relationship_types", {}),
            })

    # 4. Module Graph Edges
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

    # 5. Raw Symbol References & Cycles
    cross_refs = getattr(repo_builder, "cross_references", [])
    cycles = getattr(repo_builder, "cycles", [])

    # 6. Overall Stats
    comp_nodes_in_graph = set()
    for edge in comp_edges:
        comp_nodes_in_graph.add(edge["source"])
        comp_nodes_in_graph.add(edge["target"])
    singleton_comps = [
        c for c in components_list
        if len(c.get("modules", [])) == 1 and c["id"] not in comp_nodes_in_graph
    ]
    multi_comps = [
        c for c in components_list if c not in singleton_comps
    ]
    stats = {
        "total_modules": len(modules_list),
        "total_components": len(components_list),
        "total_singleton_components": len(singleton_comps),
        "total_multi_components": len(multi_comps),
        "total_symbols": sum(m["function_count"] + m["class_count"] + m["variable_count"] for m in modules_list),
        "total_lines": sum(m["line_count"] for m in modules_list),
        "total_module_edges": len(mod_edges),
        "total_component_edges": len(comp_edges),
        "total_edges": len(mod_edges),
        "total_cross_references": len(cross_refs),
        "total_cycles": len(cycles),
        "circular_dependencies": len(cycles),
    }

    # 9. Precomputed Markdown Documentation
    doc_markdown = generate_architecture_markdown(arch_model)

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


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Karuvi — Living Codebase Atlas</title>
  <!-- Google Fonts & Vis-Network -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js"></script>
  <style>
    :root {
      /* Minimalist Monochrome Dark Base */
      --bg-canvas: #121212;
      --bg-surface: #1e1e1e;
      --bg-card: #252525;
      --bg-card-hover: #2e2e2e;
      --border: #333333;
      --border-subtle: #222222;
      --border-glow: transparent;
      
      --text: #eeeeee;
      --text-secondary: #a0a0a0;
      --text-muted: #777777;
      --text-heading: #ffffff;
      
      /* Maintained Graph Colors */
      --accent-blue: #b8b8b8;
      --accent-cyan: #c4c4c4;
      --accent-purple: #a0a0a0;
      --accent-green: #b0b0b0;
      --accent-amber: #969696;
      --accent-rose: #7a7a7a;
      
      --role-entry: #b8b8b8;
      --role-bridge: #969696;
      --role-hub: #a0a0a0;
      --role-leaf: #b0b0b0;
      --role-cycle: #7a7a7a;
      --role-isolated: #777777;
      
      /* Shadows for elevation */
      --shadow-1: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
      --shadow-2: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
      
      /* Typography */
      --font-display: 'Inter', system-ui, sans-serif;
      --font-body: 'Inter', system-ui, sans-serif;
      --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-canvas);
      color: var(--text);
      font-family: var(--font-body);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* Top App Bar */
    header {
      height: 52px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      flex-shrink: 0;
      z-index: 100;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-logo {
      font-weight: 700; font-family: var(--font-display);
      font-size: 17px;
      letter-spacing: -0.5px;
      color: var(--text-heading);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .repo-pill {
      background: var(--bg-card);
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 6px;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      color: var(--accent-blue);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .search-trigger-btn {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      font-size: 12px;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
    }
    .search-trigger-btn:hover {
      border-color: var(--accent-blue);
      color: var(--text);
    }
    .kbd-shortcut {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 10px;
      font-family: 'Fira Code', monospace;
    }

    /* Main App Layout */
    .app-container {
      display: flex;
      flex: 1;
      overflow: hidden;
      position: relative;
    }

    /* Left Navigation Sidebar */
    nav.sidebar {
      width: 220px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      padding: 14px 8px;
    }

    .nav-section-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      padding: 6px 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 12px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;
      margin-bottom: 2px;
      user-select: none;
    }

    .nav-item:hover {
      background: var(--bg-card);
      color: var(--text);
    }

    .nav-item.active {
      background: var(--bg-card);
      color: #fff;
      font-weight: 600;
      box-shadow: inset 3px 0 0 var(--accent-blue);
    }

    .nav-item .icon {
      font-size: 15px;
      width: 18px;
      text-align: center;
    }

    .sidebar-footer {
      margin-top: auto;
      padding: 12px;
      border-top: 1px solid var(--border-subtle);
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    /* Workspace Content Panels */
    main.workspace {
      flex: 1;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
    }

    .tab-view {
      display: none;
      width: 100%;
      height: 100%;
      overflow-y: auto;
      padding: 24px 32px;
    }

    .tab-view.active {
      display: block;
    }

    /* Common Card Styles */
    .overview-hero {
      margin-bottom: 24px;
    }

    .overview-hero h1 {
      font-size: 26px;
      font-weight: 700;
      letter-spacing: -0.5px;
      margin-bottom: 6px;
    }

    .overview-hero p {
      font-size: 14px;
      color: var(--text-secondary);
    }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 28px;
    }

    .stat-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .stat-card:hover {
      border-color: var(--border-glow);
    }

    .stat-val {
      font-size: 24px;
      font-weight: 700; font-family: var(--font-display);
      font-family: 'Fira Code', monospace;
      color: var(--accent-blue);
    }

    .stat-lbl {
      font-size: 12px;
      color: var(--text-secondary);
      font-weight: 500;
    }

    /* Entry Point Banner */
    .banner-entrypoint {
      background: linear-gradient(135deg, rgba(184,184,184,0.08) 0%, rgba(160,160,160,0.08) 100%);
      border: 1px solid rgba(184,184,184,0.25);
      border-radius: 10px;
      padding: 18px 22px;
      margin-bottom: 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }

    .banner-content h3 {
      font-size: 15px;
      font-weight: 700;
      color: var(--accent-blue);
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .banner-content .mod-title {
      font-family: 'Fira Code', monospace;
      font-size: 15px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 4px;
    }

    .banner-content p {
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.5;
    }

    .btn-primary {
      background: var(--accent-blue);
      color: #090d16;
      border: none;
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }

    .btn-primary:hover {
      background: #d0d0d0;
      transform: translateY(-1px);
    }

    .btn-secondary {
      background: var(--bg-card);
      color: var(--text);
      border: 1px solid var(--border);
      font-size: 13px;
      font-weight: 500;
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .btn-secondary:hover {
      border-color: var(--accent-blue);
      background: var(--bg-card-hover);
    }

    .section-title {
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* Radar / Alert Cards */
    .alert-card {
      background: rgba(120,120,120,0.08);
      border: 1px solid rgba(120,120,120,0.3);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 24px;
      font-size: 13px;
      line-height: 1.6;
    }
    .alert-card.warning {
      background: rgba(150,150,150,0.08);
      border-color: rgba(150,150,150,0.3);
      color: #c8c8c8;
    }

    /* Architecture Components Grid */
    .comp-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .comp-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .comp-card:hover {
      border-color: var(--accent-blue);
      background: var(--bg-card);
      transform: translateY(-2px);
    }

    .comp-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .comp-name {
      font-size: 15px;
      font-weight: 700;
    }

    .confidence-badge {
      font-size: 10px;
      padding: 2px 7px;
      border-radius: 4px;
      font-family: 'Fira Code', monospace;
      font-weight: 600;
    }
    .confidence-high { background: rgba(176,176,176,0.15); color: var(--accent-green); border: 1px solid rgba(176,176,176,0.3); }
    .confidence-med { background: rgba(150,150,150,0.15); color: var(--accent-amber); border: 1px solid rgba(150,150,150,0.3); }
    .confidence-low { background: rgba(120,120,120,0.15); color: var(--accent-rose); border: 1px solid rgba(120,120,120,0.3); }

    .comp-modules-list {
      font-size: 11px;
      color: var(--text-muted);
      font-family: 'Fira Code', monospace;
      line-height: 1.6;
    }

    /* Architecture panel chrome */
    .arch-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 8px;
    }
    .arch-actions { display: flex; gap: 8px; flex-shrink: 0; }
    .arch-summary {
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 18px;
    }
    .arch-legend {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 28px;
      font-size: 12px;
      color: var(--text-secondary);
    }
    .legend-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px 20px;
    }
    .legend-grid strong {
      color: #e5e5e5;
      font-family: 'Fira Code', monospace;
      font-size: 11px;
    }

    .comp-sublabel {
      font-size: 11px;
      color: var(--accent-blue);
      font-family: 'Fira Code', monospace;
      opacity: 0.85;
      margin-top: -4px;
    }
    .cohesion-badge {
      font-size: 10px;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid;
      font-family: 'Fira Code', monospace;
      font-weight: 600;
      background: rgba(0, 0, 0, 0.25);
    }
    .cohesion-track {
      height: 4px;
      border-radius: 2px;
      background: rgba(255, 255, 255, 0.08);
      overflow: hidden;
    }
    .cohesion-fill { height: 100%; border-radius: 2px; opacity: 0.9; }
    .comp-why { color: var(--accent-blue); }
    .comp-conn { font-size: 11px; color: var(--text-muted); }
    .comp-chip {
      display: inline-block;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 4px;
      padding: 1px 6px;
      margin: 2px 2px 0 0;
      color: var(--text-secondary);
      font-size: 10.5px;
    }

    .singleton-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 32px;
    }
    .singleton-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 9px 14px;
      cursor: pointer;
      font-size: 12px;
      transition: all 0.15s ease;
    }
    .singleton-item:hover { border-color: var(--accent-blue); background: var(--bg-card); }
    .singleton-name { font-weight: 600; color: #ddd; font-family: 'Fira Code', monospace; font-size: 11.5px; }
    .singleton-mods { color: var(--text-muted); font-family: 'Fira Code', monospace; font-size: 11px; text-align: right; }

    /* Flows */
    .flow-role {
      flex-shrink: 0;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 4px;
      border: 1px solid;
    }
    .role-entry { color: var(--accent-blue); border-color: var(--accent-blue); background: rgba(56,189,248,0.08); }
    .role-leaf { color: var(--accent-green); border-color: var(--accent-green); background: rgba(16,185,129,0.08); }
    .role-cycle { color: var(--accent-rose); border-color: var(--accent-rose); background: rgba(244,63,94,0.08); }
    .flow-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
    .flow-algo { font-size: 10px; color: var(--text-muted); font-family: 'Fira Code', monospace; }

    /* Flows */
    .flows-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 32px;
    }

    .flow-row {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 18px;
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .flow-row:hover { border-color: var(--accent-blue); background: var(--bg-card); }

    .flow-node-badge {
      background: var(--bg-card);
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 6px;
      font-family: 'Fira Code', monospace;
      font-weight: 600;
      color: var(--accent-blue);
    }

    .flow-arrow {
      color: var(--text-muted);
      font-weight: bold;
    }

    /* ONBOARDING TAB */
    #tab-onboard {
      padding: 20px 28px;
    }

    .onboard-layout {
      display: flex;
      gap: 24px;
      height: calc(100vh - 96px);
    }

    .onboard-sidebar {
      width: 320px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      flex-shrink: 0;
    }

    .onboard-sidebar-header {
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .onboard-sidebar-header h2 {
      font-size: 14px;
      font-weight: 700;
    }

    .onboard-sidebar-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
    }

    .step-item-card {
      padding: 10px 14px;
      border-radius: 6px;
      margin-bottom: 6px;
      cursor: pointer;
      border: 1px solid transparent;
      display: flex;
      flex-direction: column;
      gap: 4px;
      transition: all 0.15s ease;
    }

    .step-item-card:hover {
      background: var(--bg-card);
    }

    .step-item-card.active {
      background: var(--bg-card);
      border-color: var(--accent-blue);
      box-shadow: 0 0 10px rgba(184,184,184,0.15);
    }

    .step-item-card.completed .step-title-text {
      color: var(--accent-green);
    }

    .step-num-badge {
      font-size: 10px;
      font-weight: 700;
      font-family: 'Fira Code', monospace;
      color: var(--text-muted);
    }

    .step-title-text {
      font-size: 13px;
      font-weight: 600;
      color: var(--text);
    }

    .onboard-main {
      flex: 1;
      overflow-y: auto;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 24px 32px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .complexity-selector {
      display: flex;
      gap: 6px;
      background: var(--bg-canvas);
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--border);
      width: fit-content;
    }

    .complexity-btn {
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      border: none;
      background: transparent;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .complexity-btn.active {
      background: var(--bg-card);
      color: var(--accent-blue);
      box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }

    .pill-tag {
      background: var(--bg-card);
      border: 1px solid var(--border);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      color: var(--text-secondary);
      font-family: 'Fira Code', monospace;
    }

    /* GRAPH EXPLORER TAB */
    #tab-graph {
      padding: 0;
      height: 100%;
      overflow: hidden;
    }

    .graph-layout {
      display: flex;
      width: 100%;
      height: 100%;
      position: relative;
    }

    .graph-canvas-container {
      flex: 1;
      height: 100%;
      position: relative;
      background: radial-gradient(circle at center, #111827 0%, #090d16 100%);
    }

    #network-canvas {
      width: 100%;
      height: 100%;
    }

    .graph-floating-controls {
      position: absolute;
      top: 14px;
      left: 16px;
      z-index: 10;
      display: flex;
      gap: 12px;
      align-items: center;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 6px 12px;
    }

    .vis-controls { position: relative; }
    .vis-toolbar { display: flex; align-items: center; gap: 8px; }
    .btn-sm { padding: 4px 10px; font-size: 11px; }
    .vis-count {
      font-size: 11px;
      color: var(--text-muted);
      font-family: 'Fira Code', monospace;
      margin-left: 4px;
      white-space: nowrap;
    }
    .comp-vis-panel {
      position: absolute;
      top: calc(100% + 8px);
      left: 0;
      z-index: 20;
      min-width: 280px;
      max-width: 360px;
      max-height: 320px;
      overflow-y: auto;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }
    .comp-vis-panel::-webkit-scrollbar { width: 8px; }
    .comp-vis-panel::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 4px; }
    .comp-vis-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 5px 8px;
      border-radius: 5px;
      cursor: pointer;
      font-size: 12px;
    }
    .comp-vis-item:hover { background: rgba(255, 255, 255, 0.05); }
    .comp-vis-item input { accent-color: var(--accent-blue); margin-right: 6px; flex-shrink: 0; }
    .comp-vis-name { flex: 1; color: #ddd; font-family: 'Fira Code', monospace; font-size: 11.5px; line-height: 1.4; }
    .comp-vis-n { color: var(--text-muted); font-size: 10.5px; font-family: 'Fira Code', monospace; flex-shrink: 0; }
    .comp-vis-group-label {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-muted);
      padding: 6px 8px 2px;
    }
    .vis-empty { padding: 10px 8px; color: var(--text-muted); font-size: 11.5px; }

    .pill-group {
      display: flex;
      background: var(--bg-canvas);
      padding: 2px;
      border-radius: 6px;
      border: 1px solid var(--border);
    }

    .pill-opt {
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      cursor: pointer;
      border-radius: 4px;
      user-select: none;
    }

    .pill-opt.active {
      background: var(--accent-blue);
      color: #090d16;
    }

    .filter-checkboxes {
      display: flex;
      gap: 10px;
      font-size: 11px;
      color: var(--text-secondary);
      user-select: none;
    }

    .filter-checkboxes label {
      display: flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
    }

    .graph-inspector {
      width: 340px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border);
      height: 100%;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }

    .inspector-title {
      font-size: 18px;
      font-weight: 700;
      font-family: 'Fira Code', monospace;
      margin-bottom: 4px;
      word-break: break-all;
    }

    .inspector-sub {
      font-size: 12px;
      color: var(--text-secondary);
      margin-bottom: 16px;
    }

    .inspector-prop {
      display: flex;
      justify-content: space-between;
      padding: 7px 0;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 12px;
    }
    .inspector-prop .lbl { color: var(--text-muted); }
    .inspector-prop .val { font-weight: 600; font-family: 'Fira Code', monospace; }

    /* CODE EXPLORER TAB (Sourcetrail Style Side-by-Side) */
    #tab-code {
      padding: 0;
      height: 100%;
      overflow: hidden;
    }

    .code-layout {
      display: flex;
      width: 100%;
      height: 100%;
      background: var(--bg-canvas);
    }

    .file-tree-pane {
      width: 280px;
      border-right: 1px solid var(--border);
      background: var(--bg-surface);
      overflow-y: auto;
      padding: 12px 6px;
      flex-shrink: 0;
    }

    .file-tree-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 7px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-family: 'Fira Code', monospace;
      color: var(--text-secondary);
      cursor: pointer;
      user-select: none;
      margin-bottom: 2px;
    }

    .file-tree-item:hover {
      background: var(--bg-card);
      color: var(--text);
    }

    .file-tree-item.active {
      background: var(--bg-card);
      color: #fff;
      font-weight: 600;
      border-left: 3px solid var(--accent-blue);
    }

    .role-badge {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
    }

    .code-viewer-pane {
      flex: 1;
      height: 100%;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .code-viewer-header {
      height: 52px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }

    .code-viewer-content {
      flex: 1;
      overflow: auto;
      padding: 16px;
      background: #090d16;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      line-height: 1.6;
    }

    .code-table {
      border-collapse: collapse;
      width: 100%;
    }
    .code-table td {
      vertical-align: top;
      padding: 0 8px;
    }
    .code-line-num {
      width: 44px;
      text-align: right;
      color: var(--text-muted);
      user-select: none;
      opacity: 0.5;
      font-size: 11px;
    }
    .code-line-text {
      white-space: pre-wrap;
      word-break: break-all;
      color: #e2e8f0;
    }

    /* Syntax highlight colors */
    .syntax-kw { color: #7a7a7a; font-weight: 600; }
    .syntax-fn { color: #b8b8b8; font-weight: 600; }
    .syntax-cls { color: #a0a0a0; font-weight: 600; }
    .syntax-str { color: #b0b0b0; }
    .syntax-cmt { color: #64748b; font-style: italic; }

    
    #tab-docs {
      padding: 24px 36px;
    }

    .docs-container {
      max-width: 900px;
      margin: 0 auto;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 36px 44px;
      line-height: 1.7;
    }

    .docs-nav-tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
      margin-bottom: 24px;
    }

    .docs-tab-btn {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .docs-tab-btn.active {
      background: var(--accent-blue);
      color: #090d16;
      border-color: var(--accent-blue);
    }

    .docs-container h1 { font-size: 26px; font-weight: 700; font-family: var(--font-display); margin-bottom: 16px; color: #fff; }
    .docs-container h2 { font-size: 20px; font-weight: 700; margin-top: 28px; margin-bottom: 12px; color: var(--accent-blue); border-bottom: 1px solid var(--border-subtle); padding-bottom: 6px; }
    .docs-container h3 { font-size: 16px; font-weight: 600; margin-top: 20px; margin-bottom: 8px; color: #fff; }
    .docs-container p { font-size: 14px; color: var(--text-secondary); margin-bottom: 14px; }
    .docs-container ul { margin-left: 20px; margin-bottom: 16px; font-size: 14px; color: var(--text-secondary); }
    .docs-container code { font-family: 'Fira Code', monospace; background: var(--bg-card); padding: 2px 6px; border-radius: 4px; font-size: 12px; color: var(--accent-cyan); }

    /* Modal Global Search */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(0,0,0,0.65);
      backdrop-filter: blur(4px);
      z-index: 200;
      display: none;
      align-items: flex-start;
      justify-content: center;
      padding-top: 100px;
    }
    .modal-overlay.active { display: flex; }

    .search-modal {
      width: 580px;
      background: var(--bg-surface);
      border: 1px solid var(--border-glow);
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
    }

    .search-input-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      background: var(--bg-card);
    }
    .search-input-wrap input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      font-size: 15px;
      color: #fff;
      font-family: inherit;
    }

    .search-results {
      max-height: 380px;
      overflow-y: auto;
      padding: 8px;
    }

    .search-res-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 9px 12px;
      border-radius: 6px;
      cursor: pointer;
    }
    .search-res-item:hover {
      background: var(--bg-card-hover);
    }
  
    .ast-tree-pane {
      width: 320px;
      border-right: 1px solid var(--border-subtle);
      background: var(--bg-canvas);
      overflow-y: auto;
      padding: 16px;
      flex-shrink: 0;
    }
    .ast-node {
      display: flex;
      flex-direction: column;
      margin-left: 12px;
      border-left: 1px solid var(--border-subtle);
      padding-left: 12px;
      margin-top: 6px;
      position: relative;
    }
    .ast-node::before {
      content: '';
      position: absolute;
      top: 14px;
      left: 0;
      width: 8px;
      height: 1px;
      background: var(--border-subtle);
    }
    .ast-header {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      user-select: none;
      transition: background 0.1s;
    }
    .ast-header:hover {
      background: rgba(131, 148, 150, 0.1);
    }
    .ast-type {
      font-size: 10px;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      background: var(--bg-surface);
      padding: 2px 6px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }
    .ast-label {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text);
    }
      /* Minimal monochrome visual system */
      :root {
        --bg-canvas: #101010;
        --bg-surface: #171717;
        --bg-card: #202020;
        --bg-card-hover: #292929;
        --border: #303030;
        --border-subtle: #242424;
        --border-glow: #4a4a4a;
        --text: #e7e7e7;
        --text-secondary: #a6a6a6;
        --text-muted: #707070;
        --text-heading: #f2f2f2;
        --accent-blue: #b8b8b8;
        --accent-cyan: #c4c4c4;
        --accent-purple: #a0a0a0;
        --accent-green: #b0b0b0;
        --accent-amber: #969696;
        --accent-rose: #7a7a7a;
      }
      html { background: #101010; }
      body { letter-spacing: -0.01em; }
      header { height: 56px; background: #151515; border-bottom-color: #2b2b2b; padding: 0 22px; }
      .brand-logo { font-family: var(--font-body); font-size: 14px; letter-spacing: .08em; color: #ededed; background: none; -webkit-text-fill-color: initial; }
      .repo-pill { background: transparent; border: 0; border-left: 1px solid #363636; border-radius: 0; color: #8f8f8f; }
      .search-trigger-btn { background: #1b1b1b; border-color: #303030; border-radius: 5px; }
      .search-trigger-btn:hover { border-color: #505050; color: #ededed; }
      nav.sidebar { width: 208px; background: #151515; border-right-color: #2b2b2b; padding: 18px 10px; }
      .nav-section-label { font-size: 10px; letter-spacing: .12em; font-weight: 600; }
      .nav-item { border-radius: 4px; padding: 8px 10px; color: #929292; }
      .nav-item:hover { background: #1d1d1d; color: #ddd; }
      .nav-item.active { background: #202020; color: #f0f0f0; box-shadow: inset 2px 0 0 #8c8c8c; }
      .nav-item .icon { display: none; }
      .tab-view { padding: 30px 36px; }
      .overview-hero h1 { font-size: 24px; letter-spacing: -.03em; }
      .stat-card, .comp-card, .flow-row { background: #171717; border-color: #2c2c2c; border-radius: 5px; box-shadow: none; }
      .stat-card:hover, .comp-card:hover { border-color: #484848; background: #1b1b1b; transform: none; }
      .stat-val { color: #d0d0d0; font-size: 22px; }
      .banner-entrypoint, .alert-card { background: #191919; border-color: #363636; border-radius: 5px; box-shadow: none; }
      .banner-content h3, .section-title { color: #d0d0d0; }
      .btn-primary { background: #d0d0d0; color: #111; border-radius: 4px; }
      .btn-primary:hover { background: #ededed; transform: none; }
      .btn-secondary { background: #1c1c1c; border-color: #363636; border-radius: 4px; }
      .btn-secondary:hover { border-color: #555; background: #252525; }
      .confidence-high, .confidence-med, .confidence-low, .cohesion-badge, .comp-chip, .singleton-item, .flow-node-badge, .flow-role, .pill-tag, .role-badge { background: #252525 !important; color: #bdbdbd !important; border-color: #444 !important; }
      .onboard-sidebar, .onboard-main { background: #171717; border-color: #2c2c2c; border-radius: 5px; }
      .step-item-card.active { background: #222; border-color: #4a4a4a; box-shadow: none; }
      .graph-canvas-container { background: #101010; }
      .graph-floating-controls { background: rgba(20,20,20,.94); border-color: #333; border-radius: 5px; backdrop-filter: none; }
      .comp-vis-panel { background: #1c1c1c; border-color: #333; border-radius: 5px; box-shadow: none; }
      .comp-vis-item:hover { background: #242424; }
      .comp-vis-n, .vis-count { color: #999; }
      .pill-opt.active { background: #bdbdbd; color: #111; }
      #graph-role-filters .pill-opt { display: inline-flex; align-items: center; transition: all 0.15s ease; }
      #graph-role-filters .pill-opt.active { background: #2a2a2a !important; color: #fff !important; box-shadow: 0 0 0 1px #555; }
      #graph-role-filters .pill-opt[data-role="ENTRY_CANDIDATE"].active { background: rgba(6, 182, 212, 0.2) !important; color: #22d3ee !important; box-shadow: 0 0 0 1px #06b6d4; }
      #graph-role-filters .pill-opt[data-role="CYCLE"].active { background: rgba(244, 63, 94, 0.2) !important; color: #fb7185 !important; box-shadow: 0 0 0 1px #f43f5e; }
      #graph-role-filters .pill-opt[data-role="HUB"].active { background: rgba(192, 132, 252, 0.2) !important; color: #d8b4fe !important; box-shadow: 0 0 0 1px #c084fc; }
      #graph-role-filters .pill-opt[data-role="BRIDGE"].active { background: rgba(245, 158, 11, 0.2) !important; color: #fbbf24 !important; box-shadow: 0 0 0 1px #f59e0b; }
      #graph-role-filters .pill-opt[data-role="LEAF"].active { background: rgba(16, 185, 129, 0.2) !important; color: #34d399 !important; box-shadow: 0 0 0 1px #10b981; }
      .graph-inspector, .file-tree-pane, .ast-tree-pane, .code-viewer-header { background: #151515; }
      .file-tree-item { border-radius: 4px; }
      .file-tree-item:hover { background: #1f1f1f; }
      .file-tree-item.active { background: #202020; border-left-color: #858585; }
      .code-viewer-content { background: #101010; }
      .docs-container { background: #171717; border-color: #2c2c2c; border-radius: 5px; box-shadow: none; }
      .docs-tab-btn { background: #202020; border-color: #353535; }
      .docs-tab-btn.active { background: #bdbdbd; color: #111; border-color: #bdbdbd; }
      .modal-overlay { background: rgba(0,0,0,.72); backdrop-filter: blur(2px); }
      .search-modal { background: #171717; border-color: #3a3a3a; border-radius: 5px; box-shadow: 0 18px 50px rgba(0,0,0,.5); }
      .search-input-wrap { background: #1d1d1d; border-bottom-color: #303030; }
      .search-res-item { border-radius: 4px; }
      .search-res-item:hover { background: #252525; }
      input::placeholder { color: #666 !important; }
    </style>
</head>
<body>
  <!-- Header App Bar -->
  <header>
    <div class="brand-group">
      <div class="brand-logo">
        <span>KARUVI</span>
      </div>
      <div class="repo-pill" id="header-repo-name">Repository</div>
    </div>

    <div class="header-actions">
      <button class="search-trigger-btn" id="open-search-btn">
        <span>Search symbols, modules, components...</span>
        <span class="kbd-shortcut">⌘K</span>
      </button>
    </div>
  </header>

  <!-- App Body Layout -->
  <div class="app-container">
    <!-- Navigation Sidebar -->
    <nav class="sidebar">
      <div class="nav-section-label">Modes</div>
      <div class="nav-item active" data-tab="overview">
        <span class="icon">◉</span>
        <span>Overview</span>
      </div>
      <div class="nav-item" data-tab="architecture">
        <span class="icon"></span>
        <span>Architecture</span>
      </div>
      <div class="nav-item" data-tab="graph">
        <span class="icon"></span>
        <span>Graph Explorer</span>
      </div>
      <div class="nav-item" data-tab="code">
        <span class="icon"></span>
        <span>Code Explorer</span>
      </div>

    </nav>

    <!-- Main Workspace -->
    <main class="workspace">

      <!-- VIEW 1: OVERVIEW -->
      <div class="tab-view active" id="tab-overview">
        <div class="overview-hero">
          <h1>Codebase Intelligence & Cartography</h1>
          <p>Deterministic architecture reconstruction, topological graph analysis, and progressive onboarding.</p>
        </div>

        <div class="stat-grid" id="stats-container"></div>

        <!-- Start Here Entry Point Banner -->
        <div class="banner-entrypoint" id="entry-point-banner">
          <div class="banner-content">
            <h3>Recommended Starting Point</h3>
            <div class="mod-title" id="entry-mod-name">analyzing...</div>
            <p id="entry-mod-desc">This module sits structurally high and can reach major portions of the repository.</p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn-secondary" id="btn-jump-code">View Code</button>
          </div>
        </div>

        <!-- Radar Alert for Cycles -->
        <div id="overview-cycle-radar" style="display: none;"></div>

        <!-- Key Architectural Insights -->
        <div class="section-title">Structural Bridges & Central Modules</div>
        <div id="bridges-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 30px;"></div>
      </div>

      <!-- VIEW 3: ARCHITECTURE -->
      <div class="tab-view" id="tab-architecture">
        <div class="arch-header">
          <div>
            <div class="section-title" style="margin-bottom: 4px;">Architectural Components</div>
            <div class="arch-summary" id="arch-summary"></div>
          </div>
          <div class="arch-actions">
            <button class="btn-secondary" id="btn-toggle-singletons" style="display: none;"></button>
            <button class="btn-secondary" id="btn-arch-legend">What am I looking at?</button>
          </div>
        </div>

        <div class="arch-legend" id="arch-legend" style="display: none;"></div>

        <div class="section-title">Main Components</div>
        <div class="comp-grid" id="arch-components-grid"></div>

        <div id="singletons-section" style="display: none;">
          <div class="section-title">Standalone Files</div>
          <div class="singleton-list" id="singletons-list"></div>
        </div>

        <div class="section-title">High-Level Architectural Flows</div>
        <div class="flows-container" id="arch-flows-container"></div>
      </div>

      <!-- VIEW 4: GRAPH EXPLORER WITH PROGRESSIVE DISCLOSURE -->
      <div class="tab-view" id="tab-graph">
        <div class="graph-layout">
          <div class="graph-canvas-container">
            <div class="graph-floating-controls">
              <div style="display: flex; gap: 8px; align-items: center;">
                <input type="text" id="graph-text-filter" placeholder="Filter nodes (regex)..." style="background: var(--bg-surface); border: 1px solid var(--border); color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; width: 160px;">
                <div style="display: flex; gap: 4px; align-items: center; margin-left: 8px;" id="graph-role-filters">
                  <span class="pill-opt active" data-role="ALL">All</span>
                  <span class="pill-opt" data-role="ENTRY_CANDIDATE"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#06b6d4;margin-right:5px;"></span>Entry</span>
                  <span class="pill-opt" data-role="CYCLE"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#f43f5e;margin-right:5px;"></span>Cycle</span>
                  <span class="pill-opt" data-role="HUB"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#c084fc;margin-right:5px;"></span>Hub</span>
                  <span class="pill-opt" data-role="BRIDGE"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#f59e0b;margin-right:5px;"></span>Bridge</span>
                  <span class="pill-opt" data-role="LEAF"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#10b981;margin-right:5px;"></span>Leaf</span>
                </div>
              </div>
              <div class="filter-checkboxes" style="display: flex; gap: 12px; align-items: center; margin-left: 8px;">
                <label style="display: inline-flex; align-items: center; gap: 5px; cursor: pointer;"><input type="checkbox" id="chk-filter-calls" checked> <span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:#38bdf8;"></span>Calls</label>
                <label style="display: inline-flex; align-items: center; gap: 5px; cursor: pointer;"><input type="checkbox" id="chk-filter-imports" checked> <span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:#c084fc;"></span>Imports</label>
                <label style="display: inline-flex; align-items: center; gap: 5px; cursor: pointer;"><input type="checkbox" id="chk-filter-refs" checked> <span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:#34d399;"></span>References</label>
              </div>
              <div class="vis-controls">
                <div class="vis-toolbar">
                  <button class="btn-secondary btn-sm" id="btn-toggle-comp-vis">☰ Components</button>
                  <button class="btn-secondary btn-sm" id="btn-comp-vis-all">Select all</button>
                  <button class="btn-secondary btn-sm" id="btn-comp-vis-none">Unselect all</button>
                  <span class="vis-count" id="comp-vis-count"></span>
                </div>
                <div class="comp-vis-panel" id="comp-vis-panel" style="display: none;"></div>
              </div>
            </div>
            <div id="network-canvas"></div>
          </div>

        </div>
      </div>

      <!-- VIEW 5: SOURCETRAIL CODE EXPLORER -->
      <div class="tab-view" id="tab-code">
        <div class="code-layout">
          <div class="file-tree-pane" id="code-file-tree"></div>
          <div class="ast-tree-pane" id="code-ast-tree">
            <div style="color: var(--text-muted); font-size: 13px; font-family: var(--font-body);">Select a module to view AST</div>
          </div>
          <div class="code-viewer-pane" id="code-viewer-pane">
            <div class="code-viewer-header" id="code-viewer-header">
              <div style="font-family: 'Fira Code', monospace; font-size: 13px; font-weight: 600; color: #fff;" id="code-file-path">Select a file from the tree</div>
              <div id="code-header-actions"></div>
            </div>
            <div class="code-viewer-content" id="code-viewer-content">
              <div style="color: var(--text-muted); font-size: 13px; padding: 20px;">Select a file on the left to inspect its syntax-highlighted source code, AST hierarchy, and symbol bindings.</div>
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
        <span>Search</span>
        <input type="text" id="global-search-input" placeholder="Search components, modules, symbols, or roles... (Esc to close)">
      </div>
      <div class="search-results" id="search-results-list"></div>
    </div>
  </div>

  <!-- Embedded Payload -->
  <script>
    window.KARUVI_DATA = __KARUVI_PAYLOAD__;
    window.__KARUVI_DATA__ = window.KARUVI_DATA;
  </script>

  <!-- Interactive Application Logic -->
  <script>
    (function() {
      // Monaco Editor initialization
      let monacoEditor = null;
      let isMonacoReady = false;
      if (window.require) {
          require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});
          require(['vs/editor/editor.main'], function() {
              monaco.editor.defineTheme('monochromeDark', {
                  base: 'vs-dark',
                  inherit: true,
                  rules: [
                      { background: '121212' }
                  ],
                  colors: {
                      'editor.background': '#121212',
                      'editor.foreground': '#eeeeee',
                      'editorLineNumber.foreground': '#555555',
                      'editor.lineHighlightBackground': '#1e1e1e',
                      'editorCursor.foreground': '#ffffff',
                      'editor.selectionBackground': '#2e2e2e'
                  }
              });
              
              isMonacoReady = true;
          
          });
      }

      const data = window.KARUVI_DATA;
      if (!data) return;

      // Header repository label
      document.getElementById('header-repo-name').textContent = data.project_name || 'Codebase';

      // -------------------------------------------------------------
      // Tab Navigation
      // -------------------------------------------------------------
      const navItems = document.querySelectorAll('.nav-item');
      const tabViews = document.querySelectorAll('.tab-view');

      function switchTab(targetTab) {
        navItems.forEach(n => n.classList.toggle('active', n.dataset.tab === targetTab));
        tabViews.forEach(v => v.classList.toggle('active', v.id === `tab-${targetTab}`));
        if (targetTab === 'graph') {
          setTimeout(() => initOrFitNetwork(), 50);
        }
      }
      window.switchTab = switchTab;
      window.switchView = switchTab;

      navItems.forEach(item => {
        item.addEventListener('click', () => switchTab(item.dataset.tab));
      });

      document.getElementById('btn-jump-code').addEventListener('click', () => switchTab('code'));

      // -------------------------------------------------------------
      // 1. Overview Tab
      // -------------------------------------------------------------
      const statsGrid = document.getElementById('stats-container');
      const stats = data.stats || {};
      const statItems = [
        { val: stats.total_modules || 0, lbl: 'Modules' },
        { val: stats.total_components || 0, lbl: 'Components' },
        { val: stats.total_symbols || 0, lbl: 'Symbols Indexed' },
        { val: stats.total_module_edges || 0, lbl: 'Module Edges' },
        { val: stats.total_cycles || 0, lbl: 'Circular Loops' },
      ];
      statsGrid.innerHTML = statItems.map(s => `
        <div class="stat-card">
          <div class="stat-val">${s.val}</div>
          <div class="stat-lbl">${s.lbl}</div>
        </div>
      `).join('');

      // Entry point
      if (data.entry_points && data.entry_points.length > 0) {
        const topEp = data.entry_points[0];
        document.getElementById('entry-mod-name').textContent = topEp.module;
        const ev = topEp.evidence || {};
        document.getElementById('entry-mod-desc').textContent = 
          `Scores highest in downstream reach with 0 cyclic blocks. Directly reaches ${ev.reachable_modules || 0} modules across ${ev.reachable_components || 0} architectural components.`;
      } else {
        document.getElementById('entry-point-banner').style.display = 'none';
      }

      // Cycle Radar
      const cycles = data.cycles || [];
      const cycleRadarEl = document.getElementById('overview-cycle-radar');
      if (cycles.length > 0) {
        cycleRadarEl.style.display = 'block';
        cycleRadarEl.innerHTML = `
          <div class="alert-card warning">
            <div style="font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
              <span>Circular Dependency Radar</span>
              <span class="pill-tag" style="background: rgba(150,150,150,0.2); color: #b0b0b0;">${cycles.length} loop(s) detected</span>
            </div>
            <div>Multi-module cyclic loops can cause tight coupling and initialization surprises. These are grouped into unified conceptual steps in the Onboarding course.</div>
            <div style="margin-top: 8px; font-family: 'Fira Code', monospace; font-size: 11px;">
              ${cycles.map((c, i) => `<div>Loop #${i+1}: ${c.join(' → ')}</div>`).join('')}
            </div>
          </div>
        `;
      }

      // Bridges
      const bridgesContainer = document.getElementById('bridges-container');
      const bridgeMods = (data.modules || []).filter(m => m.role === 'BRIDGE' || m.role === 'HUB').slice(0, 4);
      if (bridgeMods.length > 0) {
        bridgesContainer.innerHTML = bridgeMods.map(m => `
          <div class="stat-card" style="cursor: pointer;" onclick="window.selectModule('${m.id}')">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span class="role-badge" style="background: rgba(150,150,150,0.15); color: var(--accent-amber); border: 1px solid rgba(150,150,150,0.3);">
                ${m.role === 'BRIDGE' ? 'Bridge' : 'Hub'}
              </span>
              <span style="font-size: 11px; color: var(--text-muted);">${m.component_name}</span>
            </div>
            <div style="font-weight: 700; font-family: 'Fira Code', monospace; font-size: 13px; color: #fff; margin-bottom: 6px;">${m.name}</div>
            <div style="font-size: 11px; color: var(--text-secondary);">Betweenness: ${m.betweenness} • Reach: ${m.reachable_descendants} modules</div>
          </div>
        `).join('');
      } else {
        bridgesContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No critical bridge bottlenecks detected.</div>';
      }

      // -------------------------------------------------------------
      // 3. Architecture Tab
      // -------------------------------------------------------------
      const compGrid = document.getElementById('arch-components-grid');
      const archSummary = document.getElementById('arch-summary');
      const singletonsSection = document.getElementById('singletons-section');
      const singletonsList = document.getElementById('singletons-list');
      const singletonsBtn = document.getElementById('btn-toggle-singletons');
      const archLegend = document.getElementById('arch-legend');
      document.getElementById('btn-arch-legend').addEventListener('click', () => {
        archLegend.style.display = archLegend.style.display === 'none' ? 'block' : 'none';
      });

      const METHOD_LABELS = {
        'GRAPH_COMMUNITY': 'Grouped by heavy inner connections',
        'STRUCTURAL_BOUNDARY': 'Grouped by shared folder',
        'BOUNDARY_AND_COMMUNITY': 'Folder and connections agree',
        'SINGLETON': 'Single file',
      };
      function methodLabel(m) {
        return METHOD_LABELS[m] || String(m).toLowerCase().replace(/_/g, ' ');
      }
      function compDisplayName(c) {
        const label = (c.metadata || {}).distinguishing_label;
        return label ? `${c.name} · ${label}` : c.name;
      }
      function cohesionColor(pct) {
        if (pct >= 70) return 'var(--accent-green)';
        if (pct >= 40) return 'var(--accent-amber)';
        return 'var(--accent-rose)';
      }

      function componentCard(c) {
        const confPct = Math.round((c.confidence || 0) * 100);
        const color = cohesionColor(confPct);
        const meta = c.metadata || {};
        const label = meta.distinguishing_label;
        const mods = c.modules || [];
        const why = (c.discovery_methods || []).map(methodLabel).join(', ') || 'No discovery evidence';
        const intW = meta.internal_weight || 0;
        const extW = meta.external_weight || 0;
        const connLine = (intW || extW)
          ? `<span>${intW} internal vs ${extW} external connections</span>`
          : `<span>No cross-module connections recorded</span>`;
        return `
          <div class="comp-card" onclick="window.inspectComponent('${c.id}')">
            <div class="comp-card-header">
              <span class="comp-name">${c.name}</span>
              <span class="cohesion-badge" style="color:${color}; border-color:${color};">${confPct}% cohesion</span>
            </div>
            ${label ? `<div class="comp-sublabel">${label}</div>` : ''}
            <div class="cohesion-track"><div class="cohesion-fill" style="width:${confPct}%; background:${color};"></div></div>
            <div style="font-size: 12px; color: var(--text-secondary);">
              ${mods.length} module${mods.length === 1 ? '' : 's'} • <span class="comp-why">${why}</span>
            </div>
            <div class="comp-conn">${connLine}</div>
            <div class="comp-modules-list">
              ${mods.map(m => `<span class="comp-chip">${m.split('/').pop()}</span>`).join('')}
            </div>
          </div>
        `;
      }

      const compInGraph = new Set();
      (data.component_edges || []).forEach(e => { if (e) { compInGraph.add(e.source); compInGraph.add(e.target); } });
      const isSingleton = c => (c.modules || []).length === 1 && !compInGraph.has(c.id);
      const sortComps = (a, b) => {
        const sa = (a.modules || []).length, sb = (b.modules || []).length;
        if (sa !== sb) return sb - sa;
        const ia = (a.metadata || {}).internal_weight || 0, ib = (b.metadata || {}).internal_weight || 0;
        if (ia !== ib) return ib - ia;
        return compDisplayName(a).localeCompare(compDisplayName(b));
      };
      const allComps = [...(data.components || [])];
      const multiComps = allComps.filter(c => !isSingleton(c)).sort(sortComps);
      const singletonComps = allComps.filter(isSingleton).sort((a, b) => compDisplayName(a).localeCompare(compDisplayName(b)));

      let showSingletons = false;
      function renderArchPanel() {
        compGrid.innerHTML = multiComps.map(componentCard).join('');
        singletonsSection.style.display = showSingletons && singletonComps.length ? 'block' : 'none';
        singletonsBtn.style.display = singletonComps.length ? 'inline-block' : 'none';
        singletonsBtn.textContent = `${showSingletons ? 'Hide' : 'Show'} standalone file${singletonComps.length === 1 ? '' : 's'} (${singletonComps.length})`;
        singletonsList.innerHTML = singletonComps.map(s => `
          <div class="singleton-item" onclick="window.inspectComponent('${s.id}')">
            <span class="singleton-name">${compDisplayName(s)}</span>
            <span class="singleton-mods">${(s.modules || []).map(m => m.split('/').pop()).join(', ')}</span>
          </div>
        `).join('');

        let summary = `${multiComps.length} main component${multiComps.length === 1 ? '' : 's'}`;
        if (singletonComps.length) summary += ` · ${singletonComps.length} standalone file${singletonComps.length === 1 ? '' : 's'}`;
        const biggest = multiComps[0];
        if (biggest) summary += ` · largest: ${compDisplayName(biggest)} (${(biggest.modules || []).length} modules)`;
        archSummary.textContent = summary;

        archLegend.innerHTML = `
          <div class="legend-grid">
            <div><strong>Component</strong><br>A group of files that Karuvi believes belong together.</div>
            <div><strong>Cohesion %</strong><br>How strongly the folder evidence and the dependency evidence agree the group is real.</div>
            <div><strong>Boundary</strong><br>The folder a file lives in — the "location" evidence.</div>
            <div><strong>Community</strong><br>Files that depend heavily on each other — the "who talks to whom" evidence.</div>
            <div><strong>Standalone file</strong><br>A single file that didn't group with anything. Not a design pattern — just a lone file.</div>
            <div><strong>Flow</strong><br>A common journey across components, from an entry point to an endpoint (leaf).</div>
          </div>
        `;
      }
      singletonsBtn.addEventListener('click', () => {
        showSingletons = !showSingletons;
        renderArchPanel();
      });
      renderArchPanel();

      const flowsContainer = document.getElementById('arch-flows-container');
      const flowRoleBadge = (role) => {
        if (role === 'Entry') return `<span class="flow-role role-entry">Entry</span>`;
        if (role === 'Leaf') return `<span class="flow-role role-leaf">Leaf</span>`;
        if (role === 'Cycle') return `<span class="flow-role role-cycle">Cycle</span>`;
        return '';
      };
      if (data.flows && data.flows.length > 0) {
        flowsContainer.innerHTML = data.flows.map((f, fi) => {
          const steps = f.path_names || f.path || [];
          const chain = steps.map((step, idx) => `
            <span class="flow-node-badge">${step}</span>
            ${idx < steps.length - 1 ? '<span class="flow-arrow">→</span>' : ''}
          `).join('');
          const algo = (f.evidence || {}).algorithm === 'direct_edge'
            ? 'Direct dependency'
            : 'Shortest route entry → endpoint';
          const hops = (f.evidence || {}).hop_count;
          const targetId = (f.path && f.path.length) ? f.path[0] : '';
          return `
            <div class="flow-row" title="Open in Graph Explorer" onclick="${targetId ? `window.inspectComponent('${targetId}')` : ''}">
              ${flowRoleBadge(f.start_role)}
              <div style="flex: 1; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">${chain}</div>
              ${flowRoleBadge(f.end_role)}
              <div class="flow-meta">
                <span class="flow-algo">${algo}</span>
                ${hops != null ? `<span class="flow-algo">${hops} hop${hops === 1 ? '' : 's'}</span>` : ''}
              </div>
            </div>
          `;
        }).join('');
      } else {
        flowsContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No cross-component flows recorded.</div>';
      }

      // -------------------------------------------------------------
      // 4. Code Explorer Tab (Sourcetrail Side-by-Side)
      // -------------------------------------------------------------
      const fileTreePane = document.getElementById('code-file-tree');
      fileTreePane.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; padding: 20px; text-align: center;">Select a module to view its dependency tree.</div>';

      const astStyles = `
        <style>
          .ast-node {
            font-family: 'Fira Code', monospace;
            font-size: 12px;
            position: relative;
          }
          .ast-summary {
            cursor: pointer;
            outline: none;
            user-select: none;
            display: inline-flex;
            align-items: center;
            padding: 2px 4px;
            border-radius: 4px;
            transition: background 0.2s;
          }
          .ast-summary:hover {
            background: rgba(255,255,255,0.05);
          }
          .ast-children {
            margin-left: 8px;
            padding-left: 12px;
            border-left: 1px solid rgba(255,255,255,0.15);
          }
          .ast-item-wrapper {
            position: relative;
          }
          .ast-item-wrapper::before {
            content: '';
            position: absolute;
            top: 10px;
            left: -12px;
            width: 12px;
            height: 1px;
            border-top: 1px solid var(--branch-color, rgba(255,255,255,0.25));
            z-index: 1;
          }
          .ast-badge {
            font-size: 9px;
            padding: 1px 4px;
            border-radius: 4px;
            margin-right: 6px;
            font-weight: 700;
            letter-spacing: 0.2px;
            display: inline-block;
          }
          .ast-symbol {
            color: #f8fafc;
            font-weight: 400;
            letter-spacing: 0.2px;
            z-index: 2;
            position: relative;
          }
          .ast-uuid {
            font-size: 9px;
            color: rgba(255,255,255,0.2);
            margin-bottom: 2px;
            font-family: monospace;
          }
        </style>
      `;

      function renderASTNode(node, depth = 0) {
        if (!node) return '';
        
        let nameRaw = node.name || 'Node';
        if (!node.name && node.variable) {
          nameRaw = node.variable.display || node.variable.name || 'Node';
        }
        
        let uuid = '';
        if (node.variable && node.variable.uuid) {
           uuid = node.variable.uuid;
         } else if (nameRaw.includes('id=')) {
            const match = nameRaw.match(/id=([a-f0-9-]+)/);
            if (match) uuid = match[1];
         }

        let displayName = (node.variable && node.variable.name) ? node.variable.name : nameRaw;

        let badgeBg = 'rgba(148, 163, 184, 0.1)';
        let badgeColor = '#cbd5e1';
        let badgeBorder = 'rgba(148, 163, 184, 0.3)';
        let badgeText = 'BLOCK';
        
        if (nameRaw.startsWith('def ')) {
            badgeBg = 'rgba(30, 58, 138, 0.3)';
            badgeColor = '#93c5fd';
            badgeBorder = '#1d4ed8';
            badgeText = 'FUNCTION';
            if (displayName === nameRaw) {
               displayName = displayName.replace('def ', '') + '()';
            } else {
               displayName += '()';
            }
        } else if (nameRaw.startsWith('class ')) {
            badgeBg = 'rgba(88, 28, 135, 0.3)';
            badgeColor = '#d8b4fe';
            badgeBorder = '#7e22ce';
            badgeText = 'CLASS';
            if (displayName === nameRaw) displayName = displayName.replace('class ', '');
        } else if (nameRaw.includes('(new assignment')) {
            badgeBg = 'rgba(6, 78, 59, 0.3)';
            badgeColor = '#6ee7b7';
            badgeBorder = '#047857';
            badgeText = 'VAR';
            if (displayName === nameRaw) displayName = displayName.split(' (new assignment')[0];
        } else if (nameRaw.includes('(call)')) {
            badgeBg = 'rgba(120, 53, 15, 0.3)';
            badgeColor = '#fcd34d';
            badgeBorder = '#b45309';
            badgeText = 'CALL';
            if (displayName === nameRaw) displayName = displayName.split(' (call)')[0];
        } else if (displayName === 'Module Start' || displayName === 'Node') {
            if (displayName === 'Node') displayName = 'Block';
        }

        // Flatten blocks
        if (displayName === 'Block' || displayName === 'Module Start') {
            if (node.children && node.children.length > 0) {
                return node.children.map(c => renderASTNode(c, depth)).join('');
            }
            return '';
        }

        let badgeHtml = `<span class="ast-badge" style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder};">${badgeText}</span>`;

        let depsStr = '';
        if (node.dependencies && node.dependencies.length > 0) {
          const depNames = node.dependencies.map(d => {
              let dName = (d.variable && d.variable.name) ? d.variable.name : (d.name || 'Unknown');
              if (dName.includes(' (new assignment')) dName = dName.split(' (new assignment')[0];
              if (dName.includes(' (call)')) dName = dName.split(' (call)')[0];
              return `<span style="color: #94a3b8;">${dName}</span>`;
          }).join(', ');
          depsStr = `<div style="font-size: 10px; color: var(--text-muted); margin-bottom: 4px; display: flex; align-items: center; gap: 4px;">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-blue); opacity: 0.5;"><polyline points="15 10 20 15 15 20"></polyline><path d="M4 4v7a4 4 0 0 0 4 4h12"></path></svg>
            ${depNames}
          </div>`;
        }

        let html = '';
        const lineLoc = (node.variable && node.variable.reference) ? ` <span onclick=\"if(window.monacoEditor){event.stopPropagation(); window.monacoEditor.revealLineInCenter(${node.variable.reference.line}); window.monacoEditor.setPosition({lineNumber: ${node.variable.reference.line}, column: 1}); window.monacoEditor.focus();}\" style=\"color: var(--accent-blue); font-size: 9px; margin-left: 6px; opacity: 0.8; font-weight: 500; cursor: pointer; text-decoration: underline;\" title=\"Jump to line ${node.variable.reference.line}\">L${node.variable.reference.line}</span>` : '';

        const isRoot = depth === 0;
        const uuidHtml = uuid ? `<div class="ast-uuid">${uuid}</div>` : '';

        if ((node.children && node.children.length > 0) || depsStr || uuid) {
          html += `
            <div class="${isRoot ? '' : 'ast-item-wrapper'}" ${isRoot ? '' : `style="--branch-color: ${badgeBorder};"`}>
              <details class="ast-node" style="margin-top: ${isRoot ? '0' : '2px'};" >
                <summary class="ast-summary">
                  <div style="display: inline-flex; align-items: center; vertical-align: middle;">
                      ${badgeHtml}
                      <span class="ast-symbol">${displayName}</span>
                      ${lineLoc}
                  </div>
                </summary>
                <div class="ast-children" style="border-left-color: ${badgeBorder}77;">
                  ${uuidHtml}
                  ${depsStr}
                  ${(node.children || []).map(c => renderASTNode(c, depth + 1)).join('')}
                </div>
              </details>
            </div>
          `;
        } else {
          html += `
            <div class="${isRoot ? '' : 'ast-item-wrapper'}" ${isRoot ? '' : `style="--branch-color: ${badgeBorder};"`}>
              <div class="ast-node" style="margin-top: ${isRoot ? '0' : '2px'}; padding: 2px 4px;">
                <div style="display: flex; align-items: center; width: 100%;">
                  ${badgeHtml}
                  <span class="ast-symbol">${displayName}</span>
                  ${lineLoc}
                </div>
              </div>
            </div>
          `;
        }
        return html;
      }

      function renderDependencyTree(mod) {
        if (!mod) return;
        
        let html1 = '';
        html1 += `<div style="font-size: 13px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border); word-break: break-all;">Module Explorer<br><span style="font-size: 11px; color: var(--text-muted); font-family: 'Fira Code', monospace; font-weight: normal;">${mod.id}</span></div>`;
        
        // --- Upstream ---
        html1 += `
          <div style="margin-bottom: 12px; padding: 0 8px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-amber); text-transform: uppercase; padding: 4px 0; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬆️ UPSTREAM DEPENDENCIES (${(mod.outgoing_modules || []).length})
            </div>
            <div style="padding-left: 10px; border-left: 2px solid rgba(245, 158, 11, 0.3); margin-left: 4px;">
        `;
        if (mod.outgoing_modules && mod.outgoing_modules.length > 0) {
            mod.outgoing_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              html1 += `<div class="file-tree-item" onclick="window.selectModule('${depId}')"><span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${depName}</span></div>`;
            });
        } else {
            html1 += `<div style="padding: 4px 0; font-size: 11px; color: var(--text-muted);">None (No imports)</div>`;
        }
        html1 += `</div></div>`;
        
        // --- Downstream ---
        html1 += `
          <div style="margin-bottom: 16px; padding: 0 8px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-green); text-transform: uppercase; padding: 4px 0; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬇️ DOWNSTREAM DEPENDENTS (${(mod.incoming_modules || []).length})
            </div>
            <div style="padding-left: 10px; border-left: 2px solid rgba(16, 185, 129, 0.3); margin-left: 4px;">
        `;
        if (mod.incoming_modules && mod.incoming_modules.length > 0) {
            mod.incoming_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              html1 += `<div class="file-tree-item" onclick="window.selectModule('${depId}')"><span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${depName}</span></div>`;
            });
        } else {
            html1 += `<div style="padding: 4px 0; font-size: 11px; color: var(--text-muted);">None (No dependents)</div>`;
        }
        html1 += `</div></div>`;
        
        // --- AST Tree ---
        let html2 = astStyles;
        html2 += `<div style="font-size: 11px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 4px; border-bottom: 1px solid var(--border); padding-bottom: 12px; text-transform: uppercase;">INTRA-FILE AST TREE</div>`;
        html2 += `<div style="padding: 0 8px;">`;
        if (mod.code_flow) {
            html2 += renderASTNode(mod.code_flow);
        } else {
            html2 += `<div style="color: var(--text-muted); font-size: 12px;">No AST data available.</div>`;
        }
        html2 += `</div>`;
        
        document.getElementById('code-file-tree').innerHTML = html1;
        document.getElementById('code-ast-tree').innerHTML = html2;
      }


      window.selectModule = function(modId) {
        switchTab('code');
        const mod = (data.modules || []).find(m => m.id === modId);
        if (!mod) return;

        // Render dependency tree
        renderDependencyTree(mod);

        document.getElementById('code-file-path').textContent = `${mod.path} (${mod.line_count} LOC • ${mod.role})`;
        document.getElementById('code-header-actions').innerHTML = `
          <button class="btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="window.jumpToGraphNode('${mod.id}')">View in Graph </button>
        `;

        const codeContentEl = document.getElementById('code-viewer-content');
        if (mod.source_code) {
          if (isMonacoReady) {
            if (!monacoEditor) {
                codeContentEl.innerHTML = '';
                window.monacoEditor = monacoEditor = monaco.editor.create(codeContentEl, {
                    value: mod.source_code,
                    language: 'python',
                    theme: 'monochromeDark',
                    readOnly: true,
                    automaticLayout: true,
                    minimap: { enabled: false },
                    fontSize: 13,
                    fontFamily: "'Fira Code', monospace",
                    scrollBeyondLastLine: false,
                    padding: { top: 16, bottom: 16 }
                });
            } else {
                window.monacoEditor = monacoEditor;
                  monacoEditor.setValue(mod.source_code);
                monacoEditor.setScrollTop(0);
            }
          } else {
            codeContentEl.innerHTML = '<div style="padding: 20px; color: #fff; text-align: center; font-family: monospace;">Loading Monaco Editor...</div>';
            setTimeout(() => window.selectModule(modId), 100);
          }
        } else {
          // Fallback summary if source code not cached
          if (monacoEditor) {
              monacoEditor.dispose();
              monacoEditor = null;
          }
          codeContentEl.innerHTML = `
            <div style="padding: 20px;">
              <h3 style="color: #fff; margin-bottom: 12px;">Module Inspection: ${mod.path}</h3>
              <div class="stat-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 20px;">
                <div class="stat-card"><div class="stat-val">${mod.line_count}</div><div class="stat-lbl">Lines</div></div>
                <div class="stat-card"><div class="stat-val">${mod.function_count}</div><div class="stat-lbl">Functions</div></div>
                <div class="stat-card"><div class="stat-val">${mod.class_count}</div><div class="stat-lbl">Classes</div></div>
              </div>
              <div class="section-title">Functions & Signatures</div>
              <div style="font-family: 'Fira Code', monospace; line-height: 2;">
                ${(mod.functions || []).map(f => `<div><span style="color: var(--accent-green);">def</span> <strong>${f.name}</strong>${f.signature || '()'}</div>`).join('') || '<div style="color: var(--text-muted);">None</div>'}
              </div>
            </div>
          `;
        }
      };

      // -------------------------------------------------------------
      // 5. Graph Explorer with Unrelated Node Greying & Role/Edge Color Coding
      // -------------------------------------------------------------
      let network = null;
      let currentLevel = 'modules';
      let unfoldedComponents = new Set();
      let selectedNodeId = null;

      // -------------------------------------------------------------
      // Component visibility (graph view only): hide groups of modules
      // -------------------------------------------------------------
      const VIS_STANDALONE = '__standalone__';
      const compEdgeIds = new Set();
      (data.component_edges || []).forEach(e => { if (e) { compEdgeIds.add(e.source); compEdgeIds.add(e.target); } });
      const singletonCompIds = new Set(
        (data.components || [])
          .filter(c => (c.modules || []).length === 1 && !compEdgeIds.has(c.id))
          .map(c => c.id)
      );
      const moduleGroup = function(m) {
        const cid = m.component_id || m.id;
        if (!cid || cid === 'core' || singletonCompIds.has(cid)) return VIS_STANDALONE;
        return cid;
      };
      const visibleComponents = new Set(
        [VIS_STANDALONE].concat((data.components || []).map(c => c.id))
      );
      function buildVisibleModuleSet() {
        const set = new Set();
        (data.modules || []).forEach(m => {
          if (visibleComponents.has(moduleGroup(m))) set.add(m.id);
        });
        return set;
      }

      function compVisTitle(c) {
        const label = (c.metadata || {}).distinguishing_label;
        return label ? `${c.name} · ${label}` : c.name;
      }

      const container = document.getElementById('network-canvas');

      const cyclesSet = new Set();
      (data.cycles || []).forEach(cycle => cycle.forEach(m => cyclesSet.add(m)));

      function getModuleRoleColors(role, isInCycle) {
        if (isInCycle || role === 'CYCLE_MEMBER') {
          return {
            border: '#f43f5e',
            background: '#330a14',
            text: '#ffe4e6',
            highlightBorder: '#fb7185',
            highlightBg: '#5c0b1f',
            hoverBorder: '#fda4af',
            hoverBg: '#450a18'
          };
        }
        switch (role) {
          case 'ENTRY_CANDIDATE':
            return {
              border: '#06b6d4',
              background: '#082536',
              text: '#cffafe',
              highlightBorder: '#22d3ee',
              highlightBg: '#0e4a66',
              hoverBorder: '#67e8f9',
              hoverBg: '#0b3952'
            };
          case 'HUB':
            return {
              border: '#c084fc',
              background: '#280c42',
              text: '#fae8ff',
              highlightBorder: '#d8b4fe',
              highlightBg: '#501784',
              hoverBorder: '#e9d5ff',
              hoverBg: '#3d1265'
            };
          case 'BRIDGE':
            return {
              border: '#f59e0b',
              background: '#361b05',
              text: '#fef3c7',
              highlightBorder: '#fbbf24',
              highlightBg: '#663309',
              hoverBorder: '#fde68a',
              hoverBg: '#4e2607'
            };
          case 'LEAF':
            return {
              border: '#10b981',
              background: '#072e21',
              text: '#d1fae5',
              highlightBorder: '#34d399',
              highlightBg: '#0c583f',
              hoverBorder: '#6ee7b7',
              hoverBg: '#094431'
            };
          case 'INTERMEDIARY':
          default:
            return {
              border: '#38bdf8',
              background: '#0f1f38',
              text: '#f0f9ff',
              highlightBorder: '#60a5fa',
              highlightBg: '#1e3f73',
              hoverBorder: '#93c5fd',
              hoverBg: '#173059'
            };
        }
      }

      const edgeDefaultStyles = new Map();

      function buildGraphDataSet(level) {
        edgeDefaultStyles.clear();
        const nodes = [];
        const edges = [];
        const filterCalls = document.getElementById('chk-filter-calls').checked;
        const filterImports = document.getElementById('chk-filter-imports').checked;
        const filterRefs = document.getElementById('chk-filter-refs').checked;

        if (level === 'architecture') {
          (data.components || []).forEach(c => {
            const isUnfolded = unfoldedComponents.has(c.id);
            if (!isUnfolded) {
              nodes.push({
                id: `comp:${c.id}`,
                label: `${c.name}\\n(${c.modules.length} modules)`,
                shape: 'box',
                color: {
                  background: '#0e1e38',
                  border: '#38bdf8',
                  highlight: { background: '#1d4ed8', border: '#60a5fa' },
                  hover: { background: '#173059', border: '#38bdf8' }
                },
                font: { color: '#f8fafc', face: 'Inter', size: 14, bold: true },
                margin: 12,
                borderWidth: 2,
                shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 6, x: 0, y: 2 }
              });
            } else {
              (c.modules || []).forEach(mId => {
                const mod = (data.modules || []).find(m => m.id === mId);
                const inCycle = cyclesSet.has(mId) || (mod && mod.role === 'CYCLE_MEMBER');
                const role = mod ? mod.role : 'MODULE';
                const col = getModuleRoleColors(role, inCycle);

                nodes.push({
                  id: `mod:${mId}`,
                  label: mId.split('/').pop(),
                  title: `${mId}\\nRole: ${inCycle ? 'CYCLE_MEMBER' : role}`,
                  shape: 'box',
                  color: {
                    background: col.background,
                    border: col.border,
                    highlight: { background: col.highlightBg, border: col.highlightBorder },
                    hover: { background: col.hoverBg, border: col.hoverBorder }
                  },
                  font: { color: col.text, face: 'Fira Code', size: 11, bold: true },
                  margin: 8,
                  borderWidth: 2,
                  shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 5, x: 0, y: 2 }
                });
              });
            }
          });

          (data.component_edges || []).forEach(e => {
            const srcUnfolded = unfoldedComponents.has(e.source);
            const tgtUnfolded = unfoldedComponents.has(e.target);
            if (!srcUnfolded && !tgtUnfolded) {
              const edgeId = `comp:${e.source}->comp:${e.target}`;
              const defaultCol = { color: 'rgba(56, 189, 248, 0.45)', highlight: '#38bdf8', hover: '#38bdf8', inherit: 'from', opacity: 0.75 };
              const defaultW = Math.min(6, Math.max(1.5, Math.log2((e.weight || 1) + 1) * 1.5));
              edgeDefaultStyles.set(edgeId, { color: defaultCol, width: defaultW });
              edges.push({
                id: edgeId,
                from: `comp:${e.source}`,
                to: `comp:${e.target}`,
                arrows: { to: { enabled: true, scaleFactor: 0.8 } },
                color: { ...defaultCol },
                width: defaultW,
              });
            }
          });

          if (unfoldedComponents.size > 0) {
            (data.module_edges || []).forEach(e => {
              const srcMod = (data.modules || []).find(m => m.id === e.source);
              const srcInCycle = cyclesSet.has(e.source) || (srcMod && srcMod.role === 'CYCLE_MEMBER');
              const srcRole = srcInCycle ? 'CYCLE_MEMBER' : (srcMod ? srcMod.role : 'MODULE');
              const srcCol = getModuleRoleColors(srcRole, srcInCycle);
              const edgeId = `unfolded:mod:${e.source}->mod:${e.target}`;
              const defaultCol = { color: srcCol.border, highlight: srcCol.highlightBorder, hover: srcCol.hoverBorder, inherit: 'from', opacity: 0.75 };
              const defaultW = 1.5;
              edgeDefaultStyles.set(edgeId, { color: defaultCol, width: defaultW });
              edges.push({
                id: edgeId,
                from: `mod:${e.source}`,
                to: `mod:${e.target}`,
                arrows: { to: { enabled: true, scaleFactor: 0.75 } },
                color: { ...defaultCol },
                width: defaultW,
              });
            });
          }

        } else if (level === 'modules') {
          const visibleModuleSet = buildVisibleModuleSet();
          (data.modules || []).forEach(m => {
            if (!visibleModuleSet.has(m.id)) return;
            const inCycle = cyclesSet.has(m.id) || m.role === 'CYCLE_MEMBER';
            const roleKey = inCycle ? 'CYCLE_MEMBER' : (m.role || 'MODULE');
            const col = getModuleRoleColors(roleKey, inCycle);

            nodes.push({
              id: `mod:${m.id}`,
              label: m.path.split('/').pop(),
              title: `${m.path}\\nRole: ${roleKey}\\nIn: ${m.in_degree || 0} | Out: ${m.out_degree || 0}`,
              shape: 'box',
              color: {
                background: col.background,
                border: col.border,
                highlight: { background: col.highlightBg, border: col.highlightBorder },
                hover: { background: col.hoverBg, border: col.hoverBorder }
              },
              font: { color: col.text, face: "'Fira Code', monospace", size: 12, bold: true },
              margin: 9,
              borderWidth: 2,
              shadow: {
                enabled: true,
                color: 'rgba(0, 0, 0, 0.6)',
                size: 6,
                x: 0,
                y: 2
              }
            });
          });

          (data.module_edges || []).forEach(e => {
            if (!visibleModuleSet.has(e.source) || !visibleModuleSet.has(e.target)) return;
            const types = e.relationship_types || {};
            const isCall = Boolean(types.CALL);
            const isImport = Boolean(types.IMPORT);
            const isRef = Boolean(types.REFERENCE);

            if ((isCall && filterCalls) || (isImport && filterImports) || (isRef && filterRefs) || (!isCall && !isImport && !isRef)) {
              const srcMod = (data.modules || []).find(m => m.id === e.source);
              const tgtMod = (data.modules || []).find(m => m.id === e.target);
              const srcInCycle = cyclesSet.has(e.source) || (srcMod && srcMod.role === 'CYCLE_MEMBER');
              const tgtInCycle = cyclesSet.has(e.target) || (tgtMod && tgtMod.role === 'CYCLE_MEMBER');
              const srcRole = srcInCycle ? 'CYCLE_MEMBER' : (srcMod ? srcMod.role : 'MODULE');
              const tgtRole = tgtInCycle ? 'CYCLE_MEMBER' : (tgtMod ? tgtMod.role : 'MODULE');
              const srcCol = getModuleRoleColors(srcRole, srcInCycle);

              // Connecting lines colored accordingly to node role & cycle status
              let edgeColor = srcCol.border;
              let highlightColor = srcCol.highlightBorder;
              let hoverColor = srcCol.hoverBorder;

              // Prominently highlight circular dependency loops
              if (srcInCycle && tgtInCycle) {
                edgeColor = '#f43f5e';
                highlightColor = '#fb7185';
                hoverColor = '#fda4af';
              }

              const relNames = [];
              if (isCall) relNames.push('CALL');
              if (isImport) relNames.push('IMPORT');
              if (isRef) relNames.push('REFERENCE');
              const relLabel = relNames.join(' + ') || 'DEPENDENCY';

              const edgeId = `mod:${e.source}->mod:${e.target}`;
              const defaultCol = {
                color: edgeColor,
                highlight: highlightColor,
                hover: hoverColor,
                inherit: 'from',
                opacity: 0.75
              };
              const defaultW = (srcInCycle && tgtInCycle) ? 2.5 : Math.min(5, Math.max(1.3, Math.log2((e.weight || 1) + 1) * 1.5));
              edgeDefaultStyles.set(edgeId, { color: defaultCol, width: defaultW });

              edges.push({
                id: edgeId,
                from: `mod:${e.source}`,
                to: `mod:${e.target}`,
                arrows: {
                  to: { enabled: true, scaleFactor: 0.8 }
                },
                color: { ...defaultCol },
                width: defaultW,
                title: `${e.source.split('/').pop()} (${srcRole}) ➔ ${e.target.split('/').pop()} (${tgtRole}) [${relLabel}]`
              });
            }
          });

        } else if (level === 'symbols') {
          const symbolNodesSet = new Set();
          const symbolEdges = [];

          (data.cross_references || []).slice(0, 100).forEach(xr => {
            const srcNodeId = `sym:${xr.source_file}:${xr.scope || 'caller'}`;
            const tgtNodeId = `sym:${xr.target_file}:${xr.symbol}`;

            if (!symbolNodesSet.has(srcNodeId)) {
              symbolNodesSet.add(srcNodeId);
              nodes.push({
                id: srcNodeId,
                label: `${xr.source_file.split('/').pop()}\\n${xr.scope || 'call'}()`,
                shape: 'ellipse',
                color: { background: '#0e1e38', border: '#38bdf8', highlight: { background: '#1d4ed8', border: '#60a5fa' } },
                font: { color: '#e0f2fe', size: 10 },
              });
            }
            if (!symbolNodesSet.has(tgtNodeId)) {
              symbolNodesSet.add(tgtNodeId);
              nodes.push({
                id: tgtNodeId,
                label: `${xr.target_file.split('/').pop()}\\n ${xr.symbol}`,
                shape: 'box',
                color: { background: '#072e21', border: '#10b981', highlight: { background: '#0c583f', border: '#34d399' } },
                font: { color: '#34d399', face: 'Fira Code', size: 10 },
              });
            }

            const edgeId = `sym:${srcNodeId}->${tgtNodeId}`;
            const defaultCol = { color: 'rgba(52, 211, 153, 0.5)', highlight: '#34d399', hover: '#34d399', inherit: 'from', opacity: 0.75 };
            const defaultW = 1.0;
            edgeDefaultStyles.set(edgeId, { color: defaultCol, width: defaultW });

            symbolEdges.push({
              id: edgeId,
              from: srcNodeId,
              to: tgtNodeId,
              arrows: { to: { enabled: true, scaleFactor: 0.75 } },
              color: { ...defaultCol },
              width: defaultW,
            });
          });

          edges.push(...symbolEdges);
        }

        return { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
      }

      function initOrFitNetwork() {
        if (!network) {
          const graphData = buildGraphDataSet(currentLevel);
          const options = {
            physics: {
              solver: 'forceAtlas2Based',
              forceAtlas2Based: {
                gravitationalConstant: -38,
                centralGravity: 0.01,
                springLength: 90,
                springConstant: 0.08,
              },
              stabilization: { iterations: 120 },
            },
            interaction: {
              hover: true,
              tooltipDelay: 100,
              zoomView: true,
              dragView: true,
            },
          };
          network = new vis.Network(container, graphData, options);

          // Progressive Greying: When node is selected, dim unrelated nodes!
          network.on('click', function(params) {
            if (params.nodes.length > 0) {
              const clickedId = params.nodes[0];
              if (clickedId.startsWith('mod:')) {
                  const mId = clickedId.replace('mod:', '');
                  window.selectModule(mId);
              }
              applyUnrelatedNodeGreying(clickedId);
            } else {
              selectedNodeId = null;
              applyTextFilter();
            }
          });

        } else {
          network.fit({ animation: { duration: 400 } });
        }
      }


      let currentRoleFilter = 'ALL';

      document.querySelectorAll('#graph-role-filters .pill-opt').forEach(pill => {
        pill.addEventListener('click', () => {
          document.querySelectorAll('#graph-role-filters .pill-opt').forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          currentRoleFilter = pill.dataset.role;
          applyTextFilter();
        });
      });

      document.getElementById('graph-text-filter').addEventListener('input', applyTextFilter);

      function applyTextFilter() {
        if (!network) return;
        const query = document.getElementById('graph-text-filter').value.trim();
        
        let regex = null;
        if (query) {
          try {
            regex = new RegExp(query, 'i');
          } catch (e) {
            // invalid regex, fallback to string includes
          }
        }

        const isFilterActive = (currentRoleFilter !== 'ALL') || Boolean(query);
        const allNodes = network.body.data.nodes.get();
        const matchingNodeIds = new Set();
        const updates = allNodes.map(n => {
          let matchesQuery = true;
          let matchesRole = true;

          if (query && n.label) {
             if (regex) {
               matchesQuery = regex.test(n.label);
             } else {
               matchesQuery = n.label.toLowerCase().includes(query.toLowerCase());
             }
          } else if (query && !n.label) {
             matchesQuery = false;
          }

          if (currentRoleFilter !== 'ALL' && n.id.startsWith('mod:')) {
            const mId = n.id.replace('mod:', '');
            const mod = (data.modules || []).find(m => m.id === mId);
            if (currentRoleFilter === 'CYCLE') {
              if (!cyclesSet.has(mId) && (!mod || mod.role !== 'CYCLE_MEMBER')) matchesRole = false;
            } else if (mod && mod.role !== currentRoleFilter) {
              matchesRole = false;
            }
          }

          if (matchesQuery && matchesRole) {
            matchingNodeIds.add(n.id);
            return { id: n.id, opacity: 1.0 };
          } else {
            return { id: n.id, opacity: 0.12 };
          }
        });
        network.body.data.nodes.update(updates);

        // Grey out connecting wires of others!
        const allEdges = network.body.data.edges.get();
        const edgeUpdates = allEdges.map(e => {
          const defaults = edgeDefaultStyles.get(e.id) || {
            color: { inherit: 'from', opacity: 0.75 },
            width: 1.3
          };

          if (!isFilterActive) {
            return {
              id: e.id,
              color: { ...defaults.color },
              width: defaults.width
            };
          }

          const fromMatches = matchingNodeIds.has(e.from);
          const toMatches = matchingNodeIds.has(e.to);

          let edgeMatches = false;
          if (currentRoleFilter === 'CYCLE') {
            edgeMatches = fromMatches && toMatches;
          } else if (currentRoleFilter === 'ENTRY_CANDIDATE') {
            edgeMatches = fromMatches;
          } else if (currentRoleFilter === 'LEAF') {
            edgeMatches = toMatches;
          } else {
            edgeMatches = fromMatches || toMatches;
          }

          if (edgeMatches) {
            return {
              id: e.id,
              color: { ...defaults.color },
              width: defaults.width
            };
          } else {
            return {
              id: e.id,
              color: {
                color: 'rgba(100, 100, 100, 0.06)',
                highlight: 'rgba(100, 100, 100, 0.15)',
                hover: 'rgba(100, 100, 100, 0.15)',
                inherit: false,
                opacity: 0.06
              },
              width: 1
            };
          }
        });
        network.body.data.edges.update(edgeUpdates);
      }

      function applyUnrelatedNodeGreying(focusNodeId) {
        if (!network) return;
        const connectedNodes = new Set(network.getConnectedNodes(focusNodeId));
        connectedNodes.add(focusNodeId);

        const allNodes = network.body.data.nodes.get();
        const updates = allNodes.map(n => {
          if (connectedNodes.has(n.id)) {
            return { id: n.id, opacity: 1.0 };
          } else {
            return { id: n.id, opacity: 0.12 }; // Dimmed to eliminate noise!
          }
        });
        network.body.data.nodes.update(updates);

        const allEdges = network.body.data.edges.get();
        const edgeUpdates = allEdges.map(e => {
          const defaults = edgeDefaultStyles.get(e.id) || {
            color: { inherit: 'from', opacity: 0.75 },
            width: 1.3
          };
          if (e.from === focusNodeId || e.to === focusNodeId) {
            return {
              id: e.id,
              color: { ...defaults.color, opacity: 1.0 },
              width: Math.max(defaults.width, 2)
            };
          } else {
            return {
              id: e.id,
              color: {
                color: 'rgba(100, 100, 100, 0.06)',
                highlight: 'rgba(100, 100, 100, 0.15)',
                hover: 'rgba(100, 100, 100, 0.15)',
                inherit: false,
                opacity: 0.06
              },
              width: 1
            };
          }
        });
        network.body.data.edges.update(edgeUpdates);
      }

      function resetNodeOpacities() {
        if (!network) return;
        const allNodes = network.body.data.nodes.get();
        const updates = allNodes.map(n => ({ id: n.id, opacity: 1.0 }));
        network.body.data.nodes.update(updates);

        const allEdges = network.body.data.edges.get();
        const edgeUpdates = allEdges.map(e => {
          const defaults = edgeDefaultStyles.get(e.id) || {
            color: { inherit: 'from', opacity: 0.75 },
            width: 1.3
          };
          return {
            id: e.id,
            color: { ...defaults.color },
            width: defaults.width
          };
        });
        network.body.data.edges.update(edgeUpdates);
      }

      function updateNetworkData() {
        if (network) {
          const graphData = buildGraphDataSet(currentLevel);
          network.setData(graphData);
          applyTextFilter();
        }
      }

      window.toggleUnfold = function(compId) {
        if (unfoldedComponents.has(compId)) {
          unfoldedComponents.delete(compId);
        } else {
          unfoldedComponents.add(compId);
        }
        updateNetworkData();
        onCanvasNodeSelected(`comp:${compId}`);
      };

      window.inspectComponent = function(compId) {
        switchTab('graph');
        unfoldedComponents.add(compId);
        updateNetworkData();
        setTimeout(() => onCanvasNodeSelected(`comp:${compId}`), 100);
      };

      window.jumpToGraphNode = function(modId) {
        switchTab('graph');
        currentLevel = 'modules';
        const mod = (data.modules || []).find(m => m.id === modId);
        if (mod) {
          visibleComponents.add(moduleGroup(mod));
          renderCompVisPanel();
        }
        updateNetworkData();
        setTimeout(() => {
          if (network) {
            network.focus(`mod:${modId}`, { scale: 1.2, animation: { duration: 500 } });
            network.selectNodes([`mod:${modId}`]);
            applyUnrelatedNodeGreying(`mod:${modId}`);
          }
        }, 200);
      };

      ['chk-filter-calls', 'chk-filter-imports', 'chk-filter-refs'].forEach(id => {
        document.getElementById(id).addEventListener('change', updateNetworkData);
      });

      // -------------------------------------------------------------
      // Component visibility toolbar (graph view only)
      // -------------------------------------------------------------
      const compVisPanel = document.getElementById('comp-vis-panel');
      const compVisCountEl = document.getElementById('comp-vis-count');
      const toggleCompVisBtn = document.getElementById('btn-toggle-comp-vis');
      let compVisOpen = false;

      function refreshCompVisCounter() {
        const multiComps = (data.components || []).filter(c => !singletonCompIds.has(c.id));
        const hasStandalone = (data.modules || []).some(m => moduleGroup(m) === VIS_STANDALONE);
        const total = multiComps.length + (hasStandalone ? 1 : 0);
        let visible = multiComps.filter(c => visibleComponents.has(c.id)).length;
        if (hasStandalone && visibleComponents.has(VIS_STANDALONE)) visible += 1;
        compVisCountEl.textContent = `${visible}/${total} visible`;
      }

      function renderCompVisPanel() {
        const multiComps = (data.components || []).filter(c => !singletonCompIds.has(c.id));
        const standaloneCount = (data.modules || []).filter(m => moduleGroup(m) === VIS_STANDALONE).length;
        let html = '';
        if (multiComps.length) {
          html += '<div class="comp-vis-group-label">Components</div>';
          html += multiComps.map(c => `
            <label class="comp-vis-item">
              <input type="checkbox" data-group="${c.id}" ${visibleComponents.has(c.id) ? 'checked' : ''}>
              <span class="comp-vis-name" title="${(c.modules || []).join(', ')}">${compVisTitle(c)}</span>
              <span class="comp-vis-n">${(c.modules || []).length}</span>
            </label>
          `).join('');
        }
        html += '<div class="comp-vis-group-label">Standalone</div>';
        html += `<label class="comp-vis-item">
              <input type="checkbox" data-group="${VIS_STANDALONE}" ${visibleComponents.has(VIS_STANDALONE) ? 'checked' : ''}>
              <span class="comp-vis-name" title="Single files that did not group with anything">Standalone files</span>
              <span class="comp-vis-n">${standaloneCount}</span>
            </label>`;
        if (!multiComps.length && !standaloneCount) {
          html = '<div class="vis-empty">No components to hide.</div>';
        }
        compVisPanel.innerHTML = html;
        refreshCompVisCounter();
      }

      toggleCompVisBtn.addEventListener('click', () => {
        compVisOpen = !compVisOpen;
        compVisPanel.style.display = compVisOpen ? 'block' : 'none';
        if (compVisOpen) renderCompVisPanel();
      });
      document.addEventListener('click', (e) => {
        const visControls = document.querySelector('.vis-controls');
        if (compVisOpen && visControls && !visControls.contains(e.target)) {
          compVisOpen = false;
          compVisPanel.style.display = 'none';
        }
      });
      compVisPanel.addEventListener('change', (e) => {
        const box = e.target;
        if (box && box.dataset && box.dataset.group) {
          if (box.checked) visibleComponents.add(box.dataset.group);
          else visibleComponents.delete(box.dataset.group);
          renderCompVisPanel();
          updateNetworkData();
        }
      });
      document.getElementById('btn-comp-vis-all').addEventListener('click', () => {
        visibleComponents.clear();
        (data.components || []).forEach(c => visibleComponents.add(c.id));
        visibleComponents.add(VIS_STANDALONE);
        renderCompVisPanel();
        updateNetworkData();
      });
      document.getElementById('btn-comp-vis-none').addEventListener('click', () => {
        visibleComponents.clear();
        renderCompVisPanel();
        updateNetworkData();
      });
      renderCompVisPanel();

      // -------------------------------------------------------------
      // 7. Global Search Modal (Cmd+K)
      // -------------------------------------------------------------
      const searchOverlay = document.getElementById('search-modal-overlay');
      const searchInput = document.getElementById('global-search-input');
      const searchResultsList = document.getElementById('search-results-list');

      function openSearch() {
        searchOverlay.classList.add('active');
        searchInput.value = '';
        searchInput.focus();
        renderSearchResults('');
      }

      function closeSearch() {
        searchOverlay.classList.remove('active');
      }

      document.getElementById('open-search-btn').addEventListener('click', openSearch);
      searchOverlay.addEventListener('click', function(e) {
        if (e.target === searchOverlay) closeSearch();
      });

      window.addEventListener('keydown', function(e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          if (searchOverlay.classList.contains('active')) closeSearch();
          else openSearch();
        } else if (e.key === 'Escape' && searchOverlay.classList.contains('active')) {
          closeSearch();
        }
      });

      searchInput.addEventListener('input', function() {
        renderSearchResults(this.value.trim().toLowerCase());
      });

      function renderSearchResults(query) {
        const results = [];
        (data.components || []).forEach(c => {
          if (!query || c.name.toLowerCase().includes(query)) {
            results.push({ type: 'Component', label: `${c.name}`, sub: `${c.modules.length} modules`, action: () => { closeSearch(); window.inspectComponent(c.id); } });
          }
        });
        (data.modules || []).forEach(m => {
          if (!query || m.path.toLowerCase().includes(query) || m.role.toLowerCase().includes(query)) {
            results.push({ type: 'Module', label: `${m.name}`, sub: `${m.path} (${m.role})`, action: () => { closeSearch(); window.selectModule(m.id); } });
          }
        });
        (data.modules || []).forEach(m => {
          (m.functions || []).forEach(f => {
            if (query && f.name.toLowerCase().includes(query)) {
              results.push({ type: 'Function', label: `${f.name}()`, sub: `in ${m.path}`, action: () => { closeSearch(); window.selectModule(m.id); } });
            }
          });
        });

        if (results.length === 0) {
          searchResultsList.innerHTML = '<div style="padding: 16px; color: var(--text-muted); font-size: 13px; text-align: center;">No matches found</div>';
          return;
        }

        searchResultsList.innerHTML = results.slice(0, 8).map((r, i) => `
          <div class="search-res-item" id="search-item-${i}">
            <div>
              <div style="font-weight: 600; font-size: 13px; color: #fff;">${r.label}</div>
              <div style="font-size: 11px; color: var(--text-muted); font-family: 'Fira Code', monospace;">${r.sub}</div>
            </div>
            <span style="font-size: 10px; text-transform: uppercase; color: var(--accent-blue); background: rgba(184,184,184,0.1); padding: 2px 6px; border-radius: 4px;">${r.type}</span>
          </div>
        `).join('');

        results.slice(0, 8).forEach((r, i) => {
          document.getElementById(`search-item-${i}`).addEventListener('click', r.action);
        });
      }

    })();
  </script>
</body>
</html>
"""