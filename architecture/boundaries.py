"""
Structural Boundary Detection
=============================

Derives structural component candidates from directory and package hierarchies.
Ignores generic root directories (src, lib, etc.) and assigns each module to its
primary meaningful structural boundary.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from architecture.models import ArchitectureConfig
from architecture.module_graph import normalize_module_path


def extract_module_boundary(
    rel_path: str,
    ignored_boundaries: set[str] | None = None,
) -> str:
    """
    Extracts the first meaningful architectural boundary for a repository-relative path.

    Example:
        src/api/users.py -> "api"
        backend/auth/login.py -> "backend/auth" (or "backend" depending on depth)
        app.py -> "root"
    """
    if ignored_boundaries is None:
        ignored_boundaries = ArchitectureConfig().ignored_boundaries

    parts = [p for p in Path(rel_path).parent.parts if p not in (".", "")]

    # Strip generic root wrappers like "src", "lib"
    meaningful = [p for p in parts if p.lower() not in ignored_boundaries]

    if not meaningful:
        # File lives in root directory or only inside ignored wrappers (e.g. src/main.py)
        return "root"

    # If 2 or more meaningful parts exist, we use the first one as top-level boundary,
    # or preserve first two if deeply nested (e.g. backend/auth vs backend)
    # Default to the primary top-level directory under src/
    if len(meaningful) >= 2:
        return f"{meaningful[0]}/{meaningful[1]}"
    return meaningful[0]


def detect_boundaries(
    module_graph: nx.DiGraph,
    repository_root: Path | str,
    config: ArchitectureConfig | None = None,
) -> dict[str, str]:
    """
    Detects structural package boundaries for all modules in the module graph.

    Returns:
        Mapping of module_id -> boundary_name (e.g. {"services/auth.py": "services"})
    """
    cfg = config or ArchitectureConfig()
    boundaries: dict[str, str] = {}
    repo_root = Path(repository_root).resolve()

    for node in module_graph.nodes:
        node_data = module_graph.nodes[node]
        file_path = node_data.get("path") or node
        norm_path = normalize_module_path(file_path, repo_root)
        boundary = extract_module_boundary(norm_path, cfg.ignored_boundaries)
        boundaries[node] = boundary

    return boundaries
