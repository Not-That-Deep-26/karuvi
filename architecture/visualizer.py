"""
Karuvi Living Codebase Atlas — Unified Web Visualizer
=====================================================

Generates a standalone, interactive, dark-mode Single Page Web Application
embodying Karuvi's 3 core modes:
1. 🗺️ Architecture: Calm, deterministic component-level model and flows.
2. 🕸️ Graph Explorer: Multi-level interactive canvas with dynamic cluster unfolding.
3. 📖 Knowledge / Docs: Deterministic DeepWiki-style factual documentation.
4. 📁 Code Explorer: File tree with structural role badges and AST flow.
5. ◉ Overview: Executive codebase dashboard with entry-point guidance.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from architecture.analyzer import ArchitectureAnalyzer
from architecture.documentation import generate_architecture_markdown
from architecture.models import ArchitectureModel


def build_unified_payload(
    repo_builder: Any,
    arch_model: ArchitectureModel | None = None,
) -> dict[str, Any]:
    """
    Assembles a unified data contract combining Stage 1 (AST, symbols, references, cycles)
    and Stage 2 (components, module graph, metrics, roles, entrypoints, flows, documentation).
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

    # 2. Module list with enhanced architectural metadata
    modules_list = []
    for mod_id, mod in arch_model.modules.items():
        # Get line count and AST info if available in repo_builder
        node_raw = repo_builder.nodes.get(mod_id)
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
        if mod_id in repo_builder.parsed:
            m_parsed = repo_builder.parsed[mod_id]
            from returns import deptree_to_dict
            code_flow = deptree_to_dict(m_parsed.code_flow)
            for f in m_parsed.functions:
                functions_data.append({
                    "name": f.name,
                    "signature": getattr(f, "signature", ""),
                    "uuid": getattr(f, "uuid", None),
                })
            for c in m_parsed.classes:
                cls_methods = [
                    {"name": m.name, "signature": getattr(m, "signature", ""), "uuid": getattr(m, "uuid", None)}
                    for m in c.functions
                ]
                classes_data.append({
                    "name": c.name,
                    "uuid": getattr(c, "uuid", None),
                    "methods": cls_methods,
                })

        role = arch_model.roles.get(mod_id, "MODULE")

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

    # 5. Raw Symbol References
    cross_refs = getattr(repo_builder, "cross_references", [])

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
        "total_cycles": len(getattr(repo_builder, "cycles", [])),
        "circular_dependencies": len(getattr(repo_builder, "cycles", [])),
    }

    # 7. Precomputed Markdown Documentation
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
        "cycles": getattr(repo_builder, "cycles", []),
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
    # Escape closing script tags to avoid breaking the inline script block
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
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {
      --bg-canvas: #07090e;
      --bg-surface: #0e131f;
      --bg-card: #141b2d;
      --bg-card-hover: #1c263e;
      --border: #232d42;
      --border-subtle: #172033;
      --border-glow: rgba(56, 189, 248, 0.35);
      
      --text: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      
      --accent-blue: #38bdf8;
      --accent-cyan: #22d3ee;
      --accent-purple: #c084fc;
      --accent-green: #4ade80;
      --accent-amber: #fbbf24;
      --accent-rose: #fb7185;
      
      --role-entry: #38bdf8;
      --role-bridge: #fbbf24;
      --role-hub: #c084fc;
      --role-leaf: #4ade80;
      --role-cycle: #fb7185;
      --role-isolated: #64748b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-canvas);
      color: var(--text);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* Top App Bar */
    header {
      height: 54px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      z-index: 100;
      flex-shrink: 0;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 17px;
      letter-spacing: -0.02em;
    }
    .brand .logo {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      font-weight: 800;
      font-size: 19px;
    }
    .repo-pill {
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.25);
      color: var(--accent-blue);
      font-size: 12px;
      padding: 3px 10px;
      border-radius: 9999px;
      font-family: 'Fira Code', monospace;
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .search-btn {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }
    .search-btn:hover {
      border-color: var(--accent-blue);
      color: var(--text);
    }
    .search-btn kbd {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      font-family: inherit;
    }

    /* Main Container */
    .app-body {
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }

    /* Left Sidebar Navigation */
    nav.sidebar {
      width: 220px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      padding: 16px 10px;
      gap: 6px;
      z-index: 20;
    }
    .nav-label {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      padding: 8px 10px 4px;
    }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 12px;
      border-radius: 8px;
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }
    .nav-item:hover {
      background: var(--bg-card-hover);
      color: var(--text);
    }
    .nav-item.active {
      background: rgba(56, 189, 248, 0.12);
      border-color: rgba(56, 189, 248, 0.35);
      color: var(--accent-blue);
      font-weight: 600;
    }
    .nav-item .icon {
      font-size: 16px;
      width: 20px;
      display: inline-flex;
      justify-content: center;
    }
    .sidebar-footer {
      margin-top: auto;
      padding-top: 12px;
      border-top: 1px solid var(--border-subtle);
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding-left: 10px;
    }

    /* Workspace Content Area */
    main.workspace {
      flex: 1;
      overflow: hidden;
      position: relative;
      background: var(--bg-canvas);
      display: flex;
    }

    /* Common View Panels */
    .tab-view {
      position: absolute;
      inset: 0;
      display: none;
      overflow-y: auto;
      padding: 24px 32px;
    }
    .tab-view.active {
      display: block;
    }

    /* VIEW 1: OVERVIEW DASHBOARD */
    .overview-hero {
      margin-bottom: 28px;
    }
    .overview-hero h1 {
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.03em;
      margin-bottom: 6px;
      background: linear-gradient(135deg, #ffffff, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .overview-hero p {
      color: var(--text-secondary);
      font-size: 14px;
    }
    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .stat-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      transition: transform 0.2s, border-color 0.2s;
    }
    .stat-card:hover {
      transform: translateY(-2px);
      border-color: var(--accent-blue);
    }
    .stat-val {
      font-size: 28px;
      font-weight: 800;
      color: var(--text);
      letter-spacing: -0.02em;
    }
    .stat-lbl {
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 500;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .banner-entrypoint {
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(192, 132, 252, 0.08));
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 14px;
      padding: 20px 24px;
      margin-bottom: 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }
    .banner-content h3 {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--accent-blue);
      letter-spacing: 0.06em;
      margin-bottom: 6px;
    }
    .banner-content .mod-title {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
      font-family: 'Fira Code', monospace;
      margin-bottom: 6px;
    }
    .banner-content p {
      font-size: 13px;
      color: var(--text-secondary);
    }
    .btn-primary {
      background: var(--accent-blue);
      color: #04101e;
      border: none;
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }
    .btn-primary:hover {
      background: #7dd3fc;
      transform: translateY(-1px);
    }

    /* VIEW 2: ARCHITECTURE CARDS & FLOWS */
    .section-title {
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .comp-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 18px;
      margin-bottom: 32px;
    }
    .comp-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      cursor: pointer;
      transition: all 0.2s ease;
      position: relative;
      overflow: hidden;
    }
    .comp-card:hover {
      border-color: var(--accent-blue);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      transform: translateY(-2px);
    }
    .comp-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }
    .comp-name {
      font-size: 16px;
      font-weight: 700;
      color: var(--text);
    }
    .confidence-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 9999px;
    }
    .confidence-high { background: rgba(74, 222, 128, 0.15); color: var(--accent-green); border: 1px solid rgba(74, 222, 128, 0.3); }
    .confidence-med { background: rgba(251, 191, 36, 0.15); color: var(--accent-amber); border: 1px solid rgba(251, 191, 36, 0.3); }
    .confidence-low { background: rgba(251, 113, 133, 0.15); color: var(--accent-rose); border: 1px solid rgba(251, 113, 133, 0.3); }
    .comp-modules-list {
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'Fira Code', monospace;
      margin-top: 10px;
      line-height: 1.6;
    }
    .flows-container {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 32px;
    }
    .flow-row {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      gap: 14px;
      font-size: 13px;
    }
    .flow-node-badge {
      background: var(--bg-card);
      border: 1px solid var(--border);
      padding: 4px 12px;
      border-radius: 6px;
      font-weight: 600;
      color: var(--text);
    }
    .flow-arrow {
      color: var(--accent-blue);
      font-weight: 700;
    }

    /* VIEW 3: GRAPH EXPLORER (CANVAS + CONTROLS + INSPECTOR) */
    #tab-graph {
      padding: 0;
      overflow: hidden;
    }
    .graph-layout {
      position: absolute;
      inset: 0;
      display: flex;
    }
    .graph-canvas-container {
      flex: 1;
      height: 100%;
      position: relative;
    }
    #network-canvas {
      width: 100%;
      height: 100%;
      background: radial-gradient(circle at center, #0f1524 0%, #07090e 100%);
    }
    .graph-floating-controls {
      position: absolute;
      top: 16px;
      left: 16px;
      background: rgba(14, 19, 31, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 16px;
      z-index: 10;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }
    .pill-group {
      display: flex;
      align-items: center;
      background: var(--bg-canvas);
      padding: 3px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }
    .pill-opt {
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s;
    }
    .pill-opt.active {
      background: var(--accent-blue);
      color: #030d1a;
    }
    .filter-checkboxes {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 11px;
      color: var(--text-secondary);
    }
    .filter-checkboxes label {
      display: flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
    }
    .graph-inspector {
      width: 320px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      padding: 20px;
      overflow-y: auto;
      z-index: 10;
    }
    .inspector-title {
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 6px;
      word-break: break-all;
    }
    .inspector-sub {
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 16px;
    }
    .inspector-prop {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 12px;
    }
    .inspector-prop .lbl { color: var(--text-muted); }
    .inspector-prop .val { font-weight: 600; color: var(--text); }
    .role-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* VIEW 4: CODE EXPLORER */
    #tab-code {
      padding: 0;
      overflow: hidden;
    }
    .code-layout {
      position: absolute;
      inset: 0;
      display: flex;
    }
    .file-tree-pane {
      width: 280px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      overflow-y: auto;
      padding: 16px 12px;
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
      gap: 8px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: all 0.15s;
    }
    .file-tree-item:hover {
      background: var(--bg-card-hover);
      color: var(--text);
    }
    .file-tree-item.active {
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent-blue);
      font-weight: 600;
    }
    .file-detail-pane {
      flex: 1;
      overflow-y: auto;
      padding: 24px 32px;
    }

    /* VIEW 5: KNOWLEDGE DOCS */
    .docs-container {
      max-width: 860px;
      margin: 0 auto;
      line-height: 1.7;
    }
    .docs-container h1 { font-size: 28px; font-weight: 800; margin-bottom: 16px; color: #fff; }
    .docs-container h2 { font-size: 20px; font-weight: 700; margin: 28px 0 12px; color: var(--accent-blue); border-bottom: 1px solid var(--border); padding-bottom: 6px; }
    .docs-container h3 { font-size: 16px; font-weight: 600; margin: 20px 0 8px; color: var(--accent-purple); }
    .docs-container p { font-size: 14px; color: var(--text-secondary); margin-bottom: 14px; }
    .docs-container ul { margin-left: 20px; margin-bottom: 16px; font-size: 14px; color: var(--text-secondary); }
    .docs-container code { font-family: 'Fira Code', monospace; background: var(--bg-surface); border: 1px solid var(--border); padding: 2px 6px; border-radius: 4px; font-size: 12px; color: var(--accent-cyan); }

    /* Search Modal (Cmd+K) */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      z-index: 1000;
      display: none;
      align-items: flex-start;
      justify-content: center;
      padding-top: 100px;
    }
    .modal-overlay.active { display: flex; }
    .search-modal {
      width: 580px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
    }
    .search-input-wrap {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .search-input-wrap input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: #fff;
      font-size: 16px;
      font-family: inherit;
    }
    .search-results {
      max-height: 360px;
      overflow-y: auto;
      padding: 10px;
    }
    .search-res-item {
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: background 0.15s;
    }
    .search-res-item:hover, .search-res-item.selected {
      background: var(--bg-card-hover);
    }
  </style>
</head>
<body>

  <!-- Top App Header -->
  <header>
    <div class="brand">
      <span class="logo">⚡ KARUVI</span>
      <span style="color: var(--text-muted); font-size: 14px;">/</span>
      <span id="header-repo-name" class="repo-pill">Repository</span>
    </div>
    <div class="header-actions">
      <button class="search-btn" id="open-search-btn">
        <span>🔍 Search Codebase</span>
        <kbd>⌘K</kbd>
      </button>
    </div>
  </header>

  <div class="app-body">
    <!-- Left Navigation Sidebar -->
    <nav class="sidebar">
      <div class="nav-label">Modes</div>
      <div class="nav-item active" data-tab="overview">
        <span class="icon">◉</span>
        <span>Overview</span>
      </div>
      <div class="nav-item" data-tab="architecture">
        <span class="icon">🗺️</span>
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
      <div class="nav-item" data-tab="docs">
        <span class="icon">📖</span>
        <span>Knowledge Docs</span>
      </div>

      <div class="sidebar-footer">
        <span>Deterministic Architecture Engine</span>
        <span style="opacity: 0.6;">Karuvi v0.2.0 • Evidence Grounded</span>
      </div>
    </nav>

    <!-- Main Views Workspace -->
    <main class="workspace">

      <!-- VIEW 1: OVERVIEW -->
      <div class="tab-view active" id="tab-overview">
        <div class="overview-hero">
          <h1>Good morning, here's your codebase.</h1>
          <p>Deterministic architecture reconstruction, topological graph analysis, and structural evidence.</p>
        </div>

        <div class="stat-grid" id="stats-container">
          <!-- Stat cards injected dynamically -->
        </div>

        <!-- Start Here Entry Point Banner -->
        <div class="banner-entrypoint" id="entry-point-banner">
          <div class="banner-content">
            <h3>🚪 Recommended Starting Point</h3>
            <div class="mod-title" id="entry-mod-name">loading...</div>
            <p id="entry-mod-desc">This module sits structurally high and can reach major portions of the repository.</p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn-primary" id="btn-jump-arch">Explore Architecture ➔</button>
            <button class="btn-primary" style="background: var(--bg-card); color: #fff; border: 1px solid var(--border);" id="btn-jump-code">View Code ➔</button>
          </div>
        </div>

        <!-- Key Architectural Insights -->
        <div class="section-title">🌉 Structural Bridges & Central Modules</div>
        <div id="bridges-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 30px;">
          <!-- Bridges injected -->
        </div>
      </div>

      <!-- VIEW 2: ARCHITECTURE -->
      <div class="tab-view" id="tab-architecture">
        <div class="section-title">🏛️ Discovered Architectural Components</div>
        <div class="comp-grid" id="arch-components-grid">
          <!-- Component cards injected -->
        </div>

        <div class="section-title">🌊 High-Level Architectural Flows</div>
        <div class="flows-container" id="arch-flows-container">
          <!-- Flows injected -->
        </div>
      </div>

      <!-- VIEW 3: GRAPH EXPLORER WITH UNICLUSTER UNFOLDING -->
      <div class="tab-view" id="tab-graph">
        <div class="graph-layout">
          <div class="graph-canvas-container">
            <div class="graph-floating-controls">
              <div class="pill-group" id="graph-level-pills">
                <div class="pill-opt active" data-level="architecture">Architecture (5-15)</div>
                <div class="pill-opt" data-level="modules">Modules (All)</div>
                <div class="pill-opt" data-level="symbols">Symbols (Deep)</div>
              </div>
              <div class="filter-checkboxes">
                <label><input type="checkbox" id="chk-filter-calls" checked> Calls</label>
                <label><input type="checkbox" id="chk-filter-imports" checked> Imports</label>
                <label><input type="checkbox" id="chk-filter-refs" checked> References</label>
              </div>
              <button class="btn-primary" style="padding: 4px 12px; font-size: 11px;" id="btn-fold-all">Fold All</button>
            </div>
            <div id="network-canvas"></div>
          </div>
          <div class="graph-inspector" id="graph-inspector">
            <div class="inspector-title" id="insp-title">Select a Node</div>
            <div class="inspector-sub" id="insp-sub">Click any component or module in the canvas to inspect evidence and unfold abstractions.</div>
            <div id="insp-body"></div>
          </div>
        </div>
      </div>

      <!-- VIEW 4: CODE EXPLORER -->
      <div class="tab-view" id="tab-code">
        <div class="code-layout">
          <div class="file-tree-pane" id="code-file-tree">
            <!-- Files injected -->
          </div>
          <div class="file-detail-pane" id="code-file-detail">
            <div style="color: var(--text-muted); font-size: 14px;">Select a file on the left to inspect its structural role, components, and declared symbols.</div>
          </div>
        </div>
      </div>

      <!-- VIEW 5: KNOWLEDGE DOCS -->
      <div class="tab-view" id="tab-docs">
        <div class="docs-container" id="docs-content">
          <!-- Documentation markdown rendered dynamically -->
        </div>
      </div>

    </main>
  </div>

  <!-- Search Modal (Cmd+K) -->
  <div class="modal-overlay" id="search-modal-overlay">
    <div class="search-modal">
      <div class="search-input-wrap">
        <span>🔍</span>
        <input type="text" id="global-search-input" placeholder="Search components, modules, symbols, or roles... (Esc to close)">
      </div>
      <div class="search-results" id="search-results-list"></div>
    </div>
  </div>

  <!-- Embedded Unified Karuvi Payload -->
  <script>
    window.KARUVI_DATA = __KARUVI_PAYLOAD__;
    window.__KARUVI_DATA__ = window.KARUVI_DATA;
  </script>

  <!-- Core Interactive Application Script -->
  <script>
    (function() {
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

      document.getElementById('btn-jump-arch').addEventListener('click', () => switchTab('architecture'));
      document.getElementById('btn-jump-code').addEventListener('click', () => switchTab('code'));

      // -------------------------------------------------------------
      // 1. Render Overview Tab
      // -------------------------------------------------------------
      const statsGrid = document.getElementById('stats-container');
      const stats = data.stats || {};
      const statItems = [
        { val: stats.total_modules || 0, lbl: 'Modules' },
        { val: stats.total_components || 0, lbl: 'Components' },
        { val: stats.total_symbols || 0, lbl: 'Symbols Indexed' },
        { val: stats.total_module_edges || 0, lbl: 'Inter-Module Edges' },
        { val: stats.total_cycles || 0, lbl: 'Circular Loops' },
      ];
      statsGrid.innerHTML = statItems.map(s => `
        <div class="stat-card">
          <div class="stat-val">${s.val}</div>
          <div class="stat-lbl">${s.lbl}</div>
        </div>
      `).join('');

      // Entry Point Banner
      if (data.entry_points && data.entry_points.length > 0) {
        const topEp = data.entry_points[0];
        document.getElementById('entry-mod-name').textContent = topEp.module;
        const ev = topEp.evidence || {};
        document.getElementById('entry-mod-desc').textContent = 
          `Scores highest in downstream reach with 0 cyclic blocks. Directly reaches ${ev.reachable_modules || 0} modules across ${ev.reachable_components || 0} architectural components.`;
      }

      // Bridges
      const bridgesContainer = document.getElementById('bridges-container');
      const bridgeMods = (data.modules || []).filter(m => m.role === 'BRIDGE' || m.role === 'HUB').slice(0, 4);
      if (bridgeMods.length > 0) {
        bridgesContainer.innerHTML = bridgeMods.map(m => `
          <div class="stat-card" style="cursor: pointer;" onclick="window.selectModule('${m.id}')">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span class="role-badge" style="background: rgba(251, 191, 36, 0.15); color: var(--accent-amber); border: 1px solid rgba(251, 191, 36, 0.3);">
                ${m.role === 'BRIDGE' ? '🌉 Bridge' : '⚡ Hub'}
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
      // 2. Render Architecture Tab
      // -------------------------------------------------------------
      const compGrid = document.getElementById('arch-components-grid');
      compGrid.innerHTML = (data.components || []).map(c => {
        const confPct = Math.round((c.confidence || 0) * 100);
        const confClass = confPct >= 70 ? 'confidence-high' : (confPct >= 40 ? 'confidence-med' : 'confidence-low');
        const sampleMods = (c.modules || []).slice(0, 3).map(m => m.split('/').pop()).join(', ');
        const extra = c.modules.length > 3 ? ` (+${c.modules.length - 3} more)` : '';
        return `
          <div class="comp-card" onclick="window.inspectComponent('${c.id}')">
            <div class="comp-card-header">
              <span class="comp-name">📦 ${c.name}</span>
              <span class="confidence-badge ${confClass}">${confPct}% confidence</span>
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">
              ${c.modules.length} module${c.modules.length === 1 ? '' : 's'} • ${(c.discovery_methods || []).join(', ')}
            </div>
            <div class="comp-modules-list">${sampleMods}${extra}</div>
          </div>
        `;
      }).join('');

      const flowsContainer = document.getElementById('arch-flows-container');
      if (data.flows && data.flows.length > 0) {
        flowsContainer.innerHTML = data.flows.map(f => {
          const pathHtml = f.path.map((step, idx) => `
            <span class="flow-node-badge">${step}</span>
            ${idx < f.path.length - 1 ? '<span class="flow-arrow">➔</span>' : ''}
          `).join('');
          return `
            <div class="flow-row">
              <div style="flex: 1; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                ${pathHtml}
              </div>
            </div>
          `;
        }).join('');
      } else {
        flowsContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No cross-component flows recorded.</div>';
      }

      // -------------------------------------------------------------
      // 3. Render Code Explorer Tab
      // -------------------------------------------------------------
      const fileTreePane = document.getElementById('code-file-tree');
      fileTreePane.innerHTML = (data.modules || []).map(m => `
        <div class="file-tree-item" id="tree-item-${m.id.replace(/[^a-zA-Z0-9]/g, '_')}" onclick="window.selectModule('${m.id}')">
          <span>📄</span>
          <span>${m.path}</span>
        </div>
      `).join('');

      window.selectModule = function(modId) {
        switchTab('code');
        const mod = (data.modules || []).find(m => m.id === modId);
        if (!mod) return;

        // Highlight in tree
        document.querySelectorAll('.file-tree-item').forEach(el => el.classList.remove('active'));
        const activeTreeEl = document.getElementById(`tree-item-${modId.replace(/[^a-zA-Z0-9]/g, '_')}`);
        if (activeTreeEl) activeTreeEl.classList.add('active');

        // Render detail pane
        const detailPane = document.getElementById('code-file-detail');
        const funcsHtml = (mod.functions || []).map(f => `
          <div style="padding: 6px 0; border-bottom: 1px solid var(--border-subtle); font-family: 'Fira Code', monospace; font-size: 12px;">
            <span style="color: var(--accent-green);">⚡ def</span> <strong>${f.name}</strong><span style="color: var(--text-muted);">${f.signature || '()'}</span>
          </div>
        `).join('');

        const classesHtml = (mod.classes || []).map(c => `
          <div style="padding: 8px 0; border-bottom: 1px solid var(--border-subtle);">
            <div style="font-family: 'Fira Code', monospace; font-size: 13px; color: var(--accent-purple);">🏷️ class <strong>${c.name}</strong></div>
            ${(c.methods || []).map(m => `
              <div style="padding-left: 16px; font-family: 'Fira Code', monospace; font-size: 11px; color: var(--text-secondary); margin-top: 4px;">
                ↳ <span style="color: var(--accent-green);">def</span> ${m.name}${m.signature || '()'}
              </div>
            `).join('')}
          </div>
        `).join('');

        detailPane.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <div>
              <h2 style="font-size: 22px; font-weight: 800; font-family: 'Fira Code', monospace; margin-bottom: 6px;">${mod.path}</h2>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span class="role-badge" style="background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); border: 1px solid rgba(56, 189, 248, 0.3);">
                  Component: ${mod.component_name}
                </span>
                <span class="role-badge" style="background: rgba(192, 132, 252, 0.15); color: var(--accent-purple); border: 1px solid rgba(192, 132, 252, 0.3);">
                  Role: ${mod.role}
                </span>
              </div>
            </div>
            <button class="btn-primary" onclick="window.jumpToGraphNode('${mod.id}')">View in Graph ➔</button>
          </div>

          <div class="stat-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 24px;">
            <div class="stat-card"><div class="stat-val" style="font-size: 20px;">${mod.line_count}</div><div class="stat-lbl">Lines of Code</div></div>
            <div class="stat-card"><div class="stat-val" style="font-size: 20px;">${mod.function_count}</div><div class="stat-lbl">Functions</div></div>
            <div class="stat-card"><div class="stat-val" style="font-size: 20px;">${mod.class_count}</div><div class="stat-lbl">Classes</div></div>
            <div class="stat-card"><div class="stat-val" style="font-size: 20px;">${mod.in_degree} / ${mod.out_degree}</div><div class="stat-lbl">In / Out Deg</div></div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px;">
            <div class="stat-card">
              <div style="font-weight: 700; margin-bottom: 10px; font-size: 13px; color: var(--accent-blue);">⬆ Upstream Dependents (${mod.incoming_modules.length})</div>
              <div style="font-size: 12px; font-family: 'Fira Code', monospace; line-height: 1.8;">
                ${mod.incoming_modules.length > 0 ? mod.incoming_modules.map(im => `<div>← ${im}</div>`).join('') : '<div style="color: var(--text-muted); font-size: 12px;">None (Entry/Root)</div>'}
              </div>
            </div>
            <div class="stat-card">
              <div style="font-weight: 700; margin-bottom: 10px; font-size: 13px; color: var(--accent-green);">⬇ Downstream Imports (${mod.outgoing_modules.length})</div>
              <div style="font-size: 12px; font-family: 'Fira Code', monospace; line-height: 1.8;">
                ${mod.outgoing_modules.length > 0 ? mod.outgoing_modules.map(om => `<div>→ ${om}</div>`).join('') : '<div style="color: var(--text-muted); font-size: 12px;">None (Leaf)</div>'}
              </div>
            </div>
          </div>

          <div class="section-title">Declared Symbols</div>
          <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 24px;">
            ${classesHtml || ''}
            ${funcsHtml || '<div style="color: var(--text-muted); font-size: 12px;">No top-level functions</div>'}
          </div>
        `;
      };

      // -------------------------------------------------------------
      // 4. Render Knowledge Docs Tab
      // -------------------------------------------------------------
      const docsContent = document.getElementById('docs-content');
      // Simple Markdown-to-HTML parser for the deterministic docs
      function renderMarkdown(md) {
        return md
          .replace(/^### (.*$)/gim, '<h3>$1</h3>')
          .replace(/^## (.*$)/gim, '<h2>$1</h2>')
          .replace(/^# (.*$)/gim, '<h1>$1</h1>')
          .replace(/\\*\\*(.*)\\*\\*/gim, '<strong>$1</strong>')
          .replace(/\\*(.*)\\*/gim, '<em>$1</em>')
          .replace(/`([^`]+)`/gim, '<code>$1</code>')
          .replace(/^\\- (.*$)/gim, '<ul><li>$1</li></ul>')
          .replace(/<\\/ul>\\s*<ul>/gim, '')
          .replace(/\\n\\n/gim, '<br>');
      }
      docsContent.innerHTML = renderMarkdown(data.documentation_md || '# Documentation');

      // -------------------------------------------------------------
      // 5. Graph Explorer with Unfolding Canvas (vis-network)
      // -------------------------------------------------------------
      let network = null;
      let currentLevel = 'architecture'; // 'architecture' | 'modules' | 'symbols'
      let unfoldedComponents = new Set();

      const container = document.getElementById('network-canvas');

      function buildGraphDataSet(level) {
        const nodes = [];
        const edges = [];
        const filterCalls = document.getElementById('chk-filter-calls').checked;
        const filterImports = document.getElementById('chk-filter-imports').checked;
        const filterRefs = document.getElementById('chk-filter-refs').checked;

        if (level === 'architecture') {
          // Add component nodes
          (data.components || []).forEach(c => {
            const isUnfolded = unfoldedComponents.has(c.id);
            if (!isUnfolded) {
              nodes.push({
                id: `comp:${c.id}`,
                label: `${c.name}\\n(${c.modules.length} modules)`,
                shape: 'box',
                color: {
                  background: '#1e293b',
                  border: '#38bdf8',
                  highlight: { background: '#2563eb', border: '#60a5fa' }
                },
                font: { color: '#f8fafc', face: 'Inter', size: 14, bold: true },
                margin: 12,
                borderWidth: 2,
              });
            } else {
              // Cluster is unfolded into member modules!
              (c.modules || []).forEach(mId => {
                const mod = (data.modules || []).find(m => m.id === mId);
                const role = mod ? mod.role : 'MODULE';
                let bColor = '#38bdf8';
                if (role === 'BRIDGE') bColor = '#fbbf24';
                else if (role === 'HUB') bColor = '#c084fc';
                else if (role === 'LEAF') bColor = '#4ade80';

                nodes.push({
                  id: `mod:${mId}`,
                  label: mId.split('/').pop(),
                  shape: 'box',
                  color: {
                    background: '#0f172a',
                    border: bColor,
                    highlight: { background: '#1e293b', border: '#fff' }
                  },
                  font: { color: '#e2e8f0', face: 'Fira Code', size: 11 },
                  margin: 8,
                  borderWidth: 1.5,
                });
              });
            }
          });

          // Component edges
          (data.component_edges || []).forEach(e => {
            const srcUnfolded = unfoldedComponents.has(e.source);
            const tgtUnfolded = unfoldedComponents.has(e.target);
            if (!srcUnfolded && !tgtUnfolded) {
              edges.push({
                from: `comp:${e.source}`,
                to: `comp:${e.target}`,
                arrows: 'to',
                color: { color: 'rgba(56, 189, 248, 0.4)', highlight: '#38bdf8' },
                width: Math.min(6, Math.max(1, Math.log2((e.weight || 1) + 1))),
              });
            }
          });

          // If any components are unfolded, add corresponding inter-module edges
          if (unfoldedComponents.size > 0) {
            (data.module_edges || []).forEach(e => {
              edges.push({
                from: `mod:${e.source}`,
                to: `mod:${e.target}`,
                arrows: 'to',
                color: { color: 'rgba(148, 163, 184, 0.3)', highlight: '#38bdf8' },
                width: 1,
              });
            });
          }

        } else if (level === 'modules') {
          // Show all module nodes
          (data.modules || []).forEach(m => {
            let bColor = '#38bdf8';
            if (m.role === 'BRIDGE') bColor = '#fbbf24';
            else if (m.role === 'HUB') bColor = '#c084fc';
            else if (m.role === 'LEAF') bColor = '#4ade80';
            else if (m.role === 'CYCLE_MEMBER') bColor = '#fb7185';
            else if (m.role === 'ENTRY_CANDIDATE') bColor = '#22d3ee';

            nodes.push({
              id: `mod:${m.id}`,
              label: m.path.split('/').pop(),
              shape: 'box',
              color: {
                background: '#0f172a',
                border: bColor,
                highlight: { background: '#1e293b', border: '#fff' }
              },
              font: { color: '#f8fafc', face: 'Fira Code', size: 12 },
              margin: 8,
              borderWidth: 1.5,
            });
          });

          (data.module_edges || []).forEach(e => {
            const types = e.relationship_types || {};
            const isCall = Boolean(types.CALL);
            const isImport = Boolean(types.IMPORT);
            const isRef = Boolean(types.REFERENCE);

            if ((isCall && filterCalls) || (isImport && filterImports) || (isRef && filterRefs) || (!isCall && !isImport && !isRef)) {
              edges.push({
                from: `mod:${e.source}`,
                to: `mod:${e.target}`,
                arrows: 'to',
                color: { color: 'rgba(56, 189, 248, 0.35)', highlight: '#38bdf8' },
                width: Math.min(5, Math.max(1, e.weight || 1)),
              });
            }
          });

        } else if (level === 'symbols') {
          // Show deep symbol cross references
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
                color: { background: '#1e293b', border: '#38bdf8' },
                font: { color: '#e2e8f0', size: 10 },
              });
            }
            if (!symbolNodesSet.has(tgtNodeId)) {
              symbolNodesSet.add(tgtNodeId);
              nodes.push({
                id: tgtNodeId,
                label: `${xr.target_file.split('/').pop()}\\n⚡ ${xr.symbol}`,
                shape: 'box',
                color: { background: '#0f172a', border: '#4ade80' },
                font: { color: '#4ade80', face: 'Fira Code', size: 10 },
              });
            }

            symbolEdges.push({
              from: srcNodeId,
              to: tgtNodeId,
              arrows: 'to',
              color: { color: 'rgba(74, 222, 128, 0.4)' },
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

          // Canvas click / selection listener
          network.on('click', function(params) {
            if (params.nodes.length > 0) {
              const nodeId = params.nodes[0];
              onCanvasNodeSelected(nodeId);
            }
          });

          // Canvas double-click listener: unfolds component!
          network.on('doubleClick', function(params) {
            if (params.nodes.length > 0) {
              const nodeId = params.nodes[0];
              if (nodeId.startsWith('comp:')) {
                const compId = nodeId.replace('comp:', '');
                if (unfoldedComponents.has(compId)) {
                  unfoldedComponents.delete(compId);
                } else {
                  unfoldedComponents.add(compId);
                }
                updateNetworkData();
              }
            }
          });
        } else {
          network.fit({ animation: { duration: 400 } });
        }
      }

      function updateNetworkData() {
        if (network) {
          const graphData = buildGraphDataSet(currentLevel);
          network.setData(graphData);
        }
      }

      function onCanvasNodeSelected(nodeId) {
        const inspTitle = document.getElementById('insp-title');
        const inspSub = document.getElementById('insp-sub');
        const inspBody = document.getElementById('insp-body');

        if (nodeId.startsWith('comp:')) {
          const cId = nodeId.replace('comp:', '');
          const comp = (data.components || []).find(c => c.id === cId);
          if (!comp) return;

          inspTitle.textContent = `📦 ${comp.name}`;
          inspSub.textContent = `Architectural Component • ${comp.modules.length} member modules`;
          const isUnfolded = unfoldedComponents.has(cId);

          inspBody.innerHTML = `
            <div class="inspector-prop"><span class="lbl">Confidence</span><span class="val">${Math.round(comp.confidence * 100)}%</span></div>
            <div class="inspector-prop"><span class="lbl">Discovery</span><span class="val">${(comp.discovery_methods || []).join(', ')}</span></div>
            <div class="inspector-prop"><span class="lbl">Internal Weight</span><span class="val">${comp.metadata.internal_weight || 0}</span></div>
            <div style="margin-top: 16px;">
              <button class="btn-primary" style="width: 100%; justify-content: center; margin-bottom: 8px;" onclick="window.toggleUnfold('${cId}')">
                ${isUnfolded ? 'Fold Component' : 'Unfold into Modules ➔'}
              </button>
            </div>
            <div style="margin-top: 14px; font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Member Modules:</div>
            <div style="font-family: 'Fira Code', monospace; font-size: 11px; line-height: 1.8; color: var(--text-secondary); margin-top: 6px;">
              ${comp.modules.map(m => `<div>• ${m}</div>`).join('')}
            </div>
          `;
        } else if (nodeId.startsWith('mod:')) {
          const mId = nodeId.replace('mod:', '');
          const mod = (data.modules || []).find(m => m.id === mId);
          if (!mod) return;

          inspTitle.textContent = `📄 ${mod.name}`;
          inspSub.textContent = mod.path;
          inspBody.innerHTML = `
            <div class="inspector-prop"><span class="lbl">Component</span><span class="val">${mod.component_name}</span></div>
            <div class="inspector-prop"><span class="lbl">Role</span><span class="val">${mod.role}</span></div>
            <div class="inspector-prop"><span class="lbl">LOC</span><span class="val">${mod.line_count}</span></div>
            <div class="inspector-prop"><span class="lbl">In / Out Degree</span><span class="val">${mod.in_degree} / ${mod.out_degree}</span></div>
            <div class="inspector-prop"><span class="lbl">Betweenness</span><span class="val">${mod.betweenness}</span></div>
            <div style="margin-top: 16px;">
              <button class="btn-primary" style="width: 100%; justify-content: center;" onclick="window.selectModule('${mId}')">Inspect Code & Symbols ➔</button>
            </div>
          `;
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
        document.querySelectorAll('#graph-level-pills .pill-opt').forEach(p => p.classList.toggle('active', p.dataset.level === 'modules'));
        updateNetworkData();
        setTimeout(() => {
          if (network) {
            network.focus(`mod:${modId}`, { scale: 1.2, animation: { duration: 500 } });
            network.selectNodes([`mod:${modId}`]);
            onCanvasNodeSelected(`mod:${modId}`);
          }
        }, 200);
      };

      document.getElementById('btn-fold-all').addEventListener('click', () => {
        unfoldedComponents.clear();
        updateNetworkData();
      });

      // Level switch pills
      document.querySelectorAll('#graph-level-pills .pill-opt').forEach(pill => {
        pill.addEventListener('click', function() {
          document.querySelectorAll('#graph-level-pills .pill-opt').forEach(p => p.classList.remove('active'));
          this.classList.add('active');
          currentLevel = this.dataset.level;
          updateNetworkData();
        });
      });

      // Edge filter checkboxes
      ['chk-filter-calls', 'chk-filter-imports', 'chk-filter-refs'].forEach(id => {
        document.getElementById(id).addEventListener('change', updateNetworkData);
      });

      // -------------------------------------------------------------
      // 6. Global Search Modal (Cmd+K)
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
        // Match components
        (data.components || []).forEach(c => {
          if (!query || c.name.toLowerCase().includes(query)) {
            results.push({ type: 'Component', label: `📦 ${c.name}`, sub: `${c.modules.length} modules`, action: () => { closeSearch(); window.inspectComponent(c.id); } });
          }
        });
        // Match modules
        (data.modules || []).forEach(m => {
          if (!query || m.path.toLowerCase().includes(query) || m.role.toLowerCase().includes(query)) {
            results.push({ type: 'Module', label: `📄 ${m.name}`, sub: `${m.path} (${m.role})`, action: () => { closeSearch(); window.selectModule(m.id); } });
          }
        });
        // Match symbols
        (data.modules || []).forEach(m => {
          (m.functions || []).forEach(f => {
            if (query && f.name.toLowerCase().includes(query)) {
              results.push({ type: 'Function', label: `⚡ ${f.name}()`, sub: `in ${m.path}`, action: () => { closeSearch(); window.selectModule(m.id); } });
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
            <span style="font-size: 10px; text-transform: uppercase; color: var(--accent-blue); background: rgba(56,189,248,0.1); padding: 2px 6px; border-radius: 4px;">${r.type}</span>
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
