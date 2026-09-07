"""
Karuvi CLI — Whole-Repository Dependency Analyzer
=================================================

Analyzes an entire Python repository:
- Crawls and parses all modules into an in-memory graph.
- Traces symbol declarations, UUIDs, and cross-module usages.
- Displays rich terminal summaries, dependency tables, and cross-references.
- Exports comprehensive JSON reports and interactive HTML dependency graphs.

Usage:
    uv run python cli.py
    uv run python cli.py --repo /path/to/repo --json repo.json --html repo_graph.html
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

import get_tree
from pointers import GlobalIndex
from repo_graph import RepoGraphBuilder
from returns import Module, module_to_dict

console = Console()

ASCII_BANNER = """[bold cyan]
  ██╗  ██╗ █████╗ ██████╗ ██╗   ██╗██╗   ██╗██╗
  ██║ ██╔╝██╔══██╗██╔══██╗██║   ██║██║   ██║██║
  █████╔╝ ███████║██████╔╝██║   ██║██║   ██║██║
  ██╔═██╗ ██╔══██║██╔══██╗██║   ██║██║   ██║██║
  ██║  ██╗██║  ██║██║  ██║╚██████╔╝╚██████╔╝██║
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝
[/bold cyan][dim cyan]  ⚡ Sourcetrail-Grade Architecture, AST & Dependency Visualizer[/dim cyan]
"""

EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
}


def discover_python_files(root: Path) -> list[Path]:
    """Find all .py files in root, excluding virtual environments and caches."""
    py_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(Path(dirpath) / f)
    py_files.sort()
    return py_files


def analyze_repository(
    repo_path: Path, verbose: bool = False
) -> tuple[dict[str, Module], GlobalIndex, RepoGraphBuilder]:
    """Parse all Python files in the repository and build the graph."""
    repo_path = repo_path.resolve()
    py_files = discover_python_files(repo_path)

    if not py_files:
        console.print(f"[bold red]Error:[/bold red] No Python files found in {repo_path}")
        sys.exit(1)

    global_index = GlobalIndex()
    global_index.add_search_path(repo_path)

    parsed_modules: dict[str, Module] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Analyzing {len(py_files)} Python files...", total=len(py_files))

        for p in py_files:
            rel_key = str(p.relative_to(repo_path))
            try:
                mod = get_tree.parse_file(str(p), global_index=global_index, verbose=False)
                mod.file_path = str(p)
                parsed_modules[rel_key] = mod
            except Exception as exc:
                if verbose:
                    console.print(f"[yellow]Warning: failed to parse {rel_key}: {exc}[/yellow]")
            progress.advance(task)

    # Build repo graph
    graph_builder = RepoGraphBuilder(repo_path, parsed_modules, global_index=global_index)
    graph_builder.build()

    return parsed_modules, global_index, graph_builder


def display_commands_table():
    """Render a comprehensive cheat-sheet table of all Karuvi commands."""
    table = Table(
        title="🛠️  Karuvi CLI — Feature & Command Reference",
        header_style="bold cyan",
        border_style="dim cyan",
        show_lines=True,
    )
    table.add_column("Command / Flag", style="bold green", width=28)
    table.add_column("Description", style="white", width=42)
    table.add_column("Example Usage", style="cyan", width=42)

    commands = [
        ("karuvi <repo>", "Export the Atlas and auto-serve it over local HTTP in your browser", "uv run karuvi /path/to/repo"),
        ("onboard, --onboard", "Progressive reading roadmap with complexity tiers", "uv run karuvi <repo> onboard --level beginner"),
        ("explore, --explore", "Classic terminal dashboard with opt-in JSON/HTML exports", "uv run karuvi <repo> explore"),
        ("export", "Export analysis JSON + Atlas HTML to the repo root", "uv run karuvi <repo> export"),
        ("--open", "Auto-serve an exported atlas over local HTTP", "uv run karuvi <repo> export --open"),
        ("--tree, -t <file>", "Print aesthetic ASCII intra-file AST & code flow tree", "uv run karuvi <repo> -t src/app.py"),
        ("--deps <file>", "Print upstream imports & downstream dependents tree", "uv run karuvi <repo> --deps src/app.py"),
        ("--chart <file>", "Print indentation-based control flow chart for a file", "uv run karuvi <repo> --chart src/app.py"),
        ("--inspect <file>", "Inspect declared classes, methods, functions & symbols", "uv run karuvi <repo> --inspect src/app.py"),
        ("--blast <uuid|name>", "Trace cross-module blast radius & call sites of a symbol", "uv run karuvi <repo> --blast verify_token"),
        ("--cycles", "Detect & display all circular dependency loops in ASCII", "uv run karuvi <repo> --cycles"),
        ("--graph", "Display ASCII connectivity matrix / dependency summary", "uv run karuvi <repo> --graph"),
        ("--architecture, -a", "Reconstruct architecture components, roles & flows", "uv run karuvi <repo> -a"),
        ("--arch-json <path>", "Export reconstructed architecture model to JSON", "uv run karuvi <repo> -a --arch-json arch.json"),
        ("--arch-doc <path>", "Export deterministic Markdown architecture docs", "uv run karuvi <repo> -a --arch-doc ARCH.md"),
        ("--interactive, -i", "Launch interactive terminal explorer & AST navigator", "uv run karuvi <repo> -i"),
        ("--html <file.html>", "Generate Living Codebase Atlas interactive web visualizer", "uv run karuvi <repo> --html atlas.html"),
        ("--json <file.json>", "Export complete repository analysis and AST dump", "uv run karuvi <repo> --json report.json"),
        ("--mermaid", "Print Mermaid.js dependency diagram to stdout", "uv run karuvi <repo> --mermaid"),
        ("--serve", "Launch FastAPI stateful daemon server on port 8000", "uv run karuvi <repo> --serve"),
    ]
    for cmd, desc, ex in commands:
        table.add_row(cmd, desc, ex)

    console.print(table)


def render_ascii_intra_tree(mod: Module, file_name: str):
    """Render an aesthetic ASCII/Unicode intra-file AST and symbol hierarchy tree."""
    total_lines = mod.line_count if hasattr(mod, "line_count") else "N/A"
    root = Tree(
        f"[bold cyan]📦 {file_name}[/bold cyan] [dim]({len(mod.functions)} functions, {len(mod.classes)} classes, {len(mod.variables)} symbols)[/dim]"
    )

    if mod.classes:
        cls_branch = root.add("[bold magenta]🏷️ Classes[/bold magenta]")
        for c in mod.classes:
            uuid_str = f" [dim](uuid: {str(c.uuid)[:8]}...)[/dim]" if c.uuid else ""
            c_node = cls_branch.add(f"[magenta]Class {c.name}[/magenta]{uuid_str}")
            for fn in c.functions:
                c_node.add(f"[green]⚡ def {fn.name}{fn.signature}[/green]")

    if mod.functions:
        fn_branch = root.add("[bold green]⚡ Top-level Functions[/bold green]")
        for fn in mod.functions:
            uuid_str = f" [dim](uuid: {str(fn.uuid)[:8]}...)[/dim]" if fn.uuid else ""
            fn_branch.add(f"[green]def {fn.name}{fn.signature}[/green]{uuid_str}")

    if mod.code_flow:
        flow_branch = root.add("[bold yellow]🌳 AST Code Flow & Scopes[/bold yellow]")

        def walk_flow(node, parent_tree):
            for child in node.children:
                lbl = Text()
                name = child.name or (child.variable.name if child.variable else "Node")
                if child.name:
                    if child.name.startswith("def "):
                        lbl.append("⚡ ", style="green")
                        lbl.append(child.name, style="bold green")
                    elif child.name.startswith("class "):
                        lbl.append("🏷️  ", style="magenta")
                        lbl.append(child.name, style="bold magenta")
                    else:
                        lbl.append("• ", style="dim")
                        lbl.append(child.name, style="white")
                elif child.variable:
                    if child.variable.is_reference:
                        lbl.append("↪️  ", style="yellow")
                        lbl.append(child.variable.name, style="bold yellow")
                        if child.variable.decl_reference:
                            lbl.append(f" (ref -> L{child.variable.decl_reference[1]})", style="dim")
                    else:
                        lbl.append("🔹 ", style="cyan")
                        lbl.append(child.variable.name, style="bold cyan")
                        if child.variable.uuid:
                            lbl.append(f" [id={str(child.variable.uuid)[:8]}...]", style="dim")
                else:
                    lbl.append("• Node", style="dim")

                branch = parent_tree.add(lbl)
                walk_flow(child, branch)

        walk_flow(mod.code_flow, flow_branch)

    console.print(Panel(root, title=f"[bold]Intra-File Tree — {file_name}[/bold]", border_style="cyan"))


def render_ascii_deps(builder: RepoGraphBuilder, file_key: str):
    """Render an aesthetic ASCII tree of upstream and downstream dependencies for a file."""
    if file_key not in builder.nodes:
        console.print(f"[bold red]Error:[/bold red] Module [yellow]{file_key}[/yellow] not found in parsed modules.")
        return

    node = builder.nodes[file_key]
    deps = builder.get_dependencies(file_key)
    dependents = builder.get_dependents(file_key)

    tree = Tree(f"[bold cyan]📦 {file_key}[/bold cyan] [dim]({node.line_count} LOC, in={node.in_degree}, out={node.out_degree})[/dim]")

    # Upstream
    up_branch = tree.add(f"[bold yellow]⬆ Upstream Dependencies (Imports: {len(deps['internal']) + len(deps['external'])})[/bold yellow]")
    if deps["internal"]:
        for d in deps["internal"]:
            up_branch.add(f"[cyan]→ {d}[/cyan]")
    if deps["external"]:
        for ext in deps["external"]:
            up_branch.add(f"[dim yellow]→ {ext} (external package)[/dim yellow]")
    if not deps["internal"] and not deps["external"]:
        up_branch.add("[dim]None (no imports)[/dim]")

    # Downstream
    down_branch = tree.add(f"[bold green]⬇ Downstream Dependents (Imported by: {len(dependents)})[/bold green]")
    if dependents:
        for dep in dependents:
            down_branch.add(f"[cyan]← {dep}[/cyan]")
    else:
        down_branch.add("[dim]None (not imported by internal modules)[/dim]")

    # Cross-module usages
    xrefs_used = [x for x in builder.cross_references if x["source_file"] == file_key]
    xrefs_provided = [x for x in builder.cross_references if x["target_file"] == file_key]
    if xrefs_used or xrefs_provided:
        xref_branch = tree.add(f"[bold magenta]🔀 Cross-Module Symbol Usages (Used: {len(xrefs_used)}, Provided: {len(xrefs_provided)})[/bold magenta]")
        for x in xrefs_used[:6]:
            xref_branch.add(f"[dim yellow]Uses '{x['symbol']}' from {x['target_file']}:L{x['decl_line']}[/dim yellow]")
        for x in xrefs_provided[:6]:
            xref_branch.add(f"[dim green]'{x['symbol']}' used in {x['source_file']}:L{x['use_line']}[/dim green]")

    console.print(Panel(tree, title=f"[bold]Dependency Topology — {file_key}[/bold]", border_style="yellow"))


def render_ascii_cycles(builder: RepoGraphBuilder):
    """Detect and render ASCII diagrams of all circular dependency loops."""
    cycles = builder.cycles
    if not cycles:
        console.print(Panel("[bold green]✔ No circular dependencies detected in repository modules![/bold green]", border_style="green"))
        return

    console.print(f"\n[bold red]⚠️  Detected {len(cycles)} Circular Dependency Loop(s):[/bold red]\n")
    for i, c in enumerate(cycles, 1):
        chain_len = len(c) - 1
        console.print(f"[bold yellow]Loop #{i} ({chain_len} modules):[/bold yellow]")
        for step_idx, step in enumerate(c[:-1]):
            if step_idx == 0:
                console.print(f"  ┌──► [bold cyan]{step}[/bold cyan]")
                console.print("  │        │ [dim]imports[/dim]")
                console.print("  │        ▼")
            elif step_idx == len(c) - 2:
                console.print(f"  │    [bold cyan]{step}[/bold cyan]")
                console.print(f"  │        │ [dim]imports {c[0]}[/dim]")
                console.print("  └────────┘")
            else:
                console.print(f"  │    [bold cyan]{step}[/bold cyan]")
                console.print("  │        │ [dim]imports[/dim]")
                console.print("  │        ▼")
        console.print()


def render_ascii_blast(builder: RepoGraphBuilder, parsed_modules: dict[str, Module], query: str):
    """Trace and render the ASCII blast radius of a symbol or UUID."""
    usages = []
    decl_info = None

    for xref in builder.cross_references:
        if str(xref["uuid"]) == query or xref["symbol"] == query:
            usages.append(xref)
            if not decl_info:
                decl_info = (xref["target_file"], xref["decl_line"], xref["symbol"], xref["uuid"])

    if not usages:
        for rel_key, mod in parsed_modules.items():
            for fn in mod.functions:
                if fn.name == query or str(fn.uuid) == query:
                    decl_info = (rel_key, "decl", fn.name, fn.uuid)
                    break
            for cls in mod.classes:
                if cls.name == query or str(cls.uuid) == query:
                    decl_info = (rel_key, "decl", cls.name, cls.uuid)
                    break
            if decl_info:
                break

    if not decl_info and not usages:
        console.print(f"[yellow]No declarations or cross-module usages found for:[/yellow] [bold]{query}[/bold]")
        return

    target_file, decl_line, sym_name, sym_uuid = decl_info if decl_info else ("unknown", "?", query, "")
    tree = Tree(f"[bold red]💥 Blast Radius for '{sym_name}'[/bold red] [dim](uuid: {str(sym_uuid)[:16]}...)[/dim]")
    tree.add(f"[bold cyan]📍 Declared at:[/bold cyan] {target_file}:{decl_line}")

    impacted_files = set(u["source_file"] for u in usages)
    impact_branch = tree.add(
        f"[bold yellow]🎯 Impacted Call Sites ({len(usages)} usages across {len(impacted_files)} file(s)):[/bold yellow]"
    )
    if usages:
        for u in usages:
            impact_branch.add(
                f"[red]💥 {u['source_file']}:{u['use_line']}:{u['use_col']}[/red] [dim](scope: {u['scope']})[/dim]"
            )
    else:
        impact_branch.add("[green]✔ No cross-module usages found in index. Isolated to declaring file.[/green]")

    console.print(Panel(tree, title="[bold red]Blast Radius Report[/bold red]", border_style="red"))


def render_ascii_graph(builder: RepoGraphBuilder):
    """Render an ASCII dependency connectivity matrix / summary."""
    table = Table(title="ASCII Module Dependency Topology", show_header=True, header_style="bold cyan")
    table.add_column("Source Module", style="cyan")
    table.add_column("Imports Internal", style="yellow")
    table.add_column("External Packages", style="dim yellow")
    table.add_column("In / Out", justify="center", style="green")

    for n in sorted(builder.nodes.values(), key=lambda x: x.out_degree, reverse=True):
        if not n.is_internal:
            continue
        deps = builder.get_dependencies(n.id)
        internal_str = ", ".join(Path(d).stem for d in deps["internal"][:4])
        if len(deps["internal"]) > 4:
            internal_str += f" (+{len(deps['internal']) - 4})"
        ext_str = ", ".join(deps["external"][:3])
        if len(deps["external"]) > 3:
            ext_str += f" (+{len(deps['external']) - 3})"

        table.add_row(
            n.id,
            internal_str or "[dim]-[/dim]",
            ext_str or "[dim]-[/dim]",
            f"in:{n.in_degree} | out:{n.out_degree}",
        )

    console.print(table)


def render_architecture_dashboard(model: Any):
    """Render a comprehensive Rich terminal dashboard for reconstructed architecture."""
    # Overview Panel
    stats_table = Table.grid(padding=(0, 2))
    stats_table.add_column(style="bold cyan")
    stats_table.add_column(style="white")
    stats_table.add_row("Analyzed Repository:", f"[bold white]{model.repository_root}[/bold white]")
    stats_table.add_row("Modules:", f"[green]{len(model.modules)}[/green]")
    stats_table.add_row("Architectural Components:", f"[magenta]{len(model.components)}[/magenta]")
    stats_table.add_row("Structural Entry Points:", f"[yellow]{len(model.entry_points)}[/yellow]")
    stats_table.add_row("Key Architectural Flows:", f"[cyan]{len(model.flows)}[/cyan]")
    console.print(Panel(stats_table, title="[bold cyan]🏛️  Karuvi Architecture Reconstruction Engine[/bold cyan]", border_style="cyan"))

    # Components Table
    comp_table = Table(
        title="📦 Reconstructed Architectural Components",
        border_style="dim magenta",
        header_style="bold magenta",
        show_lines=True,
    )
    comp_table.add_column("Component", style="bold white", width=22)
    comp_table.add_column("Confidence", justify="right", width=12)
    comp_table.add_column("Modules", justify="center", width=9)
    comp_table.add_column("Discovery Evidence", style="dim", width=26)
    comp_table.add_column("Member Modules", style="cyan", width=36)
    for comp in model.components.values():
        conf_color = "green" if comp.confidence >= 0.7 else ("yellow" if comp.confidence >= 0.4 else "red")
        mods_str = ", ".join(Path(m).name for m in comp.modules[:3])
        if len(comp.modules) > 3:
            mods_str += f" (+{len(comp.modules) - 3} more)"
        comp_table.add_row(
            comp.name,
            f"[{conf_color}]{comp.confidence:.1%}[/{conf_color}]",
            str(len(comp.modules)),
            ", ".join(comp.discovery_methods),
            mods_str,
        )
    console.print(comp_table)

    # Entry Points Table
    if model.entry_points:
        ep_table = Table(
            title="🚪 Structural Entry Points",
            border_style="dim green",
            header_style="bold green",
            show_lines=True,
        )
        ep_table.add_column("Rank", style="dim", width=6)
        ep_table.add_column("Module Path", style="bold green", width=34)
        ep_table.add_column("Score", justify="right", width=8)
        ep_table.add_column("Downstream Reach", style="white", width=22)
        ep_table.add_column("Reachable Components", style="cyan", width=22)
        for i, ep in enumerate(model.entry_points[:5], 1):
            ev = ep["evidence"]
            ep_table.add_row(
                f"#{i}",
                ep["module"],
                f"{ep['entry_score']:.2f}",
                f"{ev['reachable_modules']} modules",
                f"{ev['reachable_components']} components",
            )
        console.print(ep_table)

    # Flows Table
    if model.flows:
        flow_table = Table(
            title="🌊 Representative High-Level Flows",
            border_style="dim cyan",
            header_style="bold cyan",
            show_lines=True,
        )
        flow_table.add_column("Source Component", style="bold green", width=22)
        flow_table.add_column("Flow Path", style="bold white", width=42)
        flow_table.add_column("Target Component", style="bold magenta", width=22)
        for flow in model.flows:
            path_display = " ➔ ".join(flow.path)
            flow_table.add_row(flow.source, path_display, flow.target)
        console.print(flow_table)



def interactive_menu(
    repo_path: Path,
    parsed_modules: dict[str, Module],
    global_index: GlobalIndex,
    builder: RepoGraphBuilder,
):
    """Run an interactive terminal navigator session."""
    console.print("\n[bold cyan]Entering Karuvi Interactive Terminal Navigator...[/bold cyan]")
    console.print("[dim]Type the number or command to explore. Press Ctrl+C or 'q' to exit.[/dim]\n")

    files_list = sorted(parsed_modules.keys())

    while True:
        console.print(
            Panel(
                "[bold cyan][1][/bold cyan] 🌳 View Intra-File Tree       "
                "[bold cyan][2][/bold cyan] ⚡ Inspect File Symbols\n"
                "[bold cyan][3][/bold cyan] 🔗 View Dependencies (In/Out) "
                "[bold cyan][4][/bold cyan] 💥 Trace Blast Radius\n"
                "[bold cyan][5][/bold cyan] ⚠️  Detect Circular Imports   "
                "[bold cyan][6][/bold cyan] 📊 Full Repository Dashboard\n"
                "[bold cyan][7][/bold cyan] 🌐 Export Living Atlas HTML    "
                "[bold cyan][8][/bold cyan] 💾 Export JSON Report\n"
                "[bold cyan][9][/bold cyan] 🎓 Onboarding Reading Order    "
                "[bold cyan][?] [/bold cyan] 🛠️  Show Commands Reference    "
                "[bold red][q][/bold red] Exit",
                title="[bold]Karuvi Interactive Menu[/bold]",
                border_style="cyan",
            )
        )
        try:
            choice = input("Select an action [1-10, ?, q]: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exiting interactive mode.[/yellow]")
            break

        if choice.lower() in ("q", "quit", "exit"):
            break
        elif choice == "?":
            display_commands_table()
        elif choice == "1":
            search = input("Enter file path or keyword: ").strip()
            matches = [f for f in files_list if search.lower() in f.lower()]
            if not matches:
                console.print(f"[red]No files matched '{search}'[/red]")
            elif len(matches) == 1:
                render_ascii_intra_tree(parsed_modules[matches[0]], matches[0])
            else:
                for idx, m in enumerate(matches[:15], 1):
                    console.print(f"  [{idx}] {m}")
                try:
                    pick = int(input("Select file number: ").strip()) - 1
                    if 0 <= pick < len(matches):
                        render_ascii_intra_tree(parsed_modules[matches[pick]], matches[pick])
                except Exception:
                    pass
        elif choice == "2":
            search = input("Enter file path or keyword: ").strip()
            matches = [f for f in files_list if search.lower() in f.lower()]
            if matches:
                f_key = matches[0]
                mod = parsed_modules[f_key]
                console.print(f"\n[bold cyan]Symbol Inspector for {f_key}:[/bold cyan]")
                for fn in mod.functions:
                    console.print(f"[green]Function:[/green] {fn.name}{fn.signature} (uuid: {fn.uuid})")
                for cls in mod.classes:
                    console.print(f"[magenta]Class:[/magenta] {cls.name} (uuid: {cls.uuid})")
                    for fn in cls.functions:
                        console.print(f"  [green]Method:[/green] {fn.name}{fn.signature} (uuid: {fn.uuid})")
        elif choice == "3":
            search = input("Enter file path or keyword: ").strip()
            matches = [f for f in files_list if search.lower() in f.lower()]
            if matches:
                render_ascii_deps(builder, matches[0])
        elif choice == "4":
            sym = input("Enter symbol name or UUID: ").strip()
            if sym:
                render_ascii_blast(builder, parsed_modules, sym)
        elif choice == "5":
            render_ascii_cycles(builder)
        elif choice == "6":
            display_dashboard(repo_path, parsed_modules, builder)
        elif choice == "7":
            html_out = repo_path / "karuvi_atlas.html"
            export_html_graph(builder, html_out)
        elif choice == "8":
            json_out = repo_path / "karuvi_analysis.json"
            export_full_json(repo_path, parsed_modules, builder, json_out)
        elif choice == "9":
            from architecture.analyzer import ArchitectureAnalyzer
            from architecture.onboarding import CodebaseOnboardingEngine
            arch_model = ArchitectureAnalyzer(repo_path).analyze(builder)
            plan = CodebaseOnboardingEngine(arch_model, builder).build_plan()
            render_onboarding_course(plan, level="beginner")
        console.print()


def display_dashboard(
    repo_path: Path,
    parsed_modules: dict[str, Module],
    builder: RepoGraphBuilder,
):
    """Display a Rich terminal dashboard of the repo analysis."""
    graph_data = builder.to_dict()
    stats = graph_data["stats"]

    total_loc = sum(n.line_count for n in builder.nodes.values() if n.is_internal)
    total_funcs = sum(len(m.functions) for m in parsed_modules.values())
    total_classes = sum(len(m.classes) for m in parsed_modules.values())
    total_vars = sum(len(m.variables) for m in parsed_modules.values())
    cycle_count = len(builder.cycles)

    # Summary Panel
    cycle_text = f"[bold red]{cycle_count} LOOPS DETECTED[/bold red]" if cycle_count > 0 else "[bold green]0 (None)[/bold green]"
    summary_text = (
        f"[bold cyan]Repository:[/bold cyan] {repo_path}\n"
        f"[bold green]Modules Parsed:[/bold green] {len(parsed_modules)}    "
        f"[bold green]Total LOC:[/bold green] {total_loc:,}\n"
        f"[bold blue]Classes:[/bold blue] {total_classes}    "
        f"[bold blue]Functions:[/bold blue] {total_funcs}    "
        f"[bold blue]Symbols Indexed:[/bold blue] {total_vars}\n"
        f"[bold magenta]Cross-File Connections:[/bold magenta] {stats['total_edges']}    "
        f"[bold magenta]Cross-Module Symbol Usages:[/bold magenta] {stats['total_cross_references']}\n"
        f"[bold yellow]External Packages:[/bold yellow] {stats['total_external_packages']}    "
        f"[bold red]Circular Dependencies:[/bold red] {cycle_text}"
    )
    console.print(
        Panel(summary_text, title="[bold]Karuvi — Whole Repository Analysis[/bold]", border_style="cyan")
    )

    # 1. Modules Table
    mod_table = Table(title="Internal Modules & Connectivity", show_header=True, header_style="bold cyan")
    mod_table.add_column("Module File", style="white")
    mod_table.add_column("LOC", justify="right", style="dim")
    mod_table.add_column("Functions", justify="right", style="blue")
    mod_table.add_column("Classes", justify="right", style="magenta")
    mod_table.add_column("Imports (Out)", justify="right", style="yellow")
    mod_table.add_column("Used By (In)", justify="right", style="green")

    for n in sorted(builder.nodes.values(), key=lambda x: x.in_degree, reverse=True):
        if not n.is_internal:
            continue
        mod_table.add_row(
            n.path,
            str(n.line_count),
            str(n.function_count),
            str(n.class_count),
            str(n.out_degree),
            str(n.in_degree),
        )

    console.print(mod_table)

    # 2. Cross-Module Symbol References Table (if any)
    if builder.cross_references:
        xref_table = Table(
            title=f"Cross-Module Symbol References ({len(builder.cross_references)} total)",
            show_header=True,
            header_style="bold magenta",
        )
        xref_table.add_column("Symbol", style="green")
        xref_table.add_column("Used In (File : Line)", style="yellow")
        xref_table.add_column("Scope", style="dim")
        xref_table.add_column("Declared In (File : Line)", style="cyan")
        xref_table.add_column("UUID", style="dim", overflow="fold")

        for xref in builder.cross_references[:15]:
            used_at = f"{xref['source_file']}:{xref['use_line']}:{xref['use_col']}"
            decl_at = f"{xref['target_file']}:{xref['decl_line']}:{xref['decl_col']}"
            xref_table.add_row(
                xref["symbol"],
                used_at,
                xref["scope"],
                decl_at,
                str(xref["uuid"])[:16] + "..." if xref["uuid"] else "",
            )

        console.print(xref_table)
        if len(builder.cross_references) > 15:
            console.print(
                f"[dim]... and {len(builder.cross_references) - 15} more cross-module usages (export to JSON to inspect all).[/dim]\n"
            )

    # 3. External Dependencies
    if builder.external_packages:
        ext_list = ", ".join(f"[bold yellow]{pkg}[/bold yellow]" for pkg in sorted(builder.external_packages))
        console.print(Panel(ext_list, title="External / Third-Party Dependencies", border_style="yellow"))

    # 4. Command Reference Table
    display_commands_table()


def export_full_json(
    repo_path: Path,
    parsed_modules: dict[str, Module],
    builder: RepoGraphBuilder,
    output_path: Path,
):
    """Export complete whole-repository analysis and AST trees to JSON."""
    graph_data = builder.to_dict()

    modules_dump = {
        rel_key: module_to_dict(mod)
        for rel_key, mod in parsed_modules.items()
    }

    payload = {
        "repository": str(repo_path),
        "graph": graph_data,
        "modules": modules_dump,
    }

    output_path.write_text(json.dumps(payload, indent=2))
    console.print(f"[bold green]✔ Saved full repository JSON to:[/bold green] [cyan]{output_path}[/cyan]")


def export_html_graph(builder: RepoGraphBuilder, output_path: Path, arch_model: Any = None):
    """Export standalone interactive Living Codebase Atlas HTML visualizer."""
    from architecture.visualizer import generate_atlas_html
    html_content = generate_atlas_html(builder, arch_model)
    output_path.write_text(html_content, encoding="utf-8")
    console.print(f"[bold green]✔ Saved Living Codebase Atlas interactive HTML visualizer to:[/bold green] [cyan]{output_path}[/cyan]")


def export_outputs(
    repo_path: Path,
    parsed_modules: dict[str, Module],
    builder: RepoGraphBuilder,
    arch_model: Any = None,
    json_path: Path | None = None,
    html_path: Path | None = None,
) -> dict[str, Path]:
    """Consolidated export for the repository-wide JSON report and HTML atlas."""
    if html_path is not None and arch_model is None:
        from architecture.analyzer import ArchitectureAnalyzer

        arch_model = ArchitectureAnalyzer(repo_path).analyze(builder)

    written: dict[str, Path] = {}
    if json_path is not None:
        export_full_json(repo_path, parsed_modules, builder, json_path)
        written["json"] = json_path
    if html_path is not None:
        export_html_graph(builder, html_path, arch_model=arch_model)
        written["html"] = html_path
    return written


def _atlas_server(atlas_path: Path, port: int = 8000):
    """Build a static HTTP server rooted at the atlas file's directory."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    handler = partial(SimpleHTTPRequestHandler, directory=str(atlas_path.parent))
    try:
        return ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError:
        return ThreadingHTTPServer(("127.0.0.1", 0), handler)


def serve_and_open(atlas_path: Path, port: int = 8000):
    """Serve the exported atlas HTML over local HTTP and open it in the browser."""
    server = _atlas_server(atlas_path, port)
    url = f"http://127.0.0.1:{server.server_address[1]}/{atlas_path.name}"
    console.print(f"[bold green]✔ Serving Living Codebase Atlas at:[/bold green] [cyan]{url}[/cyan]")
    console.print("[dim]Press Ctrl+C to stop the server.[/dim]")
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")
    return server


def render_onboarding_course(plan: Any, level: str = "beginner"):
    """Renders the step-by-step onboarding plan in rich terminal output."""
    console.print(
        Panel(
            f"[bold]Estimated Read Time:[/bold] [yellow]{plan.estimated_read_time_minutes} minutes[/yellow]  •  "
            f"[bold]Total Steps:[/bold] [cyan]{plan.total_steps}[/cyan]  •  "
            f"[bold]Complexity Level:[/bold] [magenta]{level.capitalize()}[/magenta]",
            title="[bold cyan]🎓 Karuvi Progressive Codebase Onboarding Course[/bold cyan]",
            border_style="cyan",
        )
    )

    for step in plan.steps:
        summary = step.beginner_summary
        if level == "intermediate":
            summary = step.intermediate_summary
        elif level == "advanced":
            summary = step.advanced_summary

        step_table = Table.grid(padding=(0, 2))
        step_table.add_column(style="bold cyan", width=18)
        step_table.add_column(style="white")

        step_table.add_row("Summary:", summary)
        step_table.add_row("Why Now:", f"[dim]{step.why_now}[/dim]")
        step_table.add_row("Target Modules:", ", ".join(f"[cyan]{m}[/cyan]" for m in step.target_modules))

        if step.prerequisites_covered:
            step_table.add_row("Prerequisites:", ", ".join(f"[green]✓ {p}[/green]" for p in step.prerequisites_covered[:5]))

        if step.next_unlocks:
            step_table.add_row("Next Unlocks:", ", ".join(f"[blue]➔ {u}[/blue]" for u in step.next_unlocks[:5]))

        if step.key_symbols:
            sym_strs = [f"{s['name']} ({s['type']})" for s in step.key_symbols[:6]]
            step_table.add_row("Key Symbols:", ", ".join(f"[yellow]{s}[/yellow]" for s in sym_strs))

        cycle_prefix = "[bold red]🔄 (Circular Loop) [/bold red]" if step.is_cycle_group else ""
        panel_title = f"{cycle_prefix}Step {step.step_number}/{plan.total_steps}: {step.title}"
        border_style = "red" if step.is_cycle_group else "blue"

        console.print(Panel(step_table, title=panel_title, border_style=border_style))
        console.print()


def main():
    console.print(ASCII_BANNER)

    # Subcommand syntactic sugar handling:
    # karuvi onboard [repo] [--level beginner]
    # karuvi explain [repo] [target]
    # karuvi explore [repo]
    # karuvi analyze [repo]
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "onboard":
            sys.argv[1] = "--onboard"
            if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
                repo_val = sys.argv.pop(2)
                sys.argv.extend(["--repo", repo_val])
        elif cmd == "explore":
            sys.argv[1] = "--explore"
            if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
                repo_val = sys.argv.pop(2)
                sys.argv.extend(["--repo", repo_val])
        elif cmd == "explain":
            if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
                repo_val = sys.argv.pop(2)
                sys.argv.extend(["--repo", repo_val])
                pass
        elif cmd == "analyze":
            sys.argv.pop(1)
        elif cmd == "export":
            sys.argv[1] = "--export"
            if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
                repo_val = sys.argv.pop(2)
                sys.argv.extend(["--repo", repo_val])

    parser = argparse.ArgumentParser(
        description="Karuvi — Whole-Repository Dependency Analyzer & Symbol Tracer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Path to repository root (prompts interactively if omitted)",
    )
    parser.add_argument(
        "--repo",
        "-r",
        dest="repo_flag",
        type=str,
        default=None,
        help="Path to repository root",
    )
    parser.add_argument(
        "--onboard",
        action="store_true",
        help="Generate a beginner-friendly progressive onboarding course for the repository",
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=["beginner", "intermediate", "advanced"],
        default="beginner",
        help="Complexity level for onboarding and explanations (default: beginner)",
    )
    parser.add_argument(
        "--explore",
        action="store_true",
        help="Run the classic terminal analysis dashboard with opt-in JSON/HTML exports",
    )
    parser.add_argument(
        "--json",
        "-j",
        type=str,
        default=None,
        help="File path to save full repository JSON analysis",
    )
    parser.add_argument(
        "--html",
        type=str,
        default=None,
        help="File path to save interactive Living Codebase Atlas HTML visualizer",
    )
    parser.add_argument(
        "--tree",
        "-t",
        "--file-tree",
        dest="tree",
        type=str,
        default=None,
        help="Print aesthetic ASCII intra-file AST & symbol hierarchy tree for a file",
    )
    parser.add_argument(
        "--deps",
        type=str,
        default=None,
        help="Print upstream imports & downstream dependents tree for a file",
    )
    parser.add_argument(
        "--chart",
        "--file-chart",
        dest="chart",
        type=str,
        default=None,
        help="Print indentation-based control flow chart for a file",
    )
    parser.add_argument(
        "--inspect",
        type=str,
        default=None,
        help="Inspect classes, methods, functions & symbols for a specific file",
    )
    parser.add_argument(
        "--blast",
        "--blast-radius",
        dest="blast",
        type=str,
        default=None,
        help="Trace cross-module blast radius of a symbol or UUID",
    )
    parser.add_argument(
        "--cycles",
        action="store_true",
        help="Detect and display circular dependency loops in ASCII",
    )
    parser.add_argument(
        "--graph",
        "--ascii-graph",
        dest="graph",
        action="store_true",
        help="Display ASCII connectivity matrix / dependency summary",
    )
    parser.add_argument(
        "--architecture",
        "-a",
        action="store_true",
        help="Reconstruct and display high-level architectural components and flows",
    )
    parser.add_argument(
        "--arch-json",
        type=str,
        default=None,
        help="Path to export reconstructed architecture model JSON",
    )
    parser.add_argument(
        "--arch-doc",
        type=str,
        default=None,
        help="Path to export deterministic architecture Markdown documentation",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Launch interactive terminal explorer & AST navigator",
    )
    parser.add_argument(
        "--commands",
        action="store_true",
        help="Display cheat-sheet table of all Karuvi commands",
    )
    parser.add_argument(
        "--mermaid",
        action="store_true",
        help="Print Mermaid dependency diagram to stdout",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the Karuvi daemon on the analyzed repository",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export repository analysis JSON + Living Codebase Atlas HTML to the repository root",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Auto-serve the exported atlas HTML over local HTTP and open it in the browser",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for auto-serving the atlas HTML (default: 8000)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose parser messages",
    )

    args = parser.parse_args()

    if args.commands:
        display_commands_table()
        if not args.repo and not args.repo_flag:
            return

    # If repo is not supplied, prompt interactively
    repo_input = args.repo_flag or args.repo
    if not repo_input:
        console.print("[bold cyan]Karuvi Whole-Repository Analyzer[/bold cyan]")
        try:
            repo_input = input("Enter repository path [default: .]: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Cancelled.[/yellow]")
            return
        if not repo_input:
            repo_input = "."

    repo_input = repo_input.strip().strip("'\"")
    repo_path = Path(repo_input).expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        console.print(f"[bold red]Error:[/bold red] Directory not found: [yellow]{repo_path}[/yellow]")
        alt_home = Path.home() / repo_path.name
        lower_path = Path(str(repo_path).replace("/Tarun/", "/tarun/"))
        if alt_home.exists() and alt_home.is_dir():
            console.print(f"[bold green]Did you mean:[/bold green] [cyan]{alt_home}[/cyan]")
        elif lower_path.exists() and lower_path.is_dir():
            console.print(f"[bold green]Did you mean (Linux paths are case-sensitive):[/bold green] [cyan]{lower_path}[/cyan]")
        sys.exit(1)

    console.print(f"\n[bold]Scanning repository:[/bold] [cyan]{repo_path}[/cyan]\n")

    # Analyze repository
    parsed_modules, global_index, builder = analyze_repository(repo_path, verbose=args.verbose)

    # Handle specific inspection flags
    if args.tree:
        # Match exact or partial file path
        target_file = args.tree
        if target_file not in parsed_modules:
            matches = [k for k in parsed_modules if target_file in k]
            if matches:
                target_file = matches[0]

        if target_file in parsed_modules:
            render_ascii_intra_tree(parsed_modules[target_file], target_file)
        else:
            console.print(f"[bold red]Error:[/bold red] File [yellow]{args.tree}[/yellow] not found in parsed modules.")

    if args.deps:
        target_file = args.deps
        if target_file not in parsed_modules:
            matches = [k for k in parsed_modules if target_file in k]
            if matches:
                target_file = matches[0]

        render_ascii_deps(builder, target_file)

    if args.inspect:
        target_file = args.inspect
        if target_file not in parsed_modules:
            matches = [k for k in parsed_modules if target_file in k]
            if matches:
                target_file = matches[0]

        if target_file in parsed_modules:
            mod = parsed_modules[target_file]
            console.print(f"\n[bold cyan]Symbol Inspector for {target_file}:[/bold cyan]")
            for fn in mod.functions:
                console.print(f"[green]Function:[/green] {fn.name}{fn.signature} (uuid: {fn.uuid})")
            for cls in mod.classes:
                console.print(f"[magenta]Class:[/magenta] {cls.name} (uuid: {cls.uuid})")
                for fn in cls.functions:
                    console.print(f"  [green]Method:[/green] {fn.name}{fn.signature} (uuid: {fn.uuid})")
            if mod.scope:
                for name, var in mod.scope.symbols.items():
                    console.print(f"[blue]Variable:[/blue] {var.display_str()}")
        else:
            console.print(f"[bold red]Error:[/bold red] File {args.inspect} not found in parsed modules.")

    if args.blast:
        render_ascii_blast(builder, parsed_modules, args.blast)

    if args.cycles:
        render_ascii_cycles(builder)

    if args.graph:
        render_ascii_graph(builder)

    if args.chart:
        target_file = args.chart
        if target_file not in parsed_modules:
            matches = [k for k in parsed_modules if target_file in k]
            if matches:
                target_file = matches[0]

        if target_file in parsed_modules:
            mod = parsed_modules[target_file]
            console.print(f"\n[bold cyan]Code Flow Chart for {target_file}:[/bold cyan]")
            def print_tree_simple(t, indent=""):
                name = t.name or (t.variable.name if t.variable else 'Node')
                console.print(f"{indent}- {name}")
                for c in t.children:
                    print_tree_simple(c, indent + "  ")
            print_tree_simple(mod.code_flow)
        else:
            console.print(f"[bold red]Error:[/bold red] File {args.chart} not found in parsed modules.")

    arch_model = None
    # Reconstructed Architecture Mode 
    needs_arch_model = bool(
        args.architecture
        or args.arch_json
        or args.arch_doc
        or args.onboard
    )
    if needs_arch_model:
        from architecture.analyzer import ArchitectureAnalyzer

        arch_analyzer = ArchitectureAnalyzer(repo_path)
        arch_model = arch_analyzer.analyze(builder)

        if args.architecture:
            render_architecture_dashboard(arch_model)

        if args.arch_json:
            from architecture.serialization import export_architecture_json
            export_architecture_json(arch_model, args.arch_json)
            console.print(f"[bold green]✔[/bold green] Exported architecture model JSON to [cyan]{args.arch_json}[/cyan]")

        if args.arch_doc:
            from architecture.documentation import generate_architecture_markdown
            doc_text = generate_architecture_markdown(arch_model)
            out_doc = Path(args.arch_doc)
            out_doc.parent.mkdir(parents=True, exist_ok=True)
            out_doc.write_text(doc_text, encoding="utf-8")
            console.print(f"[bold green]✔[/bold green] Exported architecture documentation to [cyan]{args.arch_doc}[/cyan]")

        if args.onboard:
            from architecture.onboarding import CodebaseOnboardingEngine
            plan = CodebaseOnboardingEngine(arch_model, builder).build_plan()
            render_onboarding_course(plan, level=args.level)

    if args.interactive:
        interactive_menu(repo_path, parsed_modules, global_index, builder)
        return

    has_specific_flag = bool(
        args.tree
        or args.deps
        or args.inspect
        or args.blast
        or args.cycles
        or args.graph
        or args.chart
        or args.architecture
        or args.onboard
        or args.export
    )

    # Handle outputs
    json_path = Path(args.json) if args.json else None
    html_path = Path(args.html) if args.html else None

    # --explore now runs the classic terminal dashboard (the former default).
    classic_run = args.explore and not has_specific_flag
    if classic_run:
        display_dashboard(repo_path, parsed_modules, builder)
        # If neither flag was provided and running interactively, offer to save
        if not json_path and not html_path and sys.stdin.isatty():
            try:
                choice = input("\nSave analysis outputs? ([j]son / [h]tml / [b]oth / [n]one) [b]: ").strip().lower()
                if choice in ("", "b", "both"):
                    json_path = repo_path / "karuvi_analysis.json"
                    html_path = repo_path / "karuvi_atlas.html"
                elif choice in ("j", "json"):
                    json_path = repo_path / "karuvi_analysis.json"
                elif choice in ("h", "html"):
                    html_path = repo_path / "karuvi_atlas.html"
            except (KeyboardInterrupt, EOFError):
                pass

    if args.export:
        if json_path is None:
            json_path = repo_path / "karuvi_analysis.json"
        if html_path is None:
            html_path = repo_path / "karuvi_atlas.html"

    # New default: no flags at all → export the Atlas and auto-serve it over HTTP
    bare_run = (
        not has_specific_flag
        and not args.explore
        and json_path is None
        and html_path is None
    )
    if bare_run:
        atlas_path = html_path if html_path is not None else (repo_path / "karuvi_atlas.html")
        export_outputs(repo_path, parsed_modules, builder, arch_model=arch_model, html_path=atlas_path)
        serve_and_open(atlas_path, port=args.port)
    else:
        export_outputs(
            repo_path,
            parsed_modules,
            builder,
            arch_model=arch_model,
            json_path=json_path,
            html_path=html_path,
        )

    if args.export and args.open and html_path is not None:
        serve_and_open(html_path, port=args.port)

    if args.mermaid:
        console.print("\n[bold]Mermaid Graph:[/bold]\n")
        print(builder.to_mermaid())

    if args.serve:
        console.print("\n[bold cyan]Starting Karuvi Daemon...[/bold cyan]")
        import uvicorn
        from main import app, init_project, InitRequest
        init_project(InitRequest(project_root=str(repo_path), parse_all=False))
        import main
        main.PARSED = parsed_modules
        main.PROJECT_ROOT = repo_path
        main.GLOBAL_INDEX = global_index
        uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
