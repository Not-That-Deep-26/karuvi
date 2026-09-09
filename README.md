# Karuvi

**Whole-Repository Python Dependency Analyzer, Symbol Tracer & Living Codebase Atlas**

## What is Karuvi?
Karuvi is a powerful CLI tool that analyzes an entire Python repository to build an in-memory graph of its modules, dependencies, and symbols. It provides developers with interactive insights into architecture, cross-module usage, circular dependencies, and the structural "blast radius" of changes.

## Why it exists
Navigating large, unfamiliar, or poorly documented Python codebases is challenging. While standard IDEs offer local code navigation, they often struggle to provide a high-level architectural view. Karuvi bridges this gap by offering a "Sourcetrail-grade" experience right in your terminal and browser, automatically reconstructing the architectural flows of any Python project.

## Key Features
- **Whole-Repo Analysis**: Parses all Python files in a directory to build a comprehensive dependency graph.
- **Blast Radius Tracing**: Determine the exact impact of changing a symbol or function across the entire codebase.
- **Living Codebase Atlas**: Generates a beautiful, interactive HTML visualizer to explore your repository's structure.
- **Circular Dependency Detection**: Instantly identifies and reports import loops.
- **Architecture Reconstruction**: Automatically groups modules into functional components and entry points.
- **Onboarding Engine**: Generates a progressive reading roadmap for new contributors.

## Architecture Overview
Karuvi utilizes `tree-sitter-python` to perform fast, robust AST parsing. It constructs a `GlobalIndex` to resolve imports and symbol usages across file boundaries, ultimately building a `RepoGraphBuilder` model. This model is then queried via the CLI or served over an embedded `FastAPI` daemon for interactive exploration.

## Quick Start

The quickest way to use Karuvi is to run it against a local repository:

```bash
karuvi /path/to/your/python-project
```

This will analyze the repository, generate an interactive HTML report (`karuvi_atlas.html`), and automatically open it in your browser.

## Installation

### Linux / macOS
The easiest and fastest way to install Karuvi natively is using [uv](https://github.com/astral-sh/uv):

```bash
uv tool install karuvi
```
*Alternatively, you can just run it temporarily without installing: `uvx karuvi /path/to/repo`*

### Windows
Karuvi is available via the Windows Package Manager (WinGet). To install the seamless Docker-backed launcher, run:

```powershell
winget install not-that-deep-26.karuvi
```
*Note: Make sure Docker Desktop is installed and running before using the CLI.*

### Docker (Platform Independent)
You can manually run the Karuvi Docker image against any mounted repository:

```bash
docker run -it --rm \
  -p 8000:8000 \
  -v /path/to/your/repo:/workspace:ro \
  ghcr.io/not-that-deep-26/karuvi:latest \
  /workspace [options]
```

## Basic Usage

The canonical interface is `karuvi <repository-path> [options]`.

```bash
# Analyze current directory, export reports, and serve in browser
karuvi .

# Run the interactive terminal dashboard
karuvi /path/to/repo --explore

# Trace the blast radius of a specific function
karuvi /path/to/repo --blast verify_token

# Detect circular imports
karuvi /path/to/repo --cycles

# Generate a progressive codebase onboarding guide
karuvi /path/to/repo --onboard --level beginner

# Launch the interactive terminal navigator
karuvi /path/to/repo --interactive
```

## How Repository Analysis Works
When you point Karuvi at a path, it recursively discovers all `.py` files, ignoring standard caches (like `.venv`, `__pycache__`, `.git`). It parses each file into an Abstract Syntax Tree (AST), indexing every class, function, and variable declaration. It then links all `import` statements and cross-references to build a complete topological map of the project.

## Output Examples
Karuvi generates several types of output:
- **Terminal Dashboards**: Rich, color-coded summaries and dependency tables.
- **Living Codebase Atlas**: An interactive `karuvi_atlas.html` file that visualizes your architecture in the browser.
- **JSON Analysis**: A raw `karuvi_analysis.json` file containing the complete AST dump and dependency graph for downstream processing.

## Development Setup

If you want to contribute to Karuvi or run it from source:

1. Clone the repository:
   ```bash
   git clone https://github.com/Not-That-Deep-26/karuvi.git
   cd karuvi
   ```
2. We use `uv` for dependency management:
   ```bash
   pip install uv
   uv sync
   ```
3. Run the CLI natively via `uv`:
   ```bash
   uv run karuvi /path/to/target/repo
   ```

### Configuration / Environment Variables
- `KARUVI_REPO`: If set, the CLI and `--serve` daemon will default to analyzing this path automatically.

## Roadmap
- [ ] Official PyPI / `pipx` publication.
- [ ] WinGet and Scoop submissions for Windows.
- [ ] Arch Linux AUR package.
- [ ] Native Windows execution without Docker.

## Contributing
Contributions are welcome! Please open an issue or submit a Pull Request.

## License
MIT License. See the `LICENSE` file for details.
