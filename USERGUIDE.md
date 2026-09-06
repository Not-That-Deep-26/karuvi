
---

## Table of Contents

- [1. Installation & Setup](#1-installation--setup)
- [2. Quickstart (First 5 Minutes)](#2-quickstart-first-5-minutes)
- [3. CLI Complete Reference](#3-cli-complete-reference)
  - [Cheat-Sheet Table](#cheat-sheet-table)
  - [Intra-File AST Tree (`--tree`, `-t`)](#intra-file-ast-tree---tree--t)
  - [Dependency Topology (`--deps`)](#dependency-topology---deps)
  - [Blast Radius Tracer (`--blast`)](#blast-radius-tracer---blast)
  - [Circular Dependency Detection (`--cycles`)](#circular-dependency-detection---cycles)
  - [Symbol Inspector (`--inspect`)](#symbol-inspector---inspect)
  - [Code Flow Chart (`--chart`)](#code-flow-chart---chart)
  - [ASCII Graph Matrix (`--graph`)](#ascii-graph-matrix---graph)
  - [Exporting Reports (`--html`, `--json`, `--mermaid`)](#exporting-reports---html---json---mermaid)
- [4. Interactive Terminal Navigator (`-i`)](#4-interactive-terminal-navigator--i)
- [5. Sourcetrail HTML Visualizer Guide](#5-sourcetrail-html-visualizer-guide)
  - [3-Pane Workspace Breakdown](#3-pane-workspace-breakdown)
  - [Exploring Large Repositories](#exploring-large-repositories)
  - [One-Click Blast Radius Highlighting](#one-click-blast-radius-highlighting)
  - [Investigating Circular Dependencies](#investigating-circular-dependencies)
- [6. Karuvi Daemon & HTTP API](#6-karuvi-daemon--http-api)
- [7. Programmatic Python API](#7-programmatic-python-api)
- [8. Troubleshooting & FAQ](#8-troubleshooting--faq)

---

## 1. Installation & Setup

### Requirements
- **Python**: 3.10 or newer
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (strongly recommended) or standard `pip`

### Setup with `uv`
Inside the repository clone:
```bash
# Sync dependencies automatically into the virtual environment
uv sync
```

Dependencies include `tree-sitter`, `tree-sitter-python`, `rich`, `fastapi`, and `uvicorn`.

### Running Karuvi
You can run Karuvi via `uv run karuvi` or directly with `uv run python cli.py`:
```bash
uv run karuvi /path/to/target-repo
# or
uv run python cli.py /path/to/target-repo
```

---

## 2. Quickstart (First 5 Minutes)

### Step 1: Scan a Repository
Point Karuvi at any local Python repository (e.g. `/home/tarun/microdot-main/`):
```bash
uv run karuvi /home/tarun/microdot-main/
```
Karuvi automatically:
1. Crawls all `.py` files (excluding `.venv`, `__pycache__`, `.git`, `node_modules`).
2. Parses every module using tree-sitter into an in-memory graph.
3. Indexes declarations, variable scopes, UUIDs, imports, and cross-file usages.
4. Renders the ASCII Dashboard with metrics, connection tables, and external dependencies.

### Step 2: Generate the Sourcetrail Interactive Visualizer
Export an interactive visualizer HTML file:
```bash
uv run karuvi /home/tarun/microdot-main/ --html microdot_graph.html
```
Open `microdot_graph.html` in any browser:
```bash
xdg-open microdot_graph.html   # Linux
open microdot_graph.html       # macOS
start microdot_graph.html      # Windows
```

---

## 3. CLI Complete Reference

### Cheat-Sheet Table
To view the built-in reference table anytime in the terminal:
```bash
uv run karuvi --commands
```

| Command / Flag | Alias | Description | Example Usage |
|---|---|---|---|
| `karuvi <repo>` | — | Scan repository and display summary dashboard | `uv run karuvi /path/to/repo` |
| `--tree <file>` | `-t`, `--file-tree` | Print aesthetic ASCII intra-file AST & code flow tree | `uv run karuvi <repo> -t src/app.py` |
| `--deps <file>` | — | Print upstream imports & downstream dependents tree | `uv run karuvi <repo> --deps src/app.py` |
| `--blast <uuid\|name>` | `--blast-radius` | Trace cross-module call sites and impact of a symbol | `uv run karuvi <repo> --blast verify_token` |
| `--cycles` | — | Detect & display circular dependency loops in ASCII | `uv run karuvi <repo> --cycles` |
| `--inspect <file>` | — | Inspect classes, methods, functions & symbols in a file | `uv run karuvi <repo> --inspect src/app.py` |
| `--chart <file>` | `--file-chart` | Print indentation-based control flow chart | `uv run karuvi <repo> --chart src/app.py` |
| `--graph` | `--ascii-graph` | Display ASCII connectivity matrix / summary table | `uv run karuvi <repo> --graph` |
| `--interactive` | `-i` | Launch interactive terminal explorer & AST navigator | `uv run karuvi <repo> -i` |
| `--html <path>` | — | Export standalone Sourcetrail interactive HTML visualizer | `uv run karuvi <repo> --html graph.html` |
| `--json <path>` | `-j` | Export full repository analysis and AST dump | `uv run karuvi <repo> --json report.json` |
| `--mermaid` | — | Output Mermaid.js dependency diagram to stdout | `uv run karuvi <repo> --mermaid` |
| `--serve` | — | Launch FastAPI stateful daemon server on port 8000 | `uv run karuvi <repo> --serve` |
| `--verbose` | `-v` | Show verbose parser warning messages | `uv run karuvi <repo> -v` |

---

### Intra-File AST Tree (`--tree`, `-t`)
Inspects the inner syntax tree, control flow statements, variable declarations, and nested scopes for a single file.

```bash
uv run karuvi /home/tarun/microdot-main/ -t src/microdot/session.py
```

**Output Breakdown:**
- `📦 <file_name>`: Module root with total functions, classes, and variable symbols.
- `🏷️ Classes`: Declared class blocks, unique UUIDs, and their methods with argument signatures.
- `⚡ Top-level Functions`: Declared functions with parameters.
- `🌳 AST Code Flow & Scopes`:
  - `🏷️ class <Name>`: Class scope boundaries.
  - `⚡ def <name>(<args>)`: Function bodies.
  - `🔹 <var_name>`: New variable assignment with generated UUID.
  - `↪️ <var_name>`: Variable reference pointing back to its declaration line (`ref -> L24`).

---

### Dependency Topology (`--deps`)
Inspects what a specific file depends on and what depends on it:

```bash
uv run karuvi /home/tarun/microdot-main/ --deps src/microdot/asgi.py
```

**Displays:**
1. **⬆ Upstream Dependencies**:
   - Internal module imports (e.g. `src/microdot/microdot.py`).
   - External third-party packages (e.g. `fastapi`, `jinja2`).
2. **⬇ Downstream Dependents**:
   - Internal files importing this module.
3. **🔀 Cross-Module Symbol Usages**:
   - Specific symbols this file uses from other modules.
   - Specific symbols this file exports that are called elsewhere.

---

### Blast Radius Tracer (`--blast`)
Before modifying or refactoring a function, class, or symbol, trace its blast radius across the whole codebase:

```bash
# By symbol name:
uv run karuvi /home/tarun/microdot-main/ --blast subapp

# Or by UUID:
uv run karuvi /home/tarun/microdot-main/ --blast ffb6be2d-e62d-4091-a957-3f9547d6d33a
```

**Output:**
- **📍 Declared at**: `examples/subapps/subapp.py:3`
- **🎯 Impacted Call Sites**:
  - `💥 examples/subapps/app.py:5:10 (scope: module)`
- **Impact Summary**: Number of affected call sites across distinct files.

---

### Circular Dependency Detection (`--cycles`)
Detects circular import loops across all internal modules using cycle path tracing:

```bash
uv run karuvi /path/to/repo --cycles
```

If loops are detected, Karuvi draws ASCII loop boxes showing the exact circular chain:
```text
⚠️  Detected 1 Circular Dependency Loop(s):

Loop #1 (3 modules):
  ┌──► [src/app.py]
  │        │ imports
  │        ▼
  │    [src/utils.py]
  │        │ imports
  │        ▼
  │    [src/config.py]
  │        │ imports src/app.py
  └────────┘
```
If no cycles exist, it outputs a clean validation banner:
`✔ No circular dependencies detected in repository modules!`

---

### Symbol Inspector (`--inspect`)
Prints a structured terminal summary of all symbols declared in a specific file:

```bash
uv run karuvi /home/tarun/microdot-main/ --inspect src/microdot/session.py
```
Lists:
- Function signatures with assigned UUIDs.
- Classes and their member methods.
- Module-level variables and imported alias mappings.

---

### Code Flow Chart (`--chart`)
Renders an indentation-based control flow outline showing nested statements, function definitions, and expression blocks:

```bash
uv run karuvi /home/tarun/microdot-main/ --chart src/microdot/session.py
```

---

### ASCII Graph Matrix (`--graph`)
Displays a whole-repository connectivity matrix in the terminal:

```bash
uv run karuvi /home/tarun/microdot-main/ --graph
```
Summarizes internal imports, external dependencies, and inbound/outbound degrees for every module.

---

### Exporting Reports (`--html`, `--json`, `--mermaid`)

#### 1. Interactive HTML Visualizer (`--html`)
```bash
uv run karuvi /home/tarun/microdot-main/ --html microdot_sourcetrail.html
```
Produces a completely self-contained HTML file (no server needed) with the Sourcetrail 3-pane architecture.

#### 2. Full Analysis JSON (`--json`)
```bash
uv run karuvi /home/tarun/microdot-main/ --json analysis.json
```
Exports:
- Whole graph metrics (`nodes`, `edges`, `cross_references`, `cycles`).
- Full module AST tree dumps (`code_flow`, `scope`, `functions`, `classes`).

#### 3. Mermaid Diagram (`--mermaid`)
```bash
uv run karuvi /home/tarun/microdot-main/ --mermaid > dependency_graph.mmd
```
Outputs a Mermaid.js diagram ready to embed in Markdown documentation.

---

## 4. Interactive Terminal Navigator (`-i`)

For exploring a codebase interactively without re-running terminal commands:

```bash
uv run karuvi /home/tarun/microdot-main/ -i
```

An interactive menu appears:
```text
╭────────────────────── Karuvi Interactive Menu ──────────────────────╮
│ [1] 🌳 View Intra-File Tree       [2] ⚡ Inspect File Symbols        │
│ [3] 🔗 View Dependencies (In/Out) [4] 💥 Trace Blast Radius         │
│ [5] ⚠️  Detect Circular Imports   [6] 📊 Full Repository Dashboard  │
│ [7] 🌐 Export Sourcetrail HTML    [8] 💾 Export JSON Report         │
│ [?] 🛠️  Show Commands Reference    [q] Exit                          │
╰─────────────────────────────────────────────────────────────────────╯
Select an action [1-8, ?, q]: 
```

- **Fuzzy Search**: When selecting `[1]`, `[2]`, or `[3]`, type any substring of the file name (e.g. `session`) to filter matching files.
- **Blast Radius Lookup**: Select `[4]` and type any symbol name (e.g. `subapp`) or UUID.
- **Cycle Inspection**: Select `[5]` to immediately check circular dependencies.

---

## 5. Sourcetrail HTML Visualizer Guide

When you generate an HTML report (`--html graph.html`), opening it in your browser launches a desktop-grade architecture workstation:

```text
┌─────────────────┬───────────────────────────────────┬──────────────────┐
│ PROJECT EXPLORER│         CENTER GRAPH CANVAS       │  RIGHT INSPECTOR │
│                 │                                   │                  │
│ [Files] [Syms]  │  [Mode: Force/DAG] [Ext] [Freeze] │ [AST] [Blast]    │
│                 │  project / path / file.py         │                  │
│ 📄 session.py   │                                   │ 📦 session.py    │
│ 📄 asgi.py      │          (Active Focus)           │ ├── 🏷️ Session   │
│ 📄 auth.py      │        ┌───────────────┐          │ │   └── ⚡ get   │
│                 │        │  session.py   │          │ ├── ⚡ with_sess │
│                 │        └───────┬───────┘          │                  │
│                 │                ▼                  │ [💥 Trace Blast] │
│                 │         microdot.py               │                  │
└─────────────────┴───────────────────────────────────┴──────────────────┘
```

### 3-Pane Workspace Breakdown

#### 1. Left Explorer Panel
- **📁 Files Tab**: Hierarchical folder view showing line counts (`LOC`) and symbol counts for each file. Clicking any file focuses it in the graph and opens the inspector.
- **🔤 Symbols Tab**: Global index of all classes (`[Class]`) and functions (`[Def]`). Clicking any symbol jumps straight to its declaring file.
- **⚠️ Cycles Tab**: If circular import loops exist, they appear here. Clicking a cycle highlights that loop in the graph.
- **Omni-Search (`/`)**: Press `/` or click the search box to filter files and symbols in real time.

#### 2. Center Graph Canvas
- **Sourcetrail Focus & Dimming**:
  - Clicking any node isolates it.
  - **Inbound connections (imported by)** turn emerald green (`#34d399`).
  - **Outbound connections (imports)** turn cyan (`#38bdf8`).
  - Non-connected nodes dim to 0.12 opacity to eliminate clutter.
- **Toolbar Actions**:
  - **Mode Switcher**: Toggle between **Force Atlas** (organic physics) and **Hierarchical DAG** (layered dependency tree).
  - **External Toggle**: Show or hide 3rd-party dependencies (e.g. `fastapi`, `jinja2`).
  - **Symbols Toggle**: Show or hide cross-file symbol call edges.
  - **Freeze / Unfreeze (`❄️`)**: Lock graph node positions for static reading.
  - **Fit (`⤢`)**: Center and fit the entire graph into view.

#### 3. Right Inspector Panel
- **🌳 AST Tree Tab**:
  - Full collapsible intra-file code flow tree.
  - Color badges for `[Class]`, `[Def]`, `[Var]`, `[Ref]`, and `[Stmt]`.
  - Buttons for **Expand All** and **Collapse All**.
- **⚡ Symbols & Blast Tab**:
  - Lists all declared classes, methods, and functions.
  - Clicking **💥 Blast** traces all cross-file occurrences of the symbol and highlights affected modules in ruby red on the canvas.
- **🔗 Dependencies Tab**:
  - Direct links to upstream imports and downstream dependents. Clicking any dependency navigates the graph canvas to that node.
- **⚠️ Cycles Tab**:
  - Displays the exact circular import loops involving this file.

---

## 6. Karuvi Daemon & HTTP API

Karuvi includes a stateful FastAPI server that holds the repository graph in memory for IDE plugins, code review bots, and CI integrations.

### Starting the Daemon
```bash
uv run karuvi /path/to/repo --serve
# or
uv run uvicorn main:app --port 8000
```

### Daemon API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/init` | Initialize repository root: `{"project_root": "/path/to/repo"}` |
| `GET` | `/status` | Returns number of indexed files and parse count |
| `GET` | `/files` | Lists all parsed files and module names |
| `GET` | `/dependencies` | Query symbol references in a file: `/dependencies?file=src/app.py&start=10&end=25` |
| `GET` | `/tree` | Returns internal AST dependency tree for a file: `/tree?file=src/app.py` |
| `GET` | `/scopes` | Returns lexical scope hierarchy for a file: `/scopes?file=src/app.py` |
| `GET` | `/functions` | Returns all functions declared in a file |
| `GET` | `/classes` | Returns all classes and methods in a file |
| `GET` | `/variables` | Search for variable declarations by name across all modules |

---

## 7. Programmatic Python API

You can import and use Karuvi directly in your Python scripts:

```python
from pathlib import Path
import get_tree
from repo_graph import RepoGraphBuilder
from pointers import GlobalIndex
from rich.console import Console

# 1. Parse a single file
mod = get_tree.parse_file("src/microdot/session.py")
print(f"Functions: {[f.name for f in mod.functions]}")
print(f"Classes: {[c.name for c in mod.classes]}")

# 2. Render intra-file AST tree to terminal
Console().print(mod.code_flow._print())

# 3. Build whole-repository graph
repo_path = Path("/home/tarun/microdot-main")
global_index = GlobalIndex()
global_index.add_search_path(repo_path)

parsed_modules = {}
for p in repo_path.glob("**/*.py"):
    rel_key = str(p.relative_to(repo_path))
    parsed_modules[rel_key] = get_tree.parse_file(str(p), global_index=global_index)

builder = RepoGraphBuilder(repo_path, parsed_modules, global_index=global_index)
builder.build()

# 4. Check for cycles
print(f"Cycles: {builder.cycles}")

# 5. Export Sourcetrail HTML
Path("output_graph.html").write_text(builder.render_html(), encoding="utf-8")
```

---

## 8. Troubleshooting & FAQ

### Q: Why does Karuvi say "No Python files found"?
Make sure you pass the root directory of the repository. If running from within the repository itself, you can simply run:
```bash
uv run karuvi .
```

### Q: Are virtual environments and third-party libraries excluded?
Yes. Karuvi automatically skips directories matching:
`.venv`, `venv`, `__pycache__`, `.git`, `node_modules`, `.mypy_cache`, `.pytest_cache`, `dist`, `build`, and `.eggs`.

### Q: How are third-party imports displayed?
Imports that do not resolve to internal `.py` files in the repository (e.g. `import requests` or `import os`) are classified as **External Dependencies**. In the HTML visualizer, they appear as dashed pill nodes and can be toggled on or off with the **External** button.

### Q: Can I run Karuvi in headless or CI environments?
Yes. Pass `--json <file.json>` or `--cycles` to run headless checks:
```bash
uv run karuvi /path/to/repo --cycles
```
This returns exit code 0 and logs circular loops without prompting for interactive input.

---

*Enjoy inspecting your Python codebases with Karuvi!*
