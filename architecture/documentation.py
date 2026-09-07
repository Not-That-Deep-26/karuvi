"""
DeepWiki Architecture Documentation Generator
=============================================

Generates comprehensive DeepWiki Markdown documentation:
- Full table of contents with sections and pages
- Technical architecture explanations with <details> source files blocks
- Architectural data flows, component dependencies, and interface tables
- Exact source code citations: Sources: [file.py:lines]()
"""
from __future__ import annotations

from architecture.models import ArchitectureModel


def generate_architecture_markdown(model: ArchitectureModel) -> str:
    """
    Generates a comprehensive DeepWiki Markdown report of the architecture.
    """
    if model.wiki_cache:
        from architecture.deepwiki_engine import DeepWikiEngine
        engine = DeepWikiEngine(model.repository_root)
        return engine.export_wiki_markdown(model.wiki_cache)

    if model.wiki_pages:
        lines: list[str] = [
            "# Repository Architecture\n",
            f"Karuvi DeepWiki Architecture Analysis for `{model.repository_root}`\n",
            "---\n",
        ]
        for pid, page in model.wiki_pages.items():
            lines.append(page.content)
            lines.append("\n---\n")
        return "\n".join(lines)

    # Fallback to basic structure report
    lines: list[str] = [
        "# Repository Architecture\n",
        f"Karuvi analyzed repository: `{model.repository_root}`\n",
        f"- **{len(model.modules)}** modules analyzed",
        f"- **{len(model.components)}** architectural components discovered\n",
        "## Architectural Components\n",
    ]
    for comp_id, comp in model.components.items():
        lines.append(f"### Component: {comp.name}")
        lines.append(f"- **Modules ({len(comp.modules)})**:")
        for m in comp.modules:
            role = model.roles.get(m, "MODULE")
            lines.append(f"  - `{m}` _(Role: {role})_")
        lines.append("")

    return "\n".join(lines)
