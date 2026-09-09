# Karuvi User Guide

Welcome to the official Karuvi User Guide. Karuvi is a whole-repository Python dependency analyzer that maps out how the code in your project connects and interacts.

## 1. Installation

### Linux & macOS
The recommended way to install Karuvi natively is using [uv](https://github.com/astral-sh/uv):

```bash
uv tool install karuvi
```

Alternatively, Arch Linux users can install it from the AUR:
```bash
yay -S karuvi
```

### Windows
Karuvi provides a seamless Docker-backed launcher for Windows. You can install it easily using package managers:

**Prerequisite:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and ensure it is running.

**Using WinGet:**
```powershell
winget install not-that-deep-26.karuvi
```

**Using Scoop:**
```powershell
scoop install https://raw.githubusercontent.com/Not-That-Deep-26/karuvi/main/packaging/scoop/karuvi.json
```

## 2. Basic Usage

The simplest way to use Karuvi is to navigate to your project directory and run:

```bash
karuvi .
```

Or provide the path to your repository:
```bash
karuvi /path/to/your/python-project
```

**What happens?**
1. Karuvi scans the directory for all `.py` files.
2. It builds a dependency graph of imports and symbols.
3. It generates an interactive HTML report.
4. It starts a temporary web server (port 8000) and opens the report in your browser.

Press `Ctrl+C` in your terminal to stop the web server.

*(Note for Windows users: You can use standard Windows paths like `karuvi C:\Projects\api-backend`, the Docker wrapper handles everything automatically.)*

## 4. CLI Options

Karuvi comes with many powerful flags to explore your codebase. You can use these alongside the repository path:

| Option | Description | Example |
| :--- | :--- | :--- |
| `--repo`, `-r` | Explicitly define the repository path. | `karuvi --repo /path/to/repo` |
| `--onboard` | Generate a progressive reading roadmap for new contributors. | `karuvi . --onboard --level beginner` |
| `--explore` | Run the classic terminal analysis dashboard instead of opening the HTML atlas. | `karuvi . --explore` |
| `--export` | Export the analysis JSON and HTML Atlas to the repository root. | `karuvi . --export` |
| `--open` | Auto-serve the exported atlas over local HTTP. | `karuvi . --export --open` |
| `--tree <file>` | Print an aesthetic ASCII AST and symbol tree for a specific file. | `karuvi . --tree main.py` |
| `--deps <file>` | Print the upstream imports and downstream dependents for a file. | `karuvi . --deps utils.py` |
| `--chart <file>` | Print an indentation-based control flow chart for a file. | `karuvi . --chart app.py` |
| `--inspect <file>`| Inspect classes, methods, and functions declared in a file. | `karuvi . --inspect models.py` |
| `--blast <uuid/name>`| Trace the cross-module blast radius of a symbol. | `karuvi . --blast verify_token` |
| `--cycles` | Detect and display all circular dependency loops in the project. | `karuvi . --cycles` |
| `--graph` | Display an ASCII connectivity matrix summary. | `karuvi . --graph` |
| `--architecture`, `-a`| Reconstruct and display high-level architectural components. | `karuvi . -a` |
| `--interactive`, `-i`| Launch the interactive terminal explorer. | `karuvi . -i` |
| `--serve` | Launch the FastAPI stateful daemon server on port 8000. | `karuvi . --serve` |

## 5. Server/API Mode (`--serve`)

For advanced use cases or building integrations, you can run Karuvi as a persistent API server.

```bash
karuvi /path/to/repo --serve
```

**What it does:**
- Starts a FastAPI daemon on `http://127.0.0.1:8000`.
- Parses the repository into memory once.
- Exposes REST API endpoints to query dependencies, ASTs, and the graph structure without needing to re-parse the files.

**How to access it:**
- Open your browser to `http://127.0.0.1:8000` to view the Living Codebase Atlas.
- Access the interactive Swagger API documentation at `http://127.0.0.1:8000/docs`.

**How to stop it:**
- Press `Ctrl+C` in the terminal where it is running.

## 6. Understanding the Output

- **Terminal Dashboard (`--explore`)**: Provides a quick text-based overview of your project's health, including total lines of code, number of modules, circular dependencies, and a table of the most heavily connected modules.
- **Living Codebase Atlas (`.html`)**: A highly interactive web page that visualizes your architecture. You can click on nodes to see what they depend on and who depends on them.
- **Analysis JSON (`.json`)**: A raw, machine-readable dump of the Abstract Syntax Tree and dependency graph. Useful for CI/CD pipelines or custom tooling.

## 7. Windows-Specific Notes

Karuvi relies on the `tree-sitter-python` C-extension, which can sometimes fail to compile cleanly on certain Windows environments. 

To bypass this entirely, the Windows `karuvi.ps1` launcher uses Docker. When you run `karuvi C:\Projects\my-project`, the launcher transparently handles starting a lightweight Linux container, mapping your `C:\Projects\my-project` directory securely into the container as `/workspace`, and running the actual Python application inside.

As a normal user, **you do not need to manually write `docker run` commands**. Just use the `karuvi` command as documented.

## 8. Troubleshooting

**"Docker Desktop is not installed or not running" (Windows)**
- Ensure you have Docker Desktop installed and that the application is actively running in your system tray before running Karuvi.

**"Directory not found" or Path Issues**
- Ensure you are providing the correct path to the Python project.
- If a path has spaces, enclose it in quotes: `karuvi "C:\My Projects\Backend"`

**"Port already in use" (Error starting server)**
- If you use `karuvi .` (which opens the web server) or `karuvi . --serve`, Karuvi attempts to bind to port 8000.
- If another application is using port 8000, the server will fail.
- You can specify a different port using the `--port` flag: `karuvi . --port 8080`.

## 9. FAQ

**Q: Does Karuvi modify my code?**
A: No. Karuvi is strictly a static analysis tool. It reads your `.py` files to build its graph and does not modify your source code in any way.

**Q: Does Karuvi work with non-Python projects?**
A: Currently, Karuvi is specifically designed and optimized for Python codebases using the `tree-sitter-python` grammar.

**Q: Why isn't my virtual environment (`.venv`) being analyzed?**
A: By design, Karuvi ignores common cache and virtual environment directories (`.venv`, `venv`, `__pycache__`, `.git`, `node_modules`) so that the analysis focuses purely on *your* source code, rather than third-party libraries.
