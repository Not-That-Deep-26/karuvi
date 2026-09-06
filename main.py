"""
Karuvi Daemon — Stateful Analysis Server
========================================

A FastAPI service that keeps a project root in memory, parses Python source files
into an in-memory graph, and exposes cross-module dependency tracing over HTTP.

The daemon is *stateful*: you initialise it once with a project root, and every
subsequent query reads from the in-memory cache.  Cross-module imports are
resolved automatically — the end-user never has to worry about parse order.

Quick start
-----------
    uvicorn main:app --reload
    POST /init  {"project_root": "/path/to/project"}
    GET  /dependencies?file=package/foo.py&start=10&end=15

Endpoints
---------
POST /init
    Set (or reset) the project root.  Optionally parses every .py file in the
    tree so that the graph is warm before any queries.

DELETE /project
    Drop all in-memory state and start fresh.

GET  /status
    Return the project root, number of managed files, and total parse count.

GET  /files
    List every parsed file (absolute path + module name).

POST /parse
    Parse a single file on demand (relative to the project root).  Returns the
    full module analysis.  Already-parsed files are skipped unless ``force`` is
    set.

GET  /dependencies
    The core endpoint.  Given a filename (relative to the project root) and a
    line range, return every symbol reference occurring in that range together
    with the line/col/uuid of the declaration it resolves to — including
    cross-file references.

GET  /tree       — dependency tree for one file
GET  /classes    — classes (and methods) for one file
GET  /functions  — functions for one file
GET  /scopes     — scope hierarchy for one file
GET  /variables  — look up a variable by name (searches all modules)
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

import deps
import get_tree
from pointers import GlobalIndex
from returns import (
    Module,
    class_to_dict,
    deptree_to_dict,
    function_to_dict,
    module_to_dict,
    scope_to_dict,
    variable_to_dict,
)

# ──────────────────────────────────────────────────────────────────────────────
# Daemon state
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT: Path | None = None
GLOBAL_INDEX: GlobalIndex | None = None
PARSED: dict[str, Module] = {}   # key = relative path (posix)
TOTAL_PARSES: int = 0

Exclude_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", ".mypy_cache"}

def _reset():
    global PROJECT_ROOT, GLOBAL_INDEX, PARSED, TOTAL_PARSES
    PROJECT_ROOT = None
    GLOBAL_INDEX = None
    PARSED = {}
    TOTAL_PARSES = 0

# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Karuvi Daemon",
    description=(
        "Stateful code-analysis server.  Initialise with a project root, and "
        "all subsequent dependency queries resolve automatically across modules."
    ),
    version="1.0.0",
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _require_project() -> Path:
    if PROJECT_ROOT is None:
        raise HTTPException(
            status_code=409,
            detail="No project loaded.  POST /init with a project_root first.",
        )
    assert PROJECT_ROOT is not None
    return PROJECT_ROOT


def _require_file(rel: str) -> str:
    """Validate that *rel* is a known managed file; return the absolute path."""
    _require_project()
    if rel not in PARSED:
        raise HTTPException(
            status_code=404,
            detail=f"File not managed: {rel!r}.  POST /parse to load it first.",
        )
    return str((PROJECT_ROOT / rel).resolve())


def _rel(path: Path) -> str:
    """Return the POSIX relative path string of *path* with respect to PROJECT_ROOT."""
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))


def _find_scope(current, name: str):
    if current is None:
        return None
    if current.name == name:
        return current
    for child in current.children.values():
        found = _find_scope(child, name)
        if found is not None:
            return found
    return None


def _parse_one(abs_path: str, rel_key: str) -> Module:
    """Parse a single file using the daemon-global index.  Returns the Module."""
    global TOTAL_PARSES
    mod = get_tree.parse_file(
        abs_path, global_index=GLOBAL_INDEX, verbose=False
    )
    # Ensure the module knows the right file_path and store it
    mod.file_path = abs_path
    PARSED[rel_key] = mod
    TOTAL_PARSES += 1
    return mod

# ──────────────────────────────────────────────────────────────────────────────
# Request models
# ──────────────────────────────────────────────────────────────────────────────

class InitRequest(BaseModel):
    """Body for ``POST /init``."""

    project_root: str = Field(
        ...,
        description="Absolute path to the project root directory.",
    )
    parse_all: bool = Field(
        True,
        description="When true, every .py file found under the root is parsed immediately.",
    )
    extra_search_paths: list[str] = Field(
        default_factory=list,
        description=(
            "Additional directories to search when resolving imports "
            "(e.g. [\"libs\"])."
        ),
    )


class ParseRequest(BaseModel):
    """Body for ``POST /parse``."""

    file: str = Field(
        ...,
        description="Path to the file, relative to the project root.",
    )
    force: bool = Field(
        False,
        description="Re-parse even if the file is already loaded.",
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /init
# ──────────────────────────────────────────────────────────────────────────────

@app.post(
    "/init",
    summary="Initialise the project",
    description=(
        "Set the project root and build the in-memory dependency graph.  "
        "Existing state is dropped first."
    ),
)
def init_project(req: InitRequest):
    _reset()

    root = Path(req.project_root).resolve()
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {root}")

    # Build a fresh GlobalIndex for this project session
    index = GlobalIndex()
    index.add_search_path(root)
    for esp in req.extra_search_paths:
        index.add_search_path(Path(esp))

    global PROJECT_ROOT, GLOBAL_INDEX
    PROJECT_ROOT = root
    GLOBAL_INDEX = index

    # Discover .py files
    py_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in Exclude_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(Path(dirpath) / f)
    py_files.sort()

    file_names: list[str] = []
    if req.parse_all:
        for p in py_files:
            rel_key = _rel(p)
            try:
                _parse_one(str(p.resolve()), rel_key)
                file_names.append(rel_key)
            except Exception as exc:
                file_names.append(f"{rel_key} [error: {exc}]")

    return {
        "project_root": str(root),
        "files": file_names,
        "total_files": len(file_names),
        "extra_search_paths": req.extra_search_paths,
    }

# ──────────────────────────────────────────────────────────────────────────────
# DELETE /project
# ──────────────────────────────────────────────────────────────────────────────

@app.delete(
    "/project",
    summary="Reset the project",
    description="Drop all in-memory state.",
)
def reset_project():
    _reset()
    return {"status": "reset"}

# ──────────────────────────────────────────────────────────────────────────────
# GET /status
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/status",
    summary="Project status",
    description="Return the project root, number of managed files, and parse count.",
)
def get_status():
    return {
        "project_root": str(PROJECT_ROOT) if PROJECT_ROOT else None,
        "total_files": len(PARSED),
        "total_parses": TOTAL_PARSES,
        "files": sorted(PARSED.keys()),
    }

# ──────────────────────────────────────────────────────────────────────────────
# GET /files
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/files",
    summary="List managed files",
    description="Return every parsed file as {path, module_name}.",
)
def list_files():
    _require_project()
    return [
        {"path": rel, "module_name": mod.name}
        for rel, mod in sorted(PARSED.items())
    ]

# ──────────────────────────────────────────────────────────────────────────────
# POST /parse
# ──────────────────────────────────────────────────────────────────────────────

@app.post(
    "/parse",
    summary="Parse a single file on demand",
    description=(
        "Read and parse the file at the given relative path.  If ``force`` is "
        "false and the file is already loaded, returns the cached analysis."
    ),
)
def parse_file_endpoint(req: ParseRequest):
    _require_project()
    rel_key = req.file
    abs_path = (PROJECT_ROOT / rel_key).resolve()

    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {abs_path}")

    if rel_key in PARSED and not req.force:
        return module_to_dict(PARSED[rel_key])

    mod = _parse_one(str(abs_path), rel_key)
    return module_to_dict(mod)

# ──────────────────────────────────────────────────────────────────────────────
# GET /dependencies
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/dependencies",
    summary="Trace dependencies for a line range",
    description=(
        "Return every symbol reference in the given line range together with "
        "the line, col, uuid, and scope of the declaration it resolves to — "
        "including cross-module references."
    ),
)
def get_dependencies(
    file: str = Query(..., description="File path relative to the project root."),
    start: int = Query(..., description="First line to inspect (1-based, inclusive)."),
    end: int | None = Query(
        None,
        description="Last line to inspect (inclusive); defaults to start.",
    ),
    include_declarations: bool = Query(
        False,
        description="Also include symbols defined (not just referenced) in the range.",
    ),
):
    _require_file(file)
    mod = PARSED[file]
    recs = deps.dependencies_for_lines(
        mod, start, end, include_declarations=include_declarations
    )
    return [r.to_dict() for r in recs]

# ──────────────────────────────────────────────────────────────────────────────
# GET /tree
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/tree",
    summary="Dependency tree",
    description="Return the dependency tree for a file, optionally rooted at a scope.",
)
def get_tree_endpoint(
    file: str = Query(..., description="File path relative to the project root."),
    scope: str | None = Query(None, description="Scope name to root the tree at."),
):
    _require_file(file)
    mod = PARSED[file]

    if scope is None:
        return deptree_to_dict(mod.code_flow)

    result = _find_scope(mod.scope, scope)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Scope not found: {scope!r}")
    return scope_to_dict(result)

# ──────────────────────────────────────────────────────────────────────────────
# GET /classes
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/classes",
    summary="Classes for a file",
    description="Return every class (and its methods) found in a file.",
)
def get_classes(
    file: str = Query(..., description="File path relative to the project root."),
):
    _require_file(file)
    mod = PARSED[file]
    return [class_to_dict(c) for c in mod.classes]

# ──────────────────────────────────────────────────────────────────────────────
# GET /functions
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/functions",
    summary="Functions for a file",
    description="Return every function found in a file.",
)
def get_functions(
    file: str = Query(..., description="File path relative to the project root."),
):
    _require_file(file)
    mod = PARSED[file]
    return [function_to_dict(f) for f in mod.functions]

# ──────────────────────────────────────────────────────────────────────────────
# GET /scopes
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/scopes",
    summary="Scope hierarchy",
    description="Return the full scope tree (module → class/function scopes) for a file.",
)
def get_scopes(
    file: str = Query(..., description="File path relative to the project root."),
):
    _require_file(file)
    mod = PARSED[file]
    if mod.scope is None:
        raise HTTPException(status_code=404, detail="No scope information available.")
    return scope_to_dict(mod.scope)

# ──────────────────────────────────────────────────────────────────────────────
# GET /variables
# ──────────────────────────────────────────────────────────────────────────────

@app.get(
    "/variables",
    summary="Look up a variable by name",
    description=(
        "Search all modules for a variable by name.  Returns the first match "
        "found (module-level symbols take priority)."
    ),
)
def get_variable(
    name: str = Query(..., description="Symbol name to look up."),
    file: str | None = Query(
        None,
        description=(
            "Optional: restrict the search to a specific file (relative path).  "
            "If omitted, all managed files are searched."
        ),
    ),
):
    _require_project()

    # Search a single file first if requested
    if file is not None:
        _require_file(file)
        mod = PARSED[file]
        var = _lookup_variable(mod, name)
        if var is not None:
            return variable_to_dict(var)
        raise HTTPException(status_code=404, detail=f"Variable {name!r} not found in {file}")

    # Search all files
    for rel, mod in PARSED.items():
        var = _lookup_variable(mod, name)
        if var is not None:
            return {"found_in": rel, **variable_to_dict(var)}

    raise HTTPException(status_code=404, detail=f"Variable {name!r} not found in any managed file.")


def _lookup_variable(mod: Module, name: str):
    """Look up *name* in a module's variables dict, then in its scope hierarchy."""
    if name in mod.variables:
        return mod.variables[name]
    return _walk_scope(mod.scope, name)


def _walk_scope(scope, name: str):
    if scope is None:
        return None
    if name in scope.symbols:
        return scope.symbols[name]
    for child in scope.children.values():
        found = _walk_scope(child, name)
        if found is not None:
            return found
    return None