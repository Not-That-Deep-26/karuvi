"""
Karuvi Repository Graph Builder
===============================

Analyzes a full repository of parsed modules to construct:
1. Inter-module import dependency graph (internal & external).
2. Cross-module symbol reference tracking (which file uses which declaration).
3. Graph metrics (in-degree, out-degree, root entrypoints, leaf utilities).
4. Export formats: Plain Dict (JSON), Mermaid diagrams, and standalone Interactive HTML.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pointers import GlobalIndex
from returns import Module, module_to_dict
from deps import iter_references


@dataclass
class Edge:
    source: str
    target: str
    type: str  # "import" | "symbol_reference"
    symbol: str | None = None
    use_line: int | None = None
    decl_line: int | None = None
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Node:
    id: str
    name: str
    path: str
    is_internal: bool
    line_count: int = 0
    function_count: int = 0
    class_count: int = 0
    variable_count: int = 0
    functions: list[str] | None = None
    classes: list[str] | None = None
    in_degree: int = 0
    out_degree: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RepoGraphBuilder:
    """Builds and manages repository-level dependency graphs."""

    def __init__(
        self,
        project_root: Path | str,
        parsed_modules: dict[str, Module],
        global_index: GlobalIndex | None = None,
    ):
        self.project_root = Path(project_root).resolve()
        self.parsed = parsed_modules  # key: relative path (posix)
        self.global_index = global_index
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.external_packages: set[str] = set()
        self.cross_references: list[dict[str, Any]] = []
        self.cycles: list[list[str]] = []

    def build(self) -> RepoGraphBuilder:
        self.nodes.clear()
        self.edges.clear()
        self.external_packages.clear()
        self.cross_references.clear()
        self.cycles.clear()

        # Map module stem and relative path to module key
        mod_name_to_key: dict[str, str] = {}
        abs_path_to_key: dict[str, str] = {}

        for rel_key, mod in self.parsed.items():
            abs_p = str((self.project_root / rel_key).resolve())
            abs_path_to_key[abs_p] = rel_key
            if mod.file_path:
                abs_path_to_key[str(Path(mod.file_path).resolve())] = rel_key

            stem = Path(rel_key).stem
            mod_name_to_key[stem] = rel_key
            if mod.name:
                mod_name_to_key[mod.name] = rel_key

        # 1. Create nodes for all internal modules
        for rel_key, mod in self.parsed.items():
            full_path = (self.project_root / rel_key).resolve()
            line_count = 0
            if full_path.exists() and full_path.is_file():
                try:
                    line_count = len(full_path.read_text(errors="ignore").splitlines())
                except Exception:
                    pass

            func_names = [f.name for f in mod.functions]
            class_names = [c.name for c in mod.classes]
            var_count = len(mod.variables)

            self.nodes[rel_key] = Node(
                id=rel_key,
                name=Path(rel_key).stem,
                path=rel_key,
                is_internal=True,
                line_count=line_count,
                function_count=len(func_names),
                class_count=len(class_names),
                variable_count=var_count,
                functions=func_names,
                classes=class_names,
            )

        # 2. Extract import edges
        for rel_key, mod in self.parsed.items():
            if not mod.scope:
                continue

            # 2a. Direct module imports (import foo)
            if hasattr(mod.scope, "imports"):
                for imp_alias, imp_mod in mod.scope.imports.items():
                    target_key = self._resolve_target_module(
                        imp_mod, rel_key, mod_name_to_key
                    )
                    if target_key:
                        if target_key != rel_key:
                            self.edges.append(
                                Edge(
                                    source=rel_key,
                                    target=target_key,
                                    type="import",
                                    details=f"imports {imp_mod}",
                                )
                            )
                    else:
                        ext_pkg = imp_mod.split(".")[0]
                        if ext_pkg and ext_pkg not in mod_name_to_key:
                            self.external_packages.add(ext_pkg)
                            ext_id = f"ext:{ext_pkg}"
                            if ext_id not in self.nodes:
                                self.nodes[ext_id] = Node(
                                    id=ext_id,
                                    name=ext_pkg,
                                    path=f"external:{ext_pkg}",
                                    is_internal=False,
                                )
                            self.edges.append(
                                Edge(
                                    source=rel_key,
                                    target=ext_id,
                                    type="import",
                                    details=f"imports third-party package '{ext_pkg}'",
                                )
                            )

            # 2b. Symbol imports (from foo import bar)
            for sym_name, sym_var in mod.scope.symbols.items():
                if sym_var.uuid and str(sym_var.uuid).startswith("import:"):
                    imported_raw = str(sym_var.uuid).split(":", 1)[1]
                    target_key = self._resolve_target_module(
                        imported_raw, rel_key, mod_name_to_key
                    )

                    if target_key:
                        if target_key != rel_key:
                            self.edges.append(
                                Edge(
                                    source=rel_key,
                                    target=target_key,
                                    type="import",
                                    details=f"imports {imported_raw}",
                                )
                            )
                    else:
                        ext_pkg = imported_raw.split(".")[0]
                        if ext_pkg and ext_pkg not in mod_name_to_key:
                            self.external_packages.add(ext_pkg)
                            ext_id = f"ext:{ext_pkg}"
                            if ext_id not in self.nodes:
                                self.nodes[ext_id] = Node(
                                    id=ext_id,
                                    name=ext_pkg,
                                    path=f"external:{ext_pkg}",
                                    is_internal=False,
                                )
                            self.edges.append(
                                Edge(
                                    source=rel_key,
                                    target=ext_id,
                                    type="import",
                                    details=f"imports third-party package '{ext_pkg}'",
                                )
                            )

        # 3. Extract cross-module symbol references
        for rel_key, mod in self.parsed.items():
            for scope_name, var in iter_references(mod.code_flow):
                if not var.is_reference or not var.decl_reference:
                    continue

                decl_file_abs = var.decl_reference[0]
                use_file_abs = var.reference[0] if var.reference else None

                if decl_file_abs:
                    decl_rel = abs_path_to_key.get(decl_file_abs)
                    use_rel = abs_path_to_key.get(use_file_abs, rel_key)

                    if decl_rel and use_rel and decl_rel != use_rel:
                        xref = {
                            "source_file": use_rel,
                            "target_file": decl_rel,
                            "symbol": var.name,
                            "uuid": var.uuid,
                            "use_line": var.reference[1] if var.reference else None,
                            "use_col": var.reference[2] if var.reference else None,
                            "decl_line": var.decl_reference[1],
                            "decl_col": var.decl_reference[2],
                            "scope": scope_name,
                        }
                        self.cross_references.append(xref)
                        self.edges.append(
                            Edge(
                                source=use_rel,
                                target=decl_rel,
                                type="symbol_reference",
                                symbol=var.name,
                                use_line=var.reference[1] if var.reference else None,
                                decl_line=var.decl_reference[1],
                                details=f"uses '{var.name}' declared at L{var.decl_reference[1]}",
                            )
                        )

        # 4. Compute metrics (degrees)
        for edge in self.edges:
            if edge.source in self.nodes:
                self.nodes[edge.source].out_degree += 1
            if edge.target in self.nodes:
                self.nodes[edge.target].in_degree += 1

        # 5. Detect circular dependencies
        self.cycles = self.detect_cycles()

        return self

    def detect_cycles(self) -> list[list[str]]:
        """Find circular dependency chains among internal modules."""
        adj: dict[str, list[str]] = {
            k: [] for k, n in self.nodes.items() if n.is_internal
        }
        for e in self.edges:
            if e.type == "import" and e.source in adj and e.target in adj and e.source != e.target:
                if e.target not in adj[e.source]:
                    adj[e.source].append(e.target)

        cycles: list[list[str]] = []
        seen_cycles: set[tuple[str, ...]] = set()

        def dfs(node: str, path: list[str]):
            if node in path:
                idx = path.index(node)
                cycle = path[idx:]
                if len(cycle) > 1:
                    min_idx = cycle.index(min(cycle))
                    canonical = tuple(cycle[min_idx:] + cycle[:min_idx])
                    if canonical not in seen_cycles:
                        seen_cycles.add(canonical)
                        cycles.append(list(canonical) + [canonical[0]])
                return

            if len(path) >= 12:
                return

            for neighbor in adj.get(node, []):
                dfs(neighbor, path + [node])

        for node in sorted(adj.keys()):
            dfs(node, [])

        return sorted(cycles, key=len)

    def get_dependencies(self, file_key: str) -> dict[str, Any]:
        """Return direct imports and external dependencies of file_key."""
        imports = []
        externals = []
        for e in self.edges:
            if e.source == file_key and e.type == "import":
                if e.target.startswith("ext:"):
                    externals.append(e.target.replace("ext:", ""))
                else:
                    imports.append(e.target)
        return {
            "internal": sorted(set(imports)),
            "external": sorted(set(externals)),
        }

    def get_dependents(self, file_key: str) -> list[str]:
        """Return files that directly import or reference file_key."""
        dependents = []
        for e in self.edges:
            if e.target == file_key:
                dependents.append(e.source)
        return sorted(set(dependents))

    def _resolve_target_module(
        self, imported_mod: str, current_rel_key: str, mod_name_to_key: dict[str, str]
    ) -> str | None:
        """Attempt to resolve imported_mod string to an internal relative file key."""
        if imported_mod in mod_name_to_key:
            return mod_name_to_key[imported_mod]

        as_path = imported_mod.replace(".", "/")
        candidates = [
            f"{as_path}.py",
            f"{as_path}/__init__.py",
        ]
        for c in candidates:
            if c in self.parsed:
                return c

        curr_dir = Path(current_rel_key).parent
        for c in candidates:
            rel_candidate = str((curr_dir / c).as_posix())
            if rel_candidate in self.parsed:
                return rel_candidate

        first_part = imported_mod.split(".")[0]
        if first_part in mod_name_to_key:
            return mod_name_to_key[first_part]

        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert repository graph and metrics into a JSON-serializable dictionary."""
        from returns import deptree_to_dict, scope_to_dict

        internal_nodes = []
        for n in self.nodes.values():
            if n.is_internal:
                n_dict = n.to_dict()
                if n.id in self.parsed:
                    mod = self.parsed[n.id]
                    n_dict["code_flow"] = deptree_to_dict(mod.code_flow)
                    if mod.scope:
                        n_dict["scope"] = scope_to_dict(mod.scope)
                internal_nodes.append(n_dict)

        external_nodes = [n.to_dict() for n in self.nodes.values() if not n.is_internal]

        sorted_by_dep = sorted(
            [n for n in self.nodes.values() if n.is_internal],
            key=lambda n: n.in_degree,
            reverse=True,
        )

        return {
            "project_root": str(self.project_root),
            "stats": {
                "total_internal_modules": len(internal_nodes),
                "total_external_packages": len(external_nodes),
                "total_edges": len(self.edges),
                "total_cross_references": len(self.cross_references),
                "total_cycles": len(self.cycles),
            },
            "cycles": self.cycles,
            "nodes": {
                "internal": internal_nodes,
                "external": external_nodes,
            },
            "edges": [e.to_dict() for e in self.edges],
            "cross_references": self.cross_references,
            "top_depended_modules": [
                {"id": n.id, "name": n.name, "in_degree": n.in_degree, "out_degree": n.out_degree}
                for n in sorted_by_dep[:5]
            ],
        }

    def to_mermaid(self) -> str:
        """Generate a Mermaid diagram for Markdown viewing."""
        lines = ["graph TD"]

        def clean_id(raw: str) -> str:
            return "n_" + "".join(c if c.isalnum() else "_" for c in raw)

        lines.append("    classDef internal fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;")
        lines.append("    classDef external fill:#0f172a,stroke:#64748b,stroke-width:1px,stroke-dasharray: 5 5,color:#94a3b8;")

        for node in self.nodes.values():
            nid = clean_id(node.id)
            if node.is_internal:
                label = f"{node.name}<br/><small>{node.line_count} lines | {node.function_count} fn</small>"
                lines.append(f'    {nid}["{label}"]:::internal')
            else:
                lines.append(f'    {nid}["{node.name} (ext)"]:::external')

        seen_edges = set()
        for edge in self.edges:
            pair = (edge.source, edge.target, edge.type)
            if pair in seen_edges:
                continue
            seen_edges.add(pair)
            s_id = clean_id(edge.source)
            t_id = clean_id(edge.target)
            if edge.type == "symbol_reference":
                lines.append(f'    {s_id} -.->|"{edge.symbol or "symbol"}"| {t_id}')
            else:
                lines.append(f"    {s_id} --> {t_id}")

        return "\n".join(lines)

    def render_html(self, arch_model: Any = None) -> str:
        """Generate the Karuvi Living Codebase Atlas interactive HTML visualization."""
        try:
            from architecture.visualizer import generate_atlas_html
            return generate_atlas_html(self, arch_model)
        except Exception:
            # Fallback to standard graph visualizer if architecture generation encounters an issue
            graph_data = self.to_dict()
            graph_json = json.dumps(graph_data)
            return SOURCETRAIL_HTML_TEMPLATE.replace("__GRAPH_JSON__", graph_json)


SOURCETRAIL_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Karuvi — Sourcetrail-Grade Architecture & Dependency Visualizer</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-canvas: #0d1117;
      --bg-panel: #161b22;
      --bg-panel-header: #13171f;
      --bg-item-hover: #21262d;
      --bg-item-active: #28303d;
      --border: #30363d;
      --border-subtle: #21262d;
      --text: #f0f6fc;
      --text-secondary: #8b949e;
      --text-muted: #6e7681;
      --accent: #58a6ff;
      --accent-glow: rgba(88, 166, 255, 0.25);
      --color-class: #bc8cff;
      --color-function: #3fb950;
      --color-var: #79c0ff;
      --color-cycle: #f85149;
      --color-inbound: #34d399;
      --color-outbound: #38bdf8;
      --color-external: #8b949e;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      scrollbar-width: thin;
      scrollbar-color: var(--border) var(--bg-panel);
    }
    *::-webkit-scrollbar { width: 6px; height: 6px; }
    *::-webkit-scrollbar-track { background: var(--bg-panel); }
    *::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

    body {
      background: var(--bg-canvas);
      color: var(--text);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* TOP WORKSPACE TOOLBAR */
    #top-bar {
      height: 48px;
      background: var(--bg-panel-header);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      z-index: 50;
      user-select: none;
    }
    .brand-section {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand-logo {
      font-family: 'Fira Code', monospace;
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: 1px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .brand-tag {
      font-size: 0.7rem;
      background: rgba(88, 166, 255, 0.15);
      color: var(--accent);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(88, 166, 255, 0.3);
      font-family: 'Fira Code', monospace;
    }
    .top-stats {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 0.78rem;
      color: var(--text-secondary);
    }
    .stat-badge {
      display: flex;
      align-items: center;
      gap: 5px;
      background: var(--bg-panel);
      border: 1px solid var(--border);
      padding: 3px 8px;
      border-radius: 4px;
    }
    .stat-badge b { color: var(--text); }
    .cycle-badge {
      background: rgba(248, 81, 73, 0.15);
      border-color: rgba(248, 81, 73, 0.4);
      color: #ff7b72;
      cursor: pointer;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.6; }
    }

    .top-controls {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .tool-btn {
      background: var(--bg-panel);
      color: var(--text-secondary);
      border: 1px solid var(--border);
      padding: 5px 10px;
      border-radius: 4px;
      font-size: 0.78rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s ease;
    }
    .tool-btn:hover {
      background: var(--bg-item-hover);
      color: var(--text);
      border-color: var(--accent);
    }
    .tool-btn.active {
      background: rgba(88, 166, 255, 0.2);
      color: var(--accent);
      border-color: var(--accent);
    }

    /* 3-PANE WORKSPACE */
    #workspace {
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }

    /* LEFT EXPLORER PANEL */
    #left-panel {
      width: 320px;
      min-width: 250px;
      max-width: 450px;
      background: var(--bg-panel);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 20;
    }
    .panel-header {
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--bg-panel-header);
    }
    .panel-title {
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .search-box-wrap {
      padding: 8px 12px;
      border-bottom: 1px solid var(--border);
      background: var(--bg-panel);
    }
    .search-input {
      width: 100%;
      background: var(--bg-canvas);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 10px;
      border-radius: 4px;
      font-size: 0.8rem;
      font-family: 'Inter', sans-serif;
      outline: none;
      transition: border-color 0.2s;
    }
    .search-input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }

    .explorer-tabs {
      display: flex;
      border-bottom: 1px solid var(--border);
      background: var(--bg-panel-header);
    }
    .tab-btn {
      flex: 1;
      padding: 8px 4px;
      font-size: 0.75rem;
      text-align: center;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-secondary);
      cursor: pointer;
      font-weight: 500;
      transition: all 0.15s;
    }
    .tab-btn:hover { color: var(--text); }
    .tab-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
      background: var(--bg-panel);
    }

    .explorer-content {
      flex: 1;
      overflow-y: auto;
      padding: 6px 0;
    }
    .tree-item {
      display: flex;
      align-items: center;
      padding: 5px 12px;
      cursor: pointer;
      font-size: 0.8rem;
      color: var(--text);
      gap: 6px;
      transition: background 0.1s;
      user-select: none;
    }
    .tree-item:hover {
      background: var(--bg-item-hover);
    }
    .tree-item.selected {
      background: var(--bg-item-active);
      color: var(--accent);
      font-weight: 600;
      border-left: 3px solid var(--accent);
    }
    .item-icon {
      font-size: 0.85rem;
      width: 16px;
      text-align: center;
    }
    .item-name {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-family: 'Fira Code', monospace;
      font-size: 0.78rem;
    }
    .item-badge {
      font-size: 0.68rem;
      color: var(--text-muted);
      background: rgba(255,255,255,0.05);
      padding: 1px 5px;
      border-radius: 3px;
    }

    /* CENTER GRAPH CANVAS */
    #center-canvas {
      flex: 1;
      position: relative;
      background: radial-gradient(circle at 50% 50%, #161e2b 0%, #0d1117 80%);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    #breadcrumbs-bar {
      position: absolute;
      top: 12px;
      left: 16px;
      z-index: 10;
      background: rgba(22, 27, 34, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.78rem;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      font-family: 'Fira Code', monospace;
    }
    #breadcrumbs-bar span.active {
      color: var(--accent);
      font-weight: 600;
    }

    #network-canvas {
      width: 100%;
      height: 100%;
    }

    .canvas-legend {
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: rgba(22, 27, 34, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      padding: 10px 14px;
      border-radius: 6px;
      font-size: 0.72rem;
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 10;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      user-select: none;
    }
    .legend-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 2px;
    }
    .legend-line {
      width: 16px;
      height: 2px;
    }

    /* RIGHT INSPECTOR PANEL (SOURCETRAIL STYLE) */
    #right-panel {
      width: 440px;
      min-width: 300px;
      max-width: 600px;
      background: var(--bg-panel);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 20;
    }
    .inspector-header {
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--bg-panel-header);
    }
    .inspector-title-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .inspector-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--accent);
      font-family: 'Fira Code', monospace;
      word-break: break-all;
    }
    .inspector-path {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 4px;
      word-break: break-all;
      font-family: 'Fira Code', monospace;
    }
    .meta-metrics {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      margin-top: 10px;
    }
    .meta-pill {
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 4px 8px;
      text-align: center;
    }
    .meta-pill .num {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text);
    }
    .meta-pill .lbl {
      font-size: 0.65rem;
      color: var(--text-muted);
      text-transform: uppercase;
    }

    .inspector-body {
      flex: 1;
      overflow-y: auto;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .section-title {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 700;
      color: var(--text-secondary);
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 4px;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    /* COLLAPSIBLE INTRA-FILE TREE */
    .ast-tree-view {
      font-family: 'Fira Code', monospace;
      font-size: 0.78rem;
      line-height: 1.5;
    }
    .ast-node {
      padding-left: 14px;
      border-left: 1px dashed rgba(255,255,255,0.08);
      margin: 2px 0;
    }
    .ast-label {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      padding: 2px 4px;
      border-radius: 3px;
    }
    .ast-label:hover {
      background: var(--bg-item-hover);
    }
    .badge-kind {
      font-size: 0.65rem;
      font-weight: 600;
      padding: 1px 5px;
      border-radius: 3px;
      text-transform: uppercase;
    }
    .badge-class { background: rgba(188, 140, 255, 0.2); color: var(--color-class); }
    .badge-def { background: rgba(63, 185, 80, 0.2); color: var(--color-function); }
    .badge-var { background: rgba(121, 192, 255, 0.2); color: var(--color-var); }
    .badge-ref { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
    .badge-stmt { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }

    /* SYMBOL ROW & BLAST RADIUS */
    .symbol-card {
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 8px 10px;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .symbol-name-wrap {
      overflow: hidden;
    }
    .symbol-name {
      font-family: 'Fira Code', monospace;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text);
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .symbol-desc {
      font-size: 0.7rem;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .blast-btn {
      background: rgba(248, 81, 73, 0.15);
      border: 1px solid rgba(248, 81, 73, 0.4);
      color: #ff7b72;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.7rem;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }
    .blast-btn:hover {
      background: rgba(248, 81, 73, 0.35);
      color: #fff;
    }

    .dep-link {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 4px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.78rem;
      font-family: 'Fira Code', monospace;
      color: var(--text-secondary);
      transition: all 0.15s;
    }
    .dep-link:hover {
      background: var(--bg-item-hover);
      color: var(--accent);
    }

    /* MODAL BLAST RADIUS / REPORT */
    #blast-banner {
      display: none;
      background: rgba(248, 81, 73, 0.2);
      border-bottom: 1px solid rgba(248, 81, 73, 0.5);
      color: #ff7b72;
      padding: 8px 16px;
      font-size: 0.8rem;
      align-items: center;
      justify-content: space-between;
      z-index: 60;
    }
    #blast-banner b { color: #fff; }
    #blast-banner button {
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.2);
      color: #fff;
      padding: 2px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 0.75rem;
    }
  </style>
</head>
<body>

  <!-- TOP TOOLBAR -->
  <div id="top-bar">
    <div class="brand-section">
      <div class="brand-logo">⬡ KARUVI</div>
      <div class="brand-tag">SOURCETRAIL ENGINE</div>
      <div class="top-stats">
        <div class="stat-badge">Modules: <b id="stat-modules">0</b></div>
        <div class="stat-badge">Links: <b id="stat-links">0</b></div>
        <div class="stat-badge">Cross-Refs: <b id="stat-xrefs">0</b></div>
        <div class="stat-badge" id="cycle-badge-wrap" style="display:none;">
          <span class="cycle-badge" id="stat-cycles" onclick="filterCycles()">⚠️ 0 Cycles</span>
        </div>
      </div>
    </div>

    <div class="top-controls">
      <button class="tool-btn" id="btn-layout" onclick="toggleLayout()">Mode: Force Atlas</button>
      <button class="tool-btn" id="btn-ext" onclick="toggleExternal()">External: On</button>
      <button class="tool-btn" id="btn-xref" onclick="toggleCrossRefs()">Symbols: On</button>
      <button class="tool-btn" onclick="fitGraph()">⤢ Fit</button>
      <button class="tool-btn" id="btn-freeze" onclick="toggleFreeze()">❄️ Freeze</button>
    </div>
  </div>

  <!-- BLAST ACTIVE BANNER -->
  <div id="blast-banner">
    <span id="blast-msg">💥 Tracing Blast Radius for symbol...</span>
    <button onclick="clearBlastRadius()">✕ Reset View</button>
  </div>

  <!-- 3-PANE WORKSPACE -->
  <div id="workspace">
    <!-- LEFT EXPLORER -->
    <div id="left-panel">
      <div class="panel-header">
        <span class="panel-title">Project Explorer</span>
      </div>
      <div class="search-box-wrap">
        <input type="text" id="omni-search" class="search-input" placeholder="Quick search modules or symbols ( / )...">
      </div>
      <div class="explorer-tabs">
        <button class="tab-btn active" id="tab-btn-files" onclick="switchLeftTab('files')">Files</button>
        <button class="tab-btn" id="tab-btn-symbols" onclick="switchLeftTab('symbols')">Symbols</button>
        <button class="tab-btn" id="tab-btn-cycles" onclick="switchLeftTab('cycles')">Cycles</button>
      </div>
      <div class="explorer-content" id="explorer-content"></div>
    </div>

    <!-- CENTER GRAPH CANVAS -->
    <div id="center-canvas">
      <div id="breadcrumbs-bar">
        <span>project</span> / <span id="crumb-file" class="active">select a module</span>
      </div>
      <div id="network-canvas"></div>

      <!-- SOURCETRAIL LEGEND -->
      <div class="canvas-legend">
        <div class="legend-row">
          <div class="legend-dot" style="background: #38bdf8;"></div>
          <span>Internal Module</span>
        </div>
        <div class="legend-row">
          <div class="legend-dot" style="background: #64748b;"></div>
          <span>External Dependency</span>
        </div>
        <div class="legend-row">
          <div class="legend-line" style="background: #38bdf8;"></div>
          <span>Module Import</span>
        </div>
        <div class="legend-row">
          <div class="legend-line" style="background: #f85149;"></div>
          <span>Symbol Call / Usage</span>
        </div>
        <div class="legend-row">
          <div class="legend-dot" style="background: #f85149;"></div>
          <span>Circular Dependency</span>
        </div>
      </div>
    </div>

    <!-- RIGHT SOURCETRAIL INSPECTOR -->
    <div id="right-panel">
      <div class="inspector-header">
        <div class="inspector-title-row">
          <div class="inspector-title" id="insp-title">Select Module</div>
        </div>
        <div class="inspector-path" id="insp-path">Click any node in the graph to inspect its AST & symbols</div>
        <div class="meta-metrics">
          <div class="meta-pill"><div class="num" id="insp-loc">-</div><div class="lbl">LOC</div></div>
          <div class="meta-pill"><div class="num" id="insp-funcs">-</div><div class="lbl">Functions</div></div>
          <div class="meta-pill"><div class="num" id="insp-classes">-</div><div class="lbl">Classes</div></div>
          <div class="meta-pill"><div class="num" id="insp-in">-</div><div class="lbl">Inbound</div></div>
        </div>
      </div>

      <div class="explorer-tabs" style="border-top: 1px solid var(--border);">
        <button class="tab-btn active" id="right-tab-tree" onclick="switchRightTab('tree')">🌳 AST Tree</button>
        <button class="tab-btn" id="right-tab-symbols" onclick="switchRightTab('symbols')">⚡ Symbols & Blast</button>
        <button class="tab-btn" id="right-tab-deps" onclick="switchRightTab('deps')">🔗 Dependencies</button>
        <button class="tab-btn" id="right-tab-cycles" onclick="switchRightTab('cycles')">⚠️ Cycles</button>
      </div>

      <div class="inspector-body" id="inspector-body">
        <div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 40px;">
          Select any node in the center graph or left explorer to inspect its intra-file tree, symbols, and dependencies.
        </div>
      </div>
    </div>
  </div>

  <script>
    const data = __GRAPH_JSON__;

    // State
    let selectedNodeId = null;
    let isHierarchical = false;
    let showExternal = true;
    let showCrossRefs = true;
    let isFrozen = false;
    let blastActive = false;
    let currentLeftTab = 'files';
    let currentRightTab = 'tree';

    // Populate Top Stats
    document.getElementById('stat-modules').innerText = data.nodes.internal.length;
    document.getElementById('stat-links').innerText = data.edges.length;
    document.getElementById('stat-xrefs').innerText = data.cross_references.length;
    if (data.cycles && data.cycles.length > 0) {
      const cBadge = document.getElementById('stat-cycles');
      cBadge.innerText = `⚠️ ${data.cycles.length} Circular Loops`;
      document.getElementById('cycle-badge-wrap').style.display = 'block';
    }

    // Node & Edge Sets
    const nodeMap = new Map();
    const visNodes = [];
    const visEdges = [];

    data.nodes.internal.forEach(n => {
      nodeMap.set(n.id, n);
      visNodes.push({
        id: n.id,
        label: n.name,
        title: `${n.id}\\n${n.line_count} LOC | ${n.function_count} fn | ${n.class_count} cls`,
        shape: 'box',
        margin: 10,
        color: {
          background: '#161b22',
          border: '#38bdf8',
          highlight: { background: '#1f293d', border: '#79c0ff' }
        },
        font: { color: '#f0f6fc', size: 13, face: 'Fira Code, monospace' },
        borderWidth: 1.5,
        shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 8, x: 2, y: 2 }
      });
    });

    data.nodes.external.forEach(n => {
      nodeMap.set(n.id, n);
      visNodes.push({
        id: n.id,
        label: n.name,
        title: `External Package: ${n.name}`,
        shape: 'box',
        margin: 7,
        color: {
          background: '#0d1117',
          border: '#64748b',
          highlight: { background: '#1c2433', border: '#94a3b8' }
        },
        font: { color: '#8b949e', size: 11, face: 'Fira Code, monospace' },
        borderWidth: 1,
        shapeProperties: { borderDashes: [4, 4] }
      });
    });

    data.edges.forEach((e, idx) => {
      const isXRef = e.type === 'symbol_reference';
      visEdges.push({
        id: 'edge_' + idx,
        from: e.source,
        to: e.target,
        arrows: { to: { enabled: true, scaleFactor: 0.7 } },
        color: {
          color: isXRef ? '#f85149' : '#38bdf8',
          highlight: isXRef ? '#ff7b72' : '#79c0ff',
          opacity: isXRef ? 0.75 : 0.45
        },
        dashes: isXRef ? [5, 5] : false,
        width: isXRef ? 1.5 : 1.2,
        title: e.details || (isXRef ? `Uses: ${e.symbol}` : 'Imports'),
        edgeType: e.type,
        isExternal: e.target.startsWith('ext:')
      });
    });

    const graphDataSet = {
      nodes: new vis.DataSet(visNodes),
      edges: new vis.DataSet(visEdges)
    };

    const container = document.getElementById('network-canvas');
    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -75,
          centralGravity: 0.015,
          springLength: 130,
          springConstant: 0.08,
          damping: 0.85
        },
        stabilization: { iterations: 180 }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: true
      }
    };

    const network = new vis.Network(container, graphDataSet, options);

    // Node Selection Handler
    network.on('click', function(params) {
      if (params.nodes.length > 0) {
        selectNode(params.nodes[0]);
      } else {
        clearSelection();
      }
    });

    function selectNode(nodeId) {
      selectedNodeId = nodeId;
      const node = nodeMap.get(nodeId);
      if (!node) return;

      // Update breadcrumb
      document.getElementById('crumb-file').innerText = node.path || node.name;

      // Sourcetrail Focus Dimming: Highlight 1st degree neighbors, dim the rest
      const connectedNodes = new Set(network.getConnectedNodes(nodeId));
      connectedNodes.add(nodeId);

      const connectedEdges = new Set(network.getConnectedEdges(nodeId));

      visNodes.forEach(n => {
        const isConnected = connectedNodes.has(n.id);
        graphDataSet.nodes.update({
          id: n.id,
          opacity: isConnected ? 1.0 : 0.12
        });
      });

      visEdges.forEach(e => {
        const isConnected = connectedEdges.has(e.id);
        graphDataSet.edges.update({
          id: e.id,
          color: {
            opacity: isConnected ? 0.9 : 0.05
          }
        });
      });

      // Update inspector
      renderInspector(node);
      highlightExplorerItem(nodeId);
    }

    function clearSelection() {
      selectedNodeId = null;
      document.getElementById('crumb-file').innerText = 'select a module';
      visNodes.forEach(n => {
        graphDataSet.nodes.update({ id: n.id, opacity: 1.0 });
      });
      visEdges.forEach(e => {
        graphDataSet.edges.update({
          id: e.id,
          color: { opacity: e.edgeType === 'symbol_reference' ? 0.75 : 0.45 }
        });
      });
      highlightExplorerItem(null);
    }

    // Render Right Inspector
    function renderInspector(node) {
      document.getElementById('insp-title').innerText = node.name;
      document.getElementById('insp-path').innerText = node.path || node.id;
      document.getElementById('insp-loc').innerText = node.line_count || '-';
      document.getElementById('insp-funcs').innerText = node.function_count || '0';
      document.getElementById('insp-classes').innerText = node.class_count || '0';
      document.getElementById('insp-in').innerText = node.in_degree || '0';

      updateRightTabContent(node);
    }

    function switchRightTab(tab) {
      currentRightTab = tab;
      ['tree', 'symbols', 'deps', 'cycles'].forEach(t => {
        const btn = document.getElementById('right-tab-' + t);
        if (btn) btn.classList.toggle('active', t === tab);
      });
      if (selectedNodeId) {
        updateRightTabContent(nodeMap.get(selectedNodeId));
      }
    }

    function updateRightTabContent(node) {
      const container = document.getElementById('inspector-body');
      if (!node || !node.is_internal) {
        container.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem;">External third-party dependency. No internal AST available.</div>`;
        return;
      }

      if (currentRightTab === 'tree') {
        container.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div class="section-title" style="margin:0; border:none;">Intra-File AST & Code Flow</div>
            <div style="display:flex; gap:6px;">
              <button class="tool-btn" style="padding:2px 6px; font-size:0.7rem;" onclick="expandAllAst()">Expand</button>
              <button class="tool-btn" style="padding:2px 6px; font-size:0.7rem;" onclick="collapseAllAst()">Collapse</button>
            </div>
          </div>
          <div class="ast-tree-view" id="ast-container">
            ${renderAstTreeHtml(node.code_flow)}
          </div>
        `;
      } else if (currentRightTab === 'symbols') {
        let html = `<div class="section-title">Declared Classes & Functions</div>`;
        if (node.classes && node.classes.length > 0) {
          node.classes.forEach(c => {
            html += `
              <div class="symbol-card">
                <div class="symbol-name-wrap">
                  <span class="badge-kind badge-class">Class</span>
                  <span class="symbol-name">${c}</span>
                </div>
                <button class="blast-btn" onclick="traceBlastRadius('${c}')">💥 Blast</button>
              </div>
            `;
          });
        }
        if (node.functions && node.functions.length > 0) {
          node.functions.forEach(f => {
            html += `
              <div class="symbol-card">
                <div class="symbol-name-wrap">
                  <span class="badge-kind badge-def">def</span>
                  <span class="symbol-name">${f}()</span>
                </div>
                <button class="blast-btn" onclick="traceBlastRadius('${f}')">💥 Blast</button>
              </div>
            `;
          });
        }
        if ((!node.classes || node.classes.length === 0) && (!node.functions || node.functions.length === 0)) {
          html += `<div style="color:var(--text-muted); font-size:0.8rem;">No top-level classes or functions declared.</div>`;
        }

        // Module symbols / variables with UUID
        if (node.scope && node.scope.symbols) {
          html += `<div class="section-title" style="margin-top:16px;">Scope Symbols & Variables</div>`;
          Object.values(node.scope.symbols).forEach(s => {
            const isRef = s.is_reference;
            const uuid = s.uuid || '';
            html += `
              <div class="symbol-card">
                <div class="symbol-name-wrap">
                  <span class="badge-kind ${isRef ? 'badge-ref' : 'badge-var'}">${isRef ? 'Ref' : 'Var'}</span>
                  <span class="symbol-name">${s.name}</span>
                  <div class="symbol-desc">${uuid ? 'uuid: ' + uuid.substring(0, 18) + '...' : ''}</div>
                </div>
                ${uuid && !uuid.startsWith('import:') ? `<button class="blast-btn" onclick="traceBlastRadius('${uuid}', '${s.name}')">💥 Blast</button>` : ''}
              </div>
            `;
          });
        }
        container.innerHTML = html;
      } else if (currentRightTab === 'deps') {
        const outEdges = data.edges.filter(e => e.source === node.id);
        const inEdges = data.edges.filter(e => e.target === node.id);

        let html = `
          <div class="section-title">Upstream Dependencies (${outEdges.length} imports)</div>
          <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:16px;">
            ${outEdges.length === 0 ? '<span style="color:var(--text-muted); font-size:0.75rem;">None</span>' : ''}
            ${outEdges.map(e => `
              <div class="dep-link" onclick="focusAndSelectNode('${e.target}')">
                <span>→ ${e.target}</span>
                <span class="badge-kind badge-stmt">${e.type}</span>
              </div>
            `).join('')}
          </div>

          <div class="section-title">Downstream Dependents (${inEdges.length} imported by)</div>
          <div style="display:flex; flex-direction:column; gap:4px;">
            ${inEdges.length === 0 ? '<span style="color:var(--text-muted); font-size:0.75rem;">None</span>' : ''}
            ${inEdges.map(e => `
              <div class="dep-link" onclick="focusAndSelectNode('${e.source}')">
                <span>← ${e.source}</span>
                <span class="badge-kind badge-stmt">${e.type}</span>
              </div>
            `).join('')}
          </div>
        `;
        container.innerHTML = html;
      } else if (currentRightTab === 'cycles') {
        const relevantCycles = (data.cycles || []).filter(c => c.includes(node.id));
        if (relevantCycles.length === 0) {
          container.innerHTML = `<div style="color:#3fb950; font-size:0.85rem;">✔ No circular dependencies involving this module.</div>`;
        } else {
          let html = `<div class="section-title" style="color:var(--color-cycle);">Circular Dependency Loops (${relevantCycles.length})</div>`;
          relevantCycles.forEach((c, idx) => {
            html += `
              <div class="symbol-card" style="border-color:rgba(248,81,73,0.3); flex-direction:column; align-items:flex-start;">
                <div style="font-weight:600; font-size:0.8rem; color:#ff7b72; margin-bottom:6px;">Cycle #${idx + 1} (${c.length - 1} steps)</div>
                <div style="font-family:'Fira Code', monospace; font-size:0.72rem; line-height:1.6; color:var(--text-secondary);">
                  ${c.map((step, i) => `<div>${i > 0 ? '↳ ' : ''}<b style="color:${step === node.id ? 'var(--accent)' : 'var(--text)'}">${step}</b></div>`).join('')}
                </div>
                <button class="blast-btn" style="margin-top:8px;" onclick="highlightCycle(${JSON.stringify(c).replace(/"/g, '&quot;')})">Highlight Cycle in Graph</button>
              </div>
            `;
          });
          container.innerHTML = html;
        }
      }
    }

    // Render AST Tree View
    function renderAstTreeHtml(flow) {
      if (!flow) return '<div style="color:var(--text-muted)">No AST flow available.</div>';

      function walk(node) {
        let name = node.name || (node.variable ? node.variable.name : 'Node');
        let kindBadge = '<span class="badge-kind badge-stmt">node</span>';

        if (name.startsWith('def ') || name.includes('function')) kindBadge = '<span class="badge-kind badge-def">def</span>';
        else if (name.startsWith('class ') || name.includes('class')) kindBadge = '<span class="badge-kind badge-class">class</span>';
        else if (node.variable) {
          kindBadge = node.variable.is_reference
            ? '<span class="badge-kind badge-ref">ref</span>'
            : '<span class="badge-kind badge-var">var</span>';
        }

        const hasChildren = node.children && node.children.length > 0;
        let html = `<div class="ast-node">`;
        html += `<div class="ast-label" onclick="toggleAstNode(this)">
          ${hasChildren ? '▼' : '•'} ${kindBadge} <span style="color:var(--text)">${name}</span>
        </div>`;

        if (hasChildren) {
          html += `<div class="ast-children">`;
          node.children.forEach(c => {
            html += walk(c);
          });
          html += `</div>`;
        }
        html += `</div>`;
        return html;
      }

      return walk(flow);
    }

    function toggleAstNode(el) {
      const children = el.nextElementSibling;
      if (children && children.classList.contains('ast-children')) {
        const isHidden = children.style.display === 'none';
        children.style.display = isHidden ? 'block' : 'none';
        el.innerHTML = el.innerHTML.replace(isHidden ? '▶' : '▼', isHidden ? '▼' : '▶');
      }
    }

    function expandAllAst() {
      document.querySelectorAll('.ast-children').forEach(c => c.style.display = 'block');
    }
    function collapseAllAst() {
      document.querySelectorAll('.ast-children').forEach(c => c.style.display = 'none');
    }

    // LEFT EXPLORER LOGIC
    function switchLeftTab(tab) {
      currentLeftTab = tab;
      ['files', 'symbols', 'cycles'].forEach(t => {
        document.getElementById('tab-btn-' + t).classList.toggle('active', t === tab);
      });
      renderLeftExplorer();
    }

    function renderLeftExplorer() {
      const container = document.getElementById('explorer-content');
      const query = document.getElementById('omni-search').value.toLowerCase().trim();

      if (currentLeftTab === 'files') {
        const files = data.nodes.internal.filter(n => !query || n.id.toLowerCase().includes(query) || n.name.toLowerCase().includes(query));
        container.innerHTML = files.map(f => `
          <div class="tree-item ${selectedNodeId === f.id ? 'selected' : ''}" id="tree-item-${f.id.replace(/[^a-zA-Z0-9]/g, '_')}" onclick="focusAndSelectNode('${f.id}')">
            <span class="item-icon" style="color:var(--accent)">📄</span>
            <span class="item-name">${f.id}</span>
            <span class="item-badge">${f.line_count}L</span>
          </div>
        `).join('');
      } else if (currentLeftTab === 'symbols') {
        let symbols = [];
        data.nodes.internal.forEach(n => {
          (n.classes || []).forEach(c => symbols.push({ name: c, type: 'class', file: n.id }));
          (n.functions || []).forEach(fn => symbols.push({ name: fn, type: 'function', file: n.id }));
        });
        if (query) {
          symbols = symbols.filter(s => s.name.toLowerCase().includes(query) || s.file.toLowerCase().includes(query));
        }
        container.innerHTML = symbols.map(s => `
          <div class="tree-item" onclick="focusAndSelectNode('${s.file}')">
            <span class="item-icon">${s.type === 'class' ? '🏷️' : '⚡'}</span>
            <span class="item-name">${s.name}</span>
            <span class="item-badge">${s.type === 'class' ? 'Class' : 'Def'}</span>
          </div>
        `).join('');
      } else if (currentLeftTab === 'cycles') {
        const cycles = data.cycles || [];
        if (cycles.length === 0) {
          container.innerHTML = `<div style="padding:16px; color:#3fb950; font-size:0.8rem;">✔ No circular dependencies in this repository.</div>`;
        } else {
          container.innerHTML = cycles.map((c, idx) => `
            <div class="tree-item" style="flex-direction:column; align-items:flex-start; gap:4px; padding:10px 12px; border-bottom:1px solid var(--border-subtle);" onclick="highlightCycle(${JSON.stringify(c).replace(/"/g, '&quot;')})">
              <div style="font-weight:600; color:#ff7b72; font-size:0.78rem;">⚠️ Loop #${idx + 1} (${c.length - 1} modules)</div>
              <div style="font-size:0.72rem; color:var(--text-secondary); font-family:'Fira Code', monospace;">
                ${c.join(' → ')}
              </div>
            </div>
          `).join('');
        }
      }
    }

    document.getElementById('omni-search').addEventListener('input', renderLeftExplorer);
    window.addEventListener('keydown', e => {
      if (e.key === '/' && document.activeElement !== document.getElementById('omni-search')) {
        e.preventDefault();
        document.getElementById('omni-search').focus();
      }
    });

    function highlightExplorerItem(nodeId) {
      document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('selected'));
      if (nodeId) {
        const item = document.getElementById('tree-item-' + nodeId.replace(/[^a-zA-Z0-9]/g, '_'));
        if (item) {
          item.classList.add('selected');
          item.scrollIntoView({ block: 'nearest' });
        }
      }
    }

    function focusAndSelectNode(nodeId) {
      if (!nodeMap.has(nodeId)) return;
      network.focus(nodeId, { scale: 1.2, animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
      network.selectNodes([nodeId]);
      selectNode(nodeId);
    }

    // BLAST RADIUS TRACER
    function traceBlastRadius(identifier, displayName) {
      displayName = displayName || identifier;
      const usages = data.cross_references.filter(xref => xref.uuid === identifier || xref.symbol === identifier);

      const targetNodes = new Set();
      const targetEdgeIds = new Set();

      usages.forEach(u => {
        targetNodes.add(u.source_file);
        targetNodes.add(u.target_file);
      });

      if (selectedNodeId) targetNodes.add(selectedNodeId);

      // Highlight in graph
      visNodes.forEach(n => {
        graphDataSet.nodes.update({
          id: n.id,
          opacity: targetNodes.has(n.id) ? 1.0 : 0.08,
          color: targetNodes.has(n.id) ? { background: '#2d1517', border: '#f85149' } : undefined
        });
      });

      visEdges.forEach(e => {
        const isMatch = e.edgeType === 'symbol_reference' && e.title && e.title.includes(displayName);
        graphDataSet.edges.update({
          id: e.id,
          color: { opacity: isMatch ? 1.0 : 0.05, color: isMatch ? '#f85149' : undefined },
          width: isMatch ? 3 : 1
        });
      });

      // Show banner
      document.getElementById('blast-msg').innerText = `💥 Blast Radius for '${displayName}': Impacting ${usages.length} cross-module call site(s) across ${targetNodes.size} module(s).`;
      document.getElementById('blast-banner').style.display = 'flex';
      blastActive = true;
    }

    function clearBlastRadius() {
      document.getElementById('blast-banner').style.display = 'none';
      blastActive = false;
      if (selectedNodeId) {
        selectNode(selectedNodeId);
      } else {
        clearSelection();
      }
    }

    function highlightCycle(cycleNodes) {
      const nodeSet = new Set(cycleNodes);
      visNodes.forEach(n => {
        const inCycle = nodeSet.has(n.id);
        graphDataSet.nodes.update({
          id: n.id,
          opacity: inCycle ? 1.0 : 0.08,
          color: inCycle ? { background: '#2d1517', border: '#f85149' } : undefined
        });
      });

      visEdges.forEach(e => {
        const isCycleEdge = nodeSet.has(e.from) && nodeSet.has(e.to);
        graphDataSet.edges.update({
          id: e.id,
          color: { opacity: isCycleEdge ? 1.0 : 0.05, color: isCycleEdge ? '#f85149' : undefined },
          width: isCycleEdge ? 3 : 1
        });
      });

      document.getElementById('blast-msg').innerText = `⚠️ Circular Dependency Loop: ${cycleNodes.join(' → ')}`;
      document.getElementById('blast-banner').style.display = 'flex';
      blastActive = true;
    }

    // TOP BAR CONTROLS
    function toggleLayout() {
      isHierarchical = !isHierarchical;
      document.getElementById('btn-layout').innerText = isHierarchical ? 'Mode: Hierarchical DAG' : 'Mode: Force Atlas';
      network.setOptions({
        layout: {
          hierarchical: isHierarchical ? {
            direction: 'UD',
            sortMethod: 'directed',
            levelSeparation: 150,
            nodeSpacing: 180
          } : false
        },
        physics: {
          enabled: !isHierarchical
        }
      });
    }

    function toggleExternal() {
      showExternal = !showExternal;
      document.getElementById('btn-ext').innerText = showExternal ? 'External: On' : 'External: Off';
      data.nodes.external.forEach(n => {
        graphDataSet.nodes.update({ id: n.id, hidden: !showExternal });
      });
      visEdges.forEach(e => {
        if (e.isExternal) {
          graphDataSet.edges.update({ id: e.id, hidden: !showExternal });
        }
      });
    }

    function toggleCrossRefs() {
      showCrossRefs = !showCrossRefs;
      document.getElementById('btn-xref').innerText = showCrossRefs ? 'Symbols: On' : 'Symbols: Off';
      visEdges.forEach(e => {
        if (e.edgeType === 'symbol_reference') {
          graphDataSet.edges.update({ id: e.id, hidden: !showCrossRefs });
        }
      });
    }

    function fitGraph() {
      network.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
    }

    function toggleFreeze() {
      isFrozen = !isFrozen;
      network.setOptions({ physics: { enabled: !isFrozen } });
      const btn = document.getElementById('btn-freeze');
      btn.innerText = isFrozen ? '🔥 Unfreeze' : '❄️ Freeze';
      btn.classList.toggle('active', isFrozen);
    }

    function filterCycles() {
      switchLeftTab('cycles');
    }

    // Init
    renderLeftExplorer();
  </script>
</body>
</html>
"""
