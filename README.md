# Karuvi


```text
  ██╗  ██╗ █████╗ ██████╗ ██╗   ██╗██╗   ██╗██╗
  ██║ ██╔╝██╔══██╗██╔══██╗██║   ██║██║   ██║██║
  █████╔╝ ███████║██████╔╝██║   ██║██║   ██║██║
  ██╔═██╗ ██╔══██║██╔══██╗██║   ██║██║   ██║██║
  ██║  ██╗██║  ██║██║  ██║╚██████╔╝╚████╔╝██║
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝
 A Deterministic Codebase Architecture Comprehension Assistant
```

## Running Karuvi

Use `uv run karuvi` or `uv run python cli.py`:

```bash
# Analyze a repository and render aesthetic ASCII dashboard
uv run karuvi /path/to/repo

# Generate a Sourcetrail-grade standalone interactive HTML visualizer
uv run karuvi /path/to/repo --html graph.html

# Launch the interactive terminal navigator
uv run karuvi /path/to/repo -i
```

---

## CLI Command Reference & ASCII Tools

| Command / Flag | Description | Example Usage |
|---|---|---|
| `karuvi <repo>` | Scan repository, build in-memory graph, and display dashboard | `uv run karuvi /path/to/repo` |
| `--tree, -t <file>` | Print aesthetic ASCII intra-file AST & code flow tree with syntax badges | `uv run karuvi <repo> -t src/app.py` |
| `--deps <file>` | Print upstream imports & downstream dependents tree | `uv run karuvi <repo> --deps src/app.py` |
| `--chart <file>` | Print indentation-based control flow chart for a file | `uv run karuvi <repo> --chart src/app.py` |
| `--inspect <file>` | Inspect declared classes, methods, functions & symbols | `uv run karuvi <repo> --inspect src/app.py` |
| `--blast <uuid\|name>` | Trace cross-module blast radius & call sites of a symbol | `uv run karuvi <repo> --blast verify_token` |
| `--cycles` | Detect & display all circular dependency loops with ASCII box loops | `uv run karuvi <repo> --cycles` |
| `--graph` | Display ASCII connectivity matrix / dependency summary | `uv run karuvi <repo> --graph` |
| `--interactive, -i` | Launch interactive terminal explorer & AST navigator | `uv run karuvi <repo> -i` |
| `--html <file.html>` | Generate Sourcetrail-grade interactive 3-pane visualizer | `uv run karuvi <repo> --html graph.html` |
| `--json <file.json>` | Export complete repository analysis and AST dump | `uv run karuvi <repo> --json report.json` |
| `--mermaid` | Print Mermaid.js dependency diagram to stdout | `uv run karuvi <repo> --mermaid` |
| `--serve` | Launch FastAPI stateful daemon server on port 8000 | `uv run karuvi <repo> --serve` |

---

##  Sourcetrail-Grade Interactive HTML Visualizer

When you export with `--html graph.html`, open it in any browser for a desktop IDE experience:
- **3-Pane Workstation Layout**: Left Project Explorer, Center Graph Canvas, Right Dockable Inspector.
- **Left Explorer**:
  - **Files Tree**: Hierarchical folder/file structure with line counts and symbol badges.
  - **Symbols Index**: Quick-jump to any Class or Function.
  - **Cycles Tab**: Lists all detected circular dependency chains.
- **Center Canvas**:
  - Vis-network graph with custom node styles (internal modules vs. external packages).
  - Focus dimming: Clicking a module isolates its 1st-degree neighbors and dims the rest.
  - Top Toolbar: Force-Directed ⟷ Hierarchical DAG toggle, External toggle, Symbol toggle, Freeze, Fit view.
- **Right Inspector**:
  -  **Intra-File AST Tree**: Nested, collapsible code flow and scope tree with Expand/Collapse and filter search.
  -  **Symbols & Blast Radius**: One-click "Blast" button to trace call sites across the whole codebase.
  - **Dependencies**: Inbound and outbound links with click-to-focus navigation.
  - **Cycles**: Displays any circular chains involving the module.
