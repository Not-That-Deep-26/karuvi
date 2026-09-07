"""
Karuvi Living Codebase Atlas — Unified Web Visualizer
========================================================================

Generates a standalone, interactive, dark-mode Single Page Web Application
embodying Karuvi's 6 core modes:
1. ◉ Overview: Executive codebase dashboard, vital metrics, and circular loop radar.
3. 🏛️ Architecture: Discovered components, confidence scores, and architectural flows.
4. 🕸️ Graph Explorer: Progressive graph disclosure, relation filters, and unrelated node greying.
5. 📁 Code Explorer: Sourcetrail-grade side-by-side file tree and syntax-highlighted code viewer.
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
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {
      --bg-canvas: #090d16;
      --bg-surface: #0f172a;
      --bg-card: #152037;
      --bg-card-hover: #1c2b4a;
      --border: #1e293b;
      --border-subtle: #162238;
      --border-glow: rgba(56, 189, 248, 0.4);
      
      --text: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      
      --accent-blue: #38bdf8;
      --accent-cyan: #22d3ee;
      --accent-purple: #c084fc;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      
      --role-entry: #38bdf8;
      --role-bridge: #f59e0b;
      --role-hub: #c084fc;
      --role-leaf: #10b981;
      --role-cycle: #f43f5e;
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
      font-weight: 800;
      font-size: 17px;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #38bdf8 0%, #a855f7 100%);
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
      font-weight: 800;
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
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%);
      border: 1px solid rgba(56, 189, 248, 0.25);
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
      background: #7dd3fc;
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
      background: rgba(244, 63, 94, 0.08);
      border: 1px solid rgba(244, 63, 94, 0.3);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 24px;
      font-size: 13px;
      line-height: 1.6;
    }
    .alert-card.warning {
      background: rgba(245, 158, 11, 0.08);
      border-color: rgba(245, 158, 11, 0.3);
      color: #fde68a;
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
    .confidence-high { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); }
    .confidence-med { background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }
    .confidence-low { background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3); }

    .comp-modules-list {
      font-size: 11px;
      color: var(--text-muted);
      font-family: 'Fira Code', monospace;
      line-height: 1.6;
    }

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
    }

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
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.15);
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
    .syntax-kw { color: #f43f5e; font-weight: 600; }
    .syntax-fn { color: #38bdf8; font-weight: 600; }
    .syntax-cls { color: #c084fc; font-weight: 600; }
    .syntax-str { color: #10b981; }
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

    .docs-container h1 { font-size: 26px; font-weight: 800; margin-bottom: 16px; color: #fff; }
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
  </style>
</head>
<body>
  <!-- Header App Bar -->
  <header>
    <div class="brand-group">
      <div class="brand-logo">
        <span>⚡ KARUVI</span>
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
          <p>Deterministic architecture reconstruction, topological graph analysis, and progressive onboarding.</p>
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
            <button class="btn-secondary" id="btn-jump-code">View Code</button>
          </div>
        </div>

        <!-- Radar Alert for Cycles -->
        <div id="overview-cycle-radar" style="display: none;"></div>

        <!-- Key Architectural Insights -->
        <div class="section-title">🌉 Structural Bridges & Central Modules</div>
        <div id="bridges-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 30px;"></div>
      </div>

      <!-- VIEW 3: ARCHITECTURE -->
      <div class="tab-view" id="tab-architecture">
        <div class="section-title">🏛️ Discovered Architectural Components</div>
        <div class="comp-grid" id="arch-components-grid"></div>

        <div class="section-title">🌊 High-Level Architectural Flows</div>
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
                  <span class="pill-opt" data-role="ENTRY_CANDIDATE">Entry</span>
                  <span class="pill-opt" data-role="CYCLE">Cycle</span>
                  <span class="pill-opt" data-role="HUB">Hub</span>
                  <span class="pill-opt" data-role="BRIDGE">Bridge</span>
                  <span class="pill-opt" data-role="LEAF">Leaf</span>
                </div>
              </div>
              <div class="filter-checkboxes">
                <label><input type="checkbox" id="chk-filter-calls" checked> Calls</label>
                <label><input type="checkbox" id="chk-filter-imports" checked> Imports</label>
                <label><input type="checkbox" id="chk-filter-refs" checked> References</label>
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
  </script>

  <!-- Interactive Application Logic -->
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
              <span>⚠️ Circular Dependency Radar</span>
              <span class="pill-tag" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">${cycles.length} loop(s) detected</span>
            </div>
            <div>Multi-module cyclic loops can cause tight coupling and initialization surprises. These are grouped into unified conceptual steps in the Onboarding course.</div>
            <div style="margin-top: 8px; font-family: 'Fira Code', monospace; font-size: 11px;">
              ${cycles.map((c, i) => `<div>Loop #${i+1}: ${c.join(' ➔ ')}</div>`).join('')}
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
              <span class="role-badge" style="background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3);">
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
      // 3. Architecture Tab
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
      // 4. Code Explorer Tab (Sourcetrail Side-by-Side)
      // -------------------------------------------------------------
      const fileTreePane = document.getElementById('code-file-tree');
      fileTreePane.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; padding: 20px; text-align: center;">Select a module to view its dependency tree.</div>';

      function renderDependencyTree(mod) {
        if (!mod) return;
        
        let html = `<div style="font-size: 13px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border); word-break: break-all;">🌳 Dependency Tree<br><span style="font-size: 11px; color: var(--text-muted); font-family: 'Fira Code', monospace; font-weight: normal;">${mod.id}</span></div>`;
        
        // Upstream dependencies (Outgoing modules)
        html += `
          <div style="margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-amber); text-transform: uppercase; padding: 4px 6px; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬆️ UPSTREAM DEPENDENCIES (${(mod.outgoing_modules || []).length})
            </div>
            <div style="padding-left: 10px;">
        `;
        if (mod.outgoing_modules && mod.outgoing_modules.length > 0) {
            mod.outgoing_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              html += `
                <div class="file-tree-item" onclick="window.selectModule('${depId}')">
                  <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${depName}</span>
                </div>
              `;
            });
        } else {
            html += `<div style="padding: 4px 10px; font-size: 11px; color: var(--text-muted);">None (No imports)</div>`;
        }
        html += `</div></div>`;
        
        // Downstream dependents (Incoming modules)
        html += `
          <div style="margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-green); text-transform: uppercase; padding: 4px 6px; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬇️ DOWNSTREAM DEPENDENTS (${(mod.incoming_modules || []).length})
            </div>
            <div style="padding-left: 10px;">
        `;
        if (mod.incoming_modules && mod.incoming_modules.length > 0) {
            mod.incoming_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              html += `
                <div class="file-tree-item" onclick="window.selectModule('${depId}')">
                  <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${depName}</span>
                </div>
              `;
            });
        } else {
            html += `<div style="padding: 4px 10px; font-size: 11px; color: var(--text-muted);">None (No dependents)</div>`;
        }
        html += `</div></div>`;
        
        fileTreePane.innerHTML = html;
      }

      function highlightPythonSyntax(rawText) {
        if (!rawText) return '<em>(Source code empty or file not on disk)</em>';
        const lines = rawText.split('\\n');
        return lines.map((line, idx) => {
          let escaped = line
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

          // Basic fast syntax highlight
          escaped = escaped.replace(/(#.*$)/g, '<span class="syntax-cmt">$1</span>');
          escaped = escaped.replace(/\\b(def)\\s+([a-zA-Z0-9_]+)/g, '<span class="syntax-kw">$1</span> <span class="syntax-fn">$2</span>');
          escaped = escaped.replace(/\\b(class)\\s+([a-zA-Z0-9_]+)/g, '<span class="syntax-kw">$1</span> <span class="syntax-cls">$2</span>');
          escaped = escaped.replace(/\\b(from|import|return|if|else|elif|for|while|try|except|finally|with|as|in|is|not|and|or|None|True|False)\\b/g, '<span class="syntax-kw">$1</span>');
          escaped = escaped.replace(/(".*?"|'.*?')/g, '<span class="syntax-str">$1</span>');

          return `
            <tr>
              <td class="code-line-text">${escaped}</td>
            </tr>
          `;
        }).join('');
      }

      window.selectModule = function(modId) {
        switchTab('code');
        const mod = (data.modules || []).find(m => m.id === modId);
        if (!mod) return;

        // Render dependency tree
        renderDependencyTree(mod);

        document.getElementById('code-file-path').textContent = `${mod.path} (${mod.line_count} LOC • ${mod.role})`;
        document.getElementById('code-header-actions').innerHTML = `
          <button class="btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="window.jumpToGraphNode('${mod.id}')">View in Graph ➔</button>
        `;

        const codeContentEl = document.getElementById('code-viewer-content');
        if (mod.source_code) {
          codeContentEl.innerHTML = `<table class="code-table">${highlightPythonSyntax(mod.source_code)}</table>`;
        } else {
          // Fallback summary if source code not cached
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
                ${(mod.functions || []).map(f => `<div>⚡ <span style="color: var(--accent-green);">def</span> <strong>${f.name}</strong>${f.signature || '()'}</div>`).join('') || '<div style="color: var(--text-muted);">None</div>'}
              </div>
            </div>
          `;
        }
      };

      // -------------------------------------------------------------
      // 5. Graph Explorer with Unrelated Node Greying
      // -------------------------------------------------------------
      let network = null;
      let currentLevel = 'modules';
      let unfoldedComponents = new Set();
      let selectedNodeId = null;

      const container = document.getElementById('network-canvas');

      function buildGraphDataSet(level) {
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
                  background: '#152037',
                  border: '#38bdf8',
                  highlight: { background: '#1d4ed8', border: '#60a5fa' }
                },
                font: { color: '#f8fafc', face: 'Inter', size: 14, bold: true },
                margin: 12,
                borderWidth: 2,
              });
            } else {
              (c.modules || []).forEach(mId => {
                const mod = (data.modules || []).find(m => m.id === mId);
                const role = mod ? mod.role : 'MODULE';
                let bColor = '#38bdf8';
                if (role === 'BRIDGE') bColor = '#f59e0b';
                else if (role === 'HUB') bColor = '#c084fc';
                else if (role === 'LEAF') bColor = '#10b981';

                nodes.push({
                  id: `mod:${mId}`,
                  label: mId.split('/').pop(),
                  shape: 'box',
                  color: {
                    background: '#090d16',
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
          (data.modules || []).forEach(m => {
            let bColor = '#38bdf8';
            if (m.role === 'BRIDGE') bColor = '#f59e0b';
            else if (m.role === 'HUB') bColor = '#c084fc';
            else if (m.role === 'LEAF') bColor = '#10b981';
            else if (m.role === 'CYCLE_MEMBER') bColor = '#f43f5e';
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
                color: { background: '#152037', border: '#38bdf8' },
                font: { color: '#e2e8f0', size: 10 },
              });
            }
            if (!symbolNodesSet.has(tgtNodeId)) {
              symbolNodesSet.add(tgtNodeId);
              nodes.push({
                id: tgtNodeId,
                label: `${xr.target_file.split('/').pop()}\\n⚡ ${xr.symbol}`,
                shape: 'box',
                color: { background: '#090d16', border: '#10b981' },
                font: { color: '#10b981', face: 'Fira Code', size: 10 },
              });
            }

            symbolEdges.push({
              from: srcNodeId,
              to: tgtNodeId,
              arrows: 'to',
              color: { color: 'rgba(16, 185, 129, 0.4)' },
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
      const cyclesSet = new Set();
      (data.cycles || []).forEach(cycle => cycle.forEach(m => cyclesSet.add(m)));

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

        const allNodes = network.body.data.nodes.get();
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
              if (!cyclesSet.has(mId)) matchesRole = false;
            } else if (mod && mod.role !== currentRoleFilter) {
              matchesRole = false;
            }
          }

          if (matchesQuery && matchesRole) {
            return { id: n.id, opacity: 1.0 };
          } else {
            return { id: n.id, opacity: 0.12 };
          }
        });
        network.body.data.nodes.update(updates);
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
      }

      function resetNodeOpacities() {
        if (!network) return;
        const allNodes = network.body.data.nodes.get();
        const updates = allNodes.map(n => ({ id: n.id, opacity: 1.0 }));
        network.body.data.nodes.update(updates);
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
            results.push({ type: 'Component', label: `📦 ${c.name}`, sub: `${c.modules.length} modules`, action: () => { closeSearch(); window.inspectComponent(c.id); } });
          }
        });
        (data.modules || []).forEach(m => {
          if (!query || m.path.toLowerCase().includes(query) || m.role.toLowerCase().includes(query)) {
            results.push({ type: 'Module', label: `📄 ${m.name}`, sub: `${m.path} (${m.role})`, action: () => { closeSearch(); window.selectModule(m.id); } });
          }
        });
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