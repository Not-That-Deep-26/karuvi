# Karuvi (கருவி) — Autonomous Codebase Intelligence & Architecture Reconstruction Engine

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/uv-supported-purple.svg)](https://github.com/astral-sh/uv)
[![Parser](https://img.shields.io/badge/tree--sitter-0.26-green.svg)](https://tree-sitter.github.io/)
[![Framework](https://img.shields.io/badge/FastAPI-0.141-teal.svg)](https://fastapi.tiangolo.com/)
[![Graph](https://img.shields.io/badge/NetworkX-3.0%2B-orange.svg)](https://networkx.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Karuvi** *(Tamil for "Tool" or "Instrument")* is an advanced, high-performance static analysis and architectural reconstruction engine for Python codebases. It combines tree-sitter AST parsing, graph centrality mathematics, community detection, and heuristic flow tracing to transform raw repositories into actionable architectural models, progressive onboarding guides, and an interactive, zero-dependency **Living Codebase Atlas** web application.

---

## Table of Contents

- [1. Overview & Core Philosophy](#1-overview--core-philosophy)
- [2. Installation & Quickstart](#2-installation--quickstart)
  - [Prerequisites](#prerequisites)
  - [Installation with `uv`](#installation-with-uv)
  - [30-Second Quickstart](#30-second-quickstart)
- [3. Key Capabilities](#3-key-capabilities)
  - [Stage 1: Deep AST & Multi-Graph Static Analysis](#stage-1-deep-ast--multi-graph-static-analysis)
  - [Stage 2: Architectural Reconstruction Engine](#stage-2-architectural-reconstruction-engine)
  - [Stage 3: Multi-Tier Cognitive Onboarding Engine](#stage-3-multi-tier-cognitive-onboarding-engine)
  - [Stage 4: Living Codebase Atlas (Interactive Web Visualizer)](#stage-4-living-codebase-atlas-interactive-web-visualizer)
- [4. Complete CLI Command Reference](#4-complete-cli-command-reference)
  - [CLI Command Cheat-Sheet](#cli-command-cheat-sheet)
  - [Detailed Command Usage & Examples](#detailed-command-usage--examples)
- [5. The Living Codebase Atlas Web Interface](#5-the-living-codebase-atlas-web-interface)
  - [Tab 1: Overview Dashboard](#tab-1-overview-dashboard)
  - [Tab 2: Onboarding Tour](#tab-2-onboarding-tour)
  - [Tab 3: System Architecture](#tab-3-system-architecture)
  - [Tab 4: Graph Explorer](#tab-4-graph-explorer)
  - [Tab 5: Sourcetrail-Grade Code Explorer](#tab-5-sourcetrail-grade-code-explorer)
  - [Global Search Modal (`Cmd+K` / `Ctrl+K`)](#global-search-modal-cmdk--ctrlk)
- [6. Karuvi Daemon & REST API Reference](#6-karuvi-daemon--rest-api-reference)
  - [Starting the Daemon](#starting-the-daemon)
  - [API Endpoints](#api-endpoints)
- [7. Programmatic Python SDK API](#7-programmatic-python-sdk-api)
- [8. Architecture & Design Principles](#8-architecture--design-principles)
- [9. Troubleshooting & FAQ](#9-troubleshooting--faq)
- [10. License](#10-license)

---

## 1. Overview & Core Philosophy

Large and legacy software repositories suffer from **architectural entropy**: documentation rots, invisible circular dependencies proliferate, critical bridge modules become bottlenecks, and onboarding developers spend weeks deciphering unspoken execution paths.

Karuvi solves this by performing **deterministic, bottom-up architectural reconstruction**:

```
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│  Raw Python Source Tree │ ──> │   Tree-Sitter AST Parse │ ──> │ Multi-Graph Indexing    │
│  (.py files & packages) │     │ (scopes, UUIDs, syntax) │     │ (calls, imports, refs)  │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
                                                                             │
┌─────────────────────────┐     ┌─────────────────────────┐                  ▼
│  Living Codebase Atlas  │ <── │ Architectural Engine    │ <── ┌─────────────────────────┐
│  (Interactive HTML App) │     │ (roles, flows, bounds)  │     │ Graph Topology Metrics  │
└─────────────────────────┘     └─────────────────────────┘     │ (PageRank, centrality)  │
                                                                └─────────────────────────┘
```

1. **Zero Guesswork**: Every connection is grounded in concrete tree-sitter AST nodes, symbol definitions, calls, or imports.
2. **Cognitive Clarity**: Modules are automatically classified by architectural role (`ENTRY_CANDIDATE`, `HUB`, `BRIDGE`, `LEAF`, `CYCLE_MEMBER`, `INTERMEDIARY`).
3. **Cohesive Boundaries**: Louvain modularity clustering and directory affinity identify real architectural components without manual tagging.
4. **Zero-Dependency Portability**: Emits self-contained, standalone single-file HTML apps that require no build steps, node servers, or external services to inspect.

---

## 2. Installation & Quickstart

### Prerequisites

- **Python**: `3.13` or newer
- **Package Manager**: [uv](https://github.com/astral-sh/uv) *(strongly recommended for maximum performance)* or standard `pip`

### Installation with `uv`

Clone the Karuvi repository and sync dependencies:

```bash
git clone https://github.com/tarunness-ops/karuvi.git
cd karuvi

# Install dependencies into virtual environment instantly
uv sync
```

Alternatively, install the package in editable mode:

```bash
uv pip install -e .
```

### 30-Second Quickstart

Point Karuvi at any target Python repository to generate an interactive Living Codebase Atlas:

```bash
# Install Karuvi as a package (editable dev install)
uv pip install -e .

# Bare run: analyze, export the Atlas, auto-serve it over local HTTP, and open it
# in your default browser (Ctrl+C stops the server)
uv run karuvi /path/to/target-repo
```

Or run the classic terminal dashboard (former default) with opt-in exports:

```bash
uv run karuvi /path/to/target-repo explore
```

When prompted:
```text
Save analysis outputs? ([j]son / [h]tml / [b]oth / [n]one) [b]: h
✔ Saved Living Codebase Atlas interactive HTML visualizer to: /path/to/target-repo/karuvi_atlas.html
```

---

## 3. Key Capabilities

### Stage 1: Deep AST & Multi-Graph Static Analysis

- **Tree-Sitter Grammar Engine**: Parses syntax trees with complete resilience to syntax quirks, tracking lexical scopes, variable life-cycles, function signatures, and class hierarchies.
- **Deterministic Symbol UUIDs**: Generates stable, content-derived UUIDs for every statement, block, branch, and expression to enable precise blast radius queries.
- **Multi-Relational Dependency Graph**: Builds directed multigraphs discriminating between `IMPORT` (module loading), `CALL` (runtime invocation), and `REFERENCE` (symbol lookup).

### Stage 2: Architectural Reconstruction Engine

- **Structural Metric Computation**:
  - **In-Degree & Out-Degree**: Module coupling and fan-out.
  - **Betweenness Centrality**: Identifies critical bottlenecks that mediate communication across subsystems.
  - **PageRank Centrality**: Ranks core modules by systemic structural authority.
  - **Transitive Downstream Reach**: Measures blast radius and total reachable downstream code surface.
- **Automated Role Detection**:
  - **`ENTRY_CANDIDATE`**: Low incoming coupling, high downstream reach (CLI entry points, API controllers, scripts).
  - **`HUB`**: High total degree and PageRank centrality; core coordination nodes.
  - **`BRIDGE`**: High betweenness centrality; bridges distinct architectural subsystems.
  - **`LEAF`**: High incoming coupling, zero or minimal outgoing imports (utility modules, primitives, models).
  - **`CYCLE_MEMBER`**: Part of an architectural circular dependency loop ($SCC > 1$).
  - **`INTERMEDIARY`**: Balanced operational units in the standard data flow.
- **Boundary & Community Detection**: Applies Louvain modularity optimization weighted by call frequencies and directory structure heuristics to group related modules into high-confidence architectural components.
- **End-to-End Architectural Flows**: Traces execution sequences starting from discovered entry points, through intermediaries, down to terminal persistence and leaf modules.

### Stage 3: Multi-Tier Cognitive Onboarding Engine

- **Targeted Reading Roadmaps**: Automatically computes cognitive reading orders broken down by developer experience:
  - **Beginner**: High-level entry candidates and high-level architectural flows.
  - **Intermediate**: Hub modules, architectural bridges, and subsystem communication contracts.
  - **Advanced**: Circular dependency loops, high-centrality risk areas, and deep AST symbol bindings.

### Stage 4: Living Codebase Atlas (Interactive Web Visualizer)

- Standalone, zero-dependency HTML file embedding all metadata, styles, Monaco Editor, and vis.js canvas.
- Features a **monochrome, minimalist workstation UI** with high-contrast role-colored graphs and 3-pane code exploration.

---

## 4. Complete CLI Command Reference

### CLI Command Cheat-Sheet

To display the built-in reference table directly in your terminal at any time:

```bash
uv run karuvi --commands
```

| Command / Flag | Alias | Description | Example Usage |
|---|---|---|---|
| `karuvi <repo>` | — | Export the Atlas and auto-serve it over local HTTP in your browser | `uv run karuvi /path/to/repo` |
| `onboard` | `--onboard` | Generate progressive reading roadmap with complexity tiers | `uv run karuvi <repo> onboard --level beginner` |
| `explore` | `--explore` | Classic terminal dashboard with opt-in JSON/HTML exports | `uv run karuvi <repo> explore` |
| `--tree <file>` | `-t`, `--file-tree` | Print aesthetic ASCII intra-file AST & code flow tree | `uv run karuvi <repo> -t src/app.py` |
| `--deps <file>` | — | Print upstream imports & downstream dependents tree | `uv run karuvi <repo> --deps src/app.py` |
| `--chart <file>` | `--file-chart` | Print indentation-based control flow chart for a file | `uv run karuvi <repo> --chart src/app.py` |
| `--inspect <file>` | — | Inspect declared classes, methods, functions & symbols | `uv run karuvi <repo> --inspect src/app.py` |
| `--blast <uuid\|name>` | `--blast-radius` | Trace cross-module blast radius & call sites of a symbol | `uv run karuvi <repo> --blast verify_token` |
| `--cycles` | — | Detect & display all circular dependency loops in ASCII | `uv run karuvi <repo> --cycles` |
| `--graph` | `--ascii-graph` | Display ASCII connectivity matrix / dependency summary | `uv run karuvi <repo> --graph` |
| `--architecture` | `-a` | Reconstruct architecture components, roles & flows | `uv run karuvi <repo> -a` |
| `--arch-json <path>` | — | Export reconstructed architecture model to JSON | `uv run karuvi <repo> -a --arch-json arch.json` |
| `--arch-doc <path>` | — | Export deterministic Markdown architecture docs | `uv run karuvi <repo> -a --arch-doc ARCH.md` |
| `--interactive` | `-i` | Launch interactive terminal explorer & AST navigator | `uv run karuvi <repo> -i` |
| `--html <file.html>` | — | Generate Living Codebase Atlas interactive web visualizer | `uv run karuvi <repo> --html atlas.html` |
| `--json <file.json>` | — | Export complete repository analysis and AST dump | `uv run karuvi <repo> --json report.json` |
| `--mermaid` | — | Print Mermaid.js dependency diagram to stdout | `uv run karuvi <repo> --mermaid` |
| `--serve` | — | Launch FastAPI stateful daemon server on port 8000 | `uv run karuvi <repo> --serve` |

---

### Detailed Command Usage & Examples

#### 1. Repository Summary Scan
Performs tree-sitter AST crawling, resolves all relative and absolute imports, detects cycles, and renders Rich summary tables:
```bash
uv run karuvi ./my-project
```

#### 2. Architecture Reconstruction (`-a`, `--architecture`)
Runs community detection, classifies roles, identifies boundaries, and prints high-level flows:
```bash
uv run karuvi ./my-project -a
```
To export architecture models to JSON or deterministic Markdown:
```bash
uv run karuvi ./my-project -a --arch-json arch.json --arch-doc ARCHITECTURE.md
```

#### 3. Cognitive Onboarding Roadmap (`onboard`)
Generates tailored learning trajectories categorized by developer tier:
```bash
# Beginner tier (entry points, high-level flows)
uv run karuvi ./my-project onboard --level beginner

# Intermediate tier (subsystem hubs, bridges)
uv run karuvi ./my-project onboard --level intermediate

# Advanced tier (circular loops, high blast-radius symbols)
uv run karuvi ./my-project onboard --level advanced
```

#### 4. Instant Living Atlas Launch (`explore`)
Generates the self-contained HTML visualizer in the target directory and launches it directly in your web browser:
```bash
uv run karuvi ./my-project explore
```

#### 5. Intra-File AST Tree (`--tree`, `-t`)
Inspects the lexical scope tree, variable life-cycles, class definitions, and internal method blocks of a specific file:
```bash
uv run karuvi ./my-project -t src/server.py
```

#### 6. Upstream & Downstream Dependencies (`--deps`)
Prints an ASCII tree showing everything imported by a module (**Upstream**) and every other module that depends on it (**Downstream**):
```bash
uv run karuvi ./my-project --deps src/models/user.py
```

#### 7. Blast Radius Tracer (`--blast`)
Identifies all call sites across the entire repository that directly or transitively depend on a symbol or AST UUID:
```bash
# By symbol name
uv run karuvi ./my-project --blast authenticate_user

# By deterministic AST UUID
uv run karuvi ./my-project --blast 4a12f9b0-9e23-4819-bf92-823901a8ef10
```

#### 8. Circular Dependency Detection (`--cycles`)
Uses Tarjan's strongly connected components algorithm to detect and visualize circular import loops:
```bash
uv run karuvi ./my-project --cycles
```

#### 9. Export Options (`--html`, `--json`, `--mermaid`)
```bash
# Standalone Interactive HTML visualizer
uv run karuvi ./my-project --html visualizer.html

# Raw AST dump and graph connectivity JSON
uv run karuvi ./my-project --json graph_dump.json

# Mermaid.js diagram definition printed to stdout
uv run karuvi ./my-project --mermaid > dependency_diagram.mmd
```

#### 10. Interactive Terminal AST Navigator (`-i`)
Launches a responsive terminal console allowing interactive jumping across files, classes, methods, and call sites without leaving the shell:
```bash
uv run karuvi ./my-project -i
```

---

## 5. The Living Codebase Atlas Web Interface

The **Living Codebase Atlas** is a standalone, single-file HTML web application engineered with a clean, minimalist workstation aesthetic.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  KARUVI ATLAS  │  my-repo  │  [Q Search (Cmd+K)]                                      [Overview]    │
├──────────────┬───────────────────────────────────────────────────────────────────────────────────────┤
│  NAV SIDEBAR │  MAIN WORKSPACE                                                                       │
│              │                                                                                       │
│  Overview    │  [Tab 1: Overview Dashboard]                                                          │
│  Onboarding  │  System health, metrics, top entry points, architecture overview                      │
│  Arch        │                                                                                       │
│  Graph       │  [Tab 4: Graph Explorer]                                                              │
│  Code        │  Force-directed interactive network canvas                                            │
│              │  - Role-colored boxes (Cyan: Entry, Rose: Cycle, Purple: Hub, Amber: Bridge, etc.)     │
│              │  - Colored connecting lines matching node origins                                     │
│              │  - Role filter pills (All, Entry, Cycle, Hub, Bridge, Leaf)                           │
│              │  - Relationship checkboxes (Calls, Imports, References)                               │
│              │  - Smart greying out: unrelated nodes & wires dim automatically                        │
│              │                                                                                       │
│              │  [Tab 5: Sourcetrail-Grade Code Explorer]                                             │
│              │  ┌──────────────────────┬──────────────────────┬────────────────────────────────────┐ │
│              │  │ Column 1:            │ Column 2:            │ Column 3:                          │ │
│              │  │ Module Explorer      │ Intra-File AST Tree  │ Monaco Code Editor                 │ │
│              │  │ - Upstream Imports   │ - Collapsible Nodes  │ - Read-only syntax highlighting    │ │
│              │  │ - Downstream Deps    │ - Clickable Line #s  │ - Direct symbol reveal line jumps  │ │
│              │  │ - Colored Branches   │ - Role Branch Lines  │ - Zero flicker / Instant switching │ │
│              │  └──────────────────────┴──────────────────────┴────────────────────────────────────┘ │
└──────────────┴───────────────────────────────────────────────────────────────────────────────────────┘
```

### Tab 1: Overview Dashboard
- High-level metric summary: Total Modules, Discovered Architectural Components, Total Inter-Module Dependencies, Total Lines of Code, and Circular Loops.
- Top Entry Point banner with confidence scores and downstream reach evidence.
- Structural health indicators and quick navigation links.

### Tab 2: Onboarding Tour
- Step-by-step cognitive roadmaps tailored for **Beginner**, **Intermediate**, and **Advanced** engineers.
- Interactive step items with complexity ratings, rationale, and quick-inspection shortcuts.

### Tab 3: System Architecture
- Reconstructed architectural component cards displaying cohesion confidence percentages, member module counts, and discovery methods.
- High-level architectural flows illustrating subsystem-to-subsystem communication chains.

### Tab 4: Graph Explorer
An interactive vis.js canvas visualizing whole-repository module connectivity:
- **Role-Based Node Color Coding**:
  - **Entry Candidates (`ENTRY_CANDIDATE`)**: Vibrant Cyan (`#06b6d4` border, deep teal background)
  - **Circular Loops (`CYCLE_MEMBER`)**: Crimson Rose (`#f43f5e` border, dark burgundy background)
  - **Hub Modules (`HUB`)**: Purple / Violet (`#c084fc` border, deep purple background)
  - **Bridge Modules (`BRIDGE`)**: Amber / Warm Gold (`#f59e0b` border, dark amber background)
  - **Leaf Modules (`LEAF`)**: Emerald Green (`#10b981` border, dark emerald background)
  - **Standard Modules (`INTERMEDIARY`)**: Sky Blue (`#38bdf8` border, deep slate background)
- **Role-Colored Connecting Lines (Edges)**:
  - Connecting lines dynamically take on the color of their origin node.
  - Circular dependency loops are highlighted with thick, prominent Rose/Red lines (`#f43f5e`, `width: 2.5`).
- **Smart Greying Out & Filtering**:
  - Clicking any role pill (`Entry`, `Cycle`, `Hub`, `Bridge`, `Leaf`) or typing a regex in the node filter keeps matching nodes and their connecting wires active while **greying out non-matching nodes AND their connecting wires** down to `opacity: 0.06`.
  - Clicking any node isolates its immediate neighborhood while dimming all unrelated nodes and edges across the canvas.
- **Relationship Type Toggles**:
  - Live toggles for **Calls**, **Imports**, and **References** with matching color indicators.
- **Direct Code Explorer Integration**:
  - Clicking any node in the graph instantly transitions to Tab 5 (Code Explorer) with that module selected, its AST parsed, and its source code rendered in Monaco.

### Tab 5: Sourcetrail-Grade Code Explorer
A responsive 3-column code inspection layout:
1. **Column 1: Module Explorer (Dependency Hierarchy)**:
   - **Upstream Dependencies**: Modules imported by the current file, bordered with an amber branch indicator.
   - **Downstream Dependents**: Modules that import the current file, bordered with an emerald branch indicator.
   - One-click navigation to jump across connected files.
2. **Column 2: Intra-File AST Tree**:
   - Collapsible hierarchy of lexical scopes, classes, functions, variable declarations, and invocation calls.
   - Formatted badges: `[CLASS]` (purple), `[FUNCTION]` (blue), `[VAR]` (green), `[CALL]` (amber).
   - Right-angle tree connector lines colored to match the parent and child badge boundaries.
   - **Clickable Line Jumpers (`L42`)**: Clicking any line indicator instantly centers and reveals the exact line in the Monaco editor.
3. **Column 3: Monaco Code Editor**:
   - High-performance Monaco editor running syntax highlighting in dark mode.
   - Clean, read-only inspection with automatic layout adjustment.

### Global Search Modal (`Cmd+K` / `Ctrl+K`)
Press `Cmd+K` (macOS) or `Ctrl+K` (Linux/Windows) anywhere in the application to open the instantaneous global search overlay to filter by module name, component, architectural role, or symbol.

---

## 6. Karuvi Daemon & REST API Reference

### Starting the Daemon

Karuvi embeds a high-performance **FastAPI** daemon server:

```bash
uv run karuvi /path/to/target-repo --serve
```
*The daemon starts on `http://127.0.0.1:8000` by default.*

### API Endpoints

| Method | Endpoint | Description | Query / Body Params |
|---|---|---|---|
| `GET` | `/` | Serves the Living Codebase Atlas Single Page Application | — |
| `GET` | `/visualize` | Alias to `/` for Living Codebase Atlas Web UI | — |
| `GET` | `/architecture` | Complete reconstructed architecture model (`components`, `roles`, `flows`) as JSON | — |
| `POST` | `/init` | Initialize or switch target repository directory | `{"project_root": "/path/to/repo"}` |
| `GET` | `/status` | Server status and indexed module count | — |
| `GET` | `/graph` | Entire dependency graph (nodes, multigraph edges, cross-references) | — |
| `GET` | `/export` | Full AST and static analysis dump as JSON | — |
| `GET` | `/files` | List of all indexed files and module identifiers | — |
| `GET` | `/dependencies` | Query symbol references within a file across a line range | `?file=src/app.py&start=1&end=100` |
| `GET` | `/tree` | Retrieve AST code-flow tree for a specific file | `?file=src/app.py` |
| `GET` | `/scopes` | Return lexical scope hierarchy for a file | `?file=src/app.py` |
| `GET` | `/functions` | Return all function definitions and signatures in a file | `?file=src/app.py` |
| `GET` | `/classes` | Return all class and method definitions in a file | `?file=src/app.py` |
| `GET` | `/variables` | Search for variable declarations and usages across all modules | `?name=config` |

---

## 7. Programmatic Python SDK API

Karuvi can be imported as a library in your Python scripts, CI automation pipelines, or custom tooling:

```python
from pathlib import Path
from karuvi import get_tree
from karuvi.repo_graph import RepoGraphBuilder
from karuvi.pointers import GlobalIndex
from karuvi.architecture.analyzer import ArchitectureAnalyzer
from karuvi.architecture.visualizer import generate_atlas_html, build_unified_payload

repo_path = Path("/path/to/my-repo")

# 1. Initialize global symbol index and parse repository files
global_index = GlobalIndex()
global_index.add_search_path(repo_path)

parsed_modules = {}
for py_file in repo_path.glob("**/*.py"):
    rel_path = str(py_file.relative_to(repo_path))
    parsed_modules[rel_path] = get_tree.parse_file(str(py_file), global_index=global_index)

# 2. Build Stage 1 Dependency & Multi-Relational Graph
builder = RepoGraphBuilder(repo_path, parsed_modules, global_index=global_index)
builder.build()

print(f"Total modules indexed: {len(builder.graph.nodes)}")
print(f"Circular dependencies detected: {len(builder.cycles)}")

# 3. Run Stage 2 Architecture Reconstruction Analyzer
analyzer = ArchitectureAnalyzer(repo_path)
arch_model = analyzer.analyze(builder)

print(f"Discovered components: {[c.name for c in arch_model.components.values()]}")
print(f"Top entry point: {arch_model.entrypoints[0]['module']}")

# 4. Generate Living Codebase Atlas Standalone HTML
html_content = generate_atlas_html(builder, arch_model)
Path("my_atlas.html").write_text(html_content, encoding="utf-8")
print("✔ Living Codebase Atlas exported successfully!")
```

---

## 8. Architecture & Design Principles

```
karuvi/
├── __init__.py                       # Package metadata (import karuvi)
├── __main__.py                       # python -m karuvi entry point
├── architecture/                     # Stage 2: Architectural Reconstruction
│   ├── analyzer.py                   # Master orchestrator combining all stages
│   ├── boundaries.py                 # Architectural boundary enforcement & validation
│   ├── communities.py                # Louvain modularity & directory-affinity clustering
│   ├── component_graph.py            # Component-level dependency contraction
│   ├── components.py                 # Component naming & heuristic role synthesis
│   ├── documentation.py              # Deterministic Markdown architecture generation
│   ├── entrypoints.py                # Structural entry-point ranking (coupling vs reach)
│   ├── flows.py                      # Transitive cross-subsystem flow tracing
│   ├── metrics.py                    # Graph centrality & PageRank calculation
│   ├── models.py                     # Pydantic-style dataclasses & models
│   ├── module_graph.py               # Directed module multigraph builder
│   ├── onboarding.py                 # Multi-tier cognitive onboarding roadmap engine
│   ├── roles.py                      # Structural role classification algorithms
│   ├── serialization.py              # JSON encoder/decoder for models
│   └── visualizer.py                 # Living Codebase Atlas HTML & JS visualizer
├── cli.py                            # CLI command parser & Rich terminal interface
├── get_tree.py                       # Tree-sitter intra-file AST parser
├── pointers.py                       # Global symbol cross-referencing & indexing
├── repo_graph.py                     # Stage 1 Whole-repository multigraph builder
├── returns.py                        # AST deptree dictionary serializer
├── main.py                           # FastAPI daemon & HTTP REST service (karuvi-serve)
└── tests/                            # Comprehensive unit & integration test suite
```

### Core Design Rules
1. **Deterministic Execution**: Given the same codebase, Karuvi generates identical outputs, AST UUIDs, and architectural metrics every time.
2. **Defensive Parsing**: Tree-sitter guarantees that files with syntax errors or partial edits do not crash the crawl; healthy parts of the AST are extracted cleanly.
3. **Pure Python & Zero Node.js Requirement**: The Living Codebase Atlas compiles into a single HTML file with embedded scripts, meaning clients need zero node servers or npm installations to inspect their projects.

---

## 9. Troubleshooting & FAQ

### Q: Why does Karuvi report "No Python files found"?
Ensure you provide the root folder of the repository. If you are already inside the target directory, simply run:
```bash
uv run karuvi .
```

### Q: Are virtual environments and third-party dependencies ignored?
Yes. Karuvi automatically ignores folders matching:
`.venv`, `venv`, `env`, `__pycache__`, `.git`, `node_modules`, `.mypy_cache`, `.pytest_cache`, `dist`, `build`, and `.eggs`.

### Q: How can I run Karuvi in headless CI/CD pipelines?
Use non-interactive flags like `--cycles` or `--arch-json`:
```bash
# Check for circular dependency loops in CI
uv run karuvi /path/to/repo --cycles

# Export architectural model JSON
uv run karuvi /path/to/repo -a --arch-json arch.json
```
Both commands terminate with exit code `0` on completion without waiting for user prompts.

### Q: How do I share the Living Codebase Atlas with teammates?
Simply share the generated `karuvi_atlas.html` file (e.g. via Slack, email, GitHub Pages, or S3 bucket). It is 100% self-contained and opens instantly in Google Chrome, Mozilla Firefox, Safari, or Microsoft Edge without any web server.

---

## 10. License

Karuvi is open-source software licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
