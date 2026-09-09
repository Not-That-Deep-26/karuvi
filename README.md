<div align="center">
  <h1>Karuvi ⚡</h1>
  <p><b>Whole-Repository Python Dependency Analyzer, Symbol Tracer & Living Codebase Atlas</b></p>
</div>

---

## 📖 What is Karuvi?
Karuvi is a powerful CLI tool that analyzes an entire Python repository to build an in-memory graph of its modules, dependencies, and symbols. It provides interactive insights into architecture, cross-module usage, circular dependencies, and the structural "blast radius" of changes.

> **Why it exists:** Navigating large, unfamiliar, or poorly documented Python codebases is challenging. Karuvi bridges this gap by offering a "Sourcetrail-grade" experience right in your terminal and browser.

## ✨ Key Features
* 🔍 **Whole-Repo Analysis**: Parses all Python files in a directory to build a comprehensive dependency graph.
* 💥 **Blast Radius Tracing**: Determine the exact impact of changing a symbol or function across the entire codebase.
* 🗺️ **Living Codebase Atlas**: Generates a beautiful, interactive HTML visualizer to explore your repository's structure.
* 🔄 **Circular Dependency Detection**: Instantly identifies and reports import loops.
* 🏗️ **Architecture Reconstruction**: Automatically groups modules into functional components and entry points.
* 🚀 **Onboarding Engine**: Generates a progressive reading roadmap for new contributors.

## 🚀 Installation

### 🐧 Linux & 🍏 macOS
The recommended way to install Karuvi natively is using [uv](https://github.com/astral-sh/uv):

```bash
uv tool install karuvi
```

### 🪟 Windows
Karuvi provides a seamless Docker-backed launcher for Windows. Install it using WinGet or Scoop:

> ⚠️ **Prerequisite**: Ensure [Docker Desktop](https://www.docker.com/products/docker-desktop/) is installed and running.

```powershell
# Using WinGet
winget install not-that-deep-26.karuvi

# Or using Scoop
scoop install https://raw.githubusercontent.com/Not-That-Deep-26/karuvi/main/packaging/scoop/karuvi.json
```

### 🐳 Docker (Any Platform)
Run Karuvi without installing it locally:

```bash
docker run -it --rm -p 8000:8000 -v $(pwd):/workspace:ro ghcr.io/not-that-deep-26/karuvi:latest /workspace
```

## 💻 Usage

Navigate to your Python project and run:

```bash
karuvi .
```

> **What happens?** Karuvi analyzes your codebase, generates an interactive HTML report, and opens it automatically in your browser.

### 🛠️ Common Commands

| Command | Description |
| :--- | :--- |
| `karuvi . --blast my_function` | Trace the impact (blast radius) of a specific function or class |
| `karuvi . --cycles` | Detect all circular imports in the project |
| `karuvi . --explore` | Explore the architecture directly in the terminal |
| `karuvi . --onboard --level beginner` | Generate an onboarding guide for new contributors |

## ⚙️ How It Works
Karuvi utilizes `tree-sitter-python` for fast, robust AST parsing. It constructs a `GlobalIndex` to resolve imports and symbol usages across file boundaries, ultimately building a `RepoGraphBuilder` model. When you point Karuvi at a path, it recursively discovers all `.py` files, ignoring standard caches (like `.venv`, `__pycache__`, `.git`).

## 🛣️ Roadmap
- [ ] Official PyPI / `pipx` publication.
- [x] WinGet and Scoop submissions for Windows.
- [ ] Arch Linux AUR package.
- [ ] Native Windows execution without Docker.

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a Pull Request.

## 📜 License
MIT License. See the `LICENSE` file for details.
