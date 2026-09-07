"""
DeepWiki Architecture Engine for Local Repositories
===================================================

Complete Python implementation of the DeepWiki architecture generation engine
(ported from AsyncFuncAI/deepwiki-open for local codebases):
- File tree & README inspection
- XML-based architecture structure determination with regex fallback
- Source-grounded technical page generation with relevant file context
- Source citation post-processing: Sources: [file.py:10-25]() -> interactive links
- Multi-provider AI execution (Gemini, OpenAI, OpenRouter, Ollama, Anthropic)
- Deterministic offline architectural fallback when no provider is connected
- Instant caching and export (Markdown/JSON)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from architecture.deepwiki_prompts import build_page_prompt, build_structure_prompt
from architecture.models import (
    WikiCacheData,
    WikiPage,
    WikiSection,
    WikiStructureModel,
)
from architecture.providers import (
    AIProviderConfig,
    generate_completion,
    is_provider_configured,
)

logger = logging.getLogger("karuvi.architecture.deepwiki")

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
    "dist",
    "karuvi.egg-info",
    ".egg-info",
}

DEFAULT_EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
}


def read_repo_file_tree(
    repo_path: str | Path,
    excluded_dirs: set[str] | None = None,
    excluded_extensions: set[str] | None = None,
) -> tuple[list[str], str]:
    """
    Scans a local repository directory, returning (sorted file tree, README text).
    """
    root_p = Path(repo_path).resolve()
    exc_dirs = excluded_dirs or DEFAULT_EXCLUDED_DIRS
    exc_exts = excluded_extensions or DEFAULT_EXCLUDED_EXTENSIONS

    file_list: list[str] = []
    readme_content: str = ""

    for root, dirs, files in os.walk(root_p):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in exc_dirs]
        for f in files:
            if f.startswith("."):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in exc_exts:
                continue

            full_p = Path(root) / f
            try:
                rel_p = str(full_p.relative_to(root_p))
            except ValueError:
                rel_p = str(full_p)

            file_list.append(rel_p)

            # Check for README
            if f.lower().startswith("readme") and not readme_content:
                try:
                    readme_content = full_p.read_text(encoding="utf-8", errors="replace")[:10000]
                except Exception as e:
                    logger.warning(f"Could not read README at {full_p}: {e}")

    file_list.sort()
    return file_list, readme_content


def _normalize_importance(value: str | None) -> str:
    v = (value or "").strip().lower()
    return v if v in ("high", "medium", "low") else "medium"


def _pages_via_regex(xml_text: str) -> list[WikiPage]:
    """Fallback when strict XML parsing fails or yields no pages."""
    pages: list[WikiPage] = []
    for i, block in enumerate(re.findall(r"<page\b[\s\S]*?</page>", xml_text)):
        pid = re.search(r'<page\s+id="([^"]+)"', block)
        title = re.search(r"<title>([\s\S]*?)</title>", block)
        importance = re.search(r"<importance>([\s\S]*?)</importance>", block)
        parent_sec = re.search(r"<parent_section>([\s\S]*?)</parent_section>", block)
        file_paths = [
            m.strip()
            for m in re.findall(r"<file_path>([\s\S]*?)</file_path>", block)
            if m.strip()
        ]
        related = [
            m.strip()
            for m in re.findall(r"<related>([\s\S]*?)</related>", block)
            if m.strip()
        ]
        pages.append(
            WikiPage(
                id=pid.group(1) if pid else f"page-{i + 1}",
                title=title.group(1).strip() if title else f"Page {i + 1}",
                content="",
                file_paths=file_paths,
                importance=_normalize_importance(importance.group(1) if importance else None),
                related_pages=related,
                parent_section=parent_sec.group(1).strip() if parent_sec else None,
            )
        )
    return pages


def _sections_via_regex(xml_text: str) -> tuple[list[WikiSection], list[str]]:
    """Recover complete <section> blocks via regex fallback."""
    sections: list[WikiSection] = []
    referenced: set[str] = set()
    for i, block in enumerate(re.findall(r"<section\b[\s\S]*?</section>", xml_text)):
        sid = re.search(r'<section\s+id="([^"]+)"', block)
        title = re.search(r"<title>([\s\S]*?)</title>", block)
        page_refs = [
            m.strip()
            for m in re.findall(r"<page_ref>([\s\S]*?)</page_ref>", block)
            if m.strip()
        ]
        subs = [
            m.strip()
            for m in re.findall(r"<section_ref>([\s\S]*?)</section_ref>", block)
            if m.strip()
        ]
        s_id = sid.group(1) if sid else f"section-{i + 1}"
        sections.append(
            WikiSection(
                id=s_id,
                title=title.group(1).strip() if title else f"Section {i + 1}",
                pages=page_refs,
                subsections=subs or None,
            )
        )
        referenced.update(subs)
    root_sections = [s.id for s in sections if s.id not in referenced]
    return sections, root_sections


def parse_wiki_structure(text: str, title_fallback: str = "Repository Architecture") -> WikiStructureModel:
    """
    Parse LLM response containing <wiki_structure> XML into WikiStructureModel.
    Handles markdown fences, unescaped ampersands, truncated closing tags, and regex fallback.
    """
    clean_text = re.sub(r"^```(?:xml)?\s*", "", text.strip(), flags=re.IGNORECASE)
    clean_text = re.sub(r"```\s*$", "", clean_text)

    match = re.search(r"<wiki_structure>[\s\S]*?</wiki_structure>", clean_text)
    if match:
        xml_text = match.group(0)
    else:
        open_match = re.search(r"<wiki_structure>[\s\S]*", clean_text)
        if not open_match:
            # Try to salvage any pages/sections inside
            pages = _pages_via_regex(clean_text)
            sections, root_secs = _sections_via_regex(clean_text)
            if pages:
                return WikiStructureModel(
                    id="root",
                    title=title_fallback,
                    description="Repository Architecture Wiki",
                    pages=pages,
                    sections=sections,
                    root_sections=root_secs,
                )
            raise ValueError("No valid <wiki_structure> XML found in model response")
        xml_text = f"{open_match.group(0)}\n</wiki_structure>"

    # Strip control characters and escape bare ampersands
    xml_text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_text)
    xml_text = re.sub(
        r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", xml_text
    )

    root: ET.Element | None = None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        logger.warning(f"Strict XML parse error, using regex fallback: {err}")

    if root is not None:
        title = (root.findtext("title") or title_fallback).strip()
        description = (root.findtext("description") or "Architecture Documentation").strip()
        pages: list[WikiPage] = []
        for i, el in enumerate(root.iter("page")):
            pid = el.get("id") or f"page-{i + 1}"
            pages.append(
                WikiPage(
                    id=pid,
                    title=(el.findtext("title") or "").strip() or f"Page {i + 1}",
                    content="",
                    file_paths=[e.text.strip() for e in el.iter("file_path") if e.text and e.text.strip()],
                    importance=_normalize_importance(el.findtext("importance")),
                    related_pages=[e.text.strip() for e in el.iter("related") if e.text and e.text.strip()],
                    parent_section=(el.findtext("parent_section") or "").strip() or None,
                )
            )

        sections: list[WikiSection] = []
        referenced_subs: set[str] = set()
        for i, el in enumerate(root.iter("section")):
            sid = el.get("id") or f"section-{i + 1}"
            subs = [e.text.strip() for e in el.iter("section_ref") if e.text and e.text.strip()]
            sections.append(
                WikiSection(
                    id=sid,
                    title=(el.findtext("title") or "").strip() or f"Section {i + 1}",
                    pages=[e.text.strip() for e in el.iter("page_ref") if e.text and e.text.strip()],
                    subsections=subs or None,
                )
            )
            referenced_subs.update(subs)
        root_sections = [s.id for s in sections if s.id not in referenced_subs]

        if pages:
            return WikiStructureModel(
                id="root",
                title=title,
                description=description,
                pages=pages,
                sections=sections,
                root_sections=root_sections,
            )

    # Fallback to regex
    pages = _pages_via_regex(xml_text)
    sections, root_sections = _sections_via_regex(xml_text)
    return WikiStructureModel(
        id="root",
        title=title_fallback,
        description="Architecture Documentation",
        pages=pages,
        sections=sections,
        root_sections=root_sections,
    )


def post_process_wiki_content(
    content: str,
    file_paths: list[str],
    repo_path: str | Path,
) -> str:
    """
    Normalizes the <details> block and resolves citations like Sources: [file.py:10-25]()
    into interactive anchors clickable in Karuvi's Code Explorer.
    """
    processed = content.strip()
    # Strip wrapping markdown code blocks if the model emitted them
    processed = re.sub(r"^```(?:markdown)?\s*", "", processed, flags=re.IGNORECASE)
    processed = re.sub(r"```\s*$", "", processed)

    # 1. Ensure <details> block is cleanly present
    details_pattern = re.compile(
        r"<details>\s*<summary>\s*Relevant source files\s*</summary>[\s\S]*?</details>",
        re.IGNORECASE,
    )
    links_str = "\n".join(f"- [{p}](#code:{p})" for p in file_paths)
    correct_details = (
        "<details>\n"
        "<summary>Relevant source files</summary>\n\n"
        "The following files were used as context for generating this wiki page:\n\n"
        f"{links_str}\n"
        "</details>"
    )
    if details_pattern.search(processed):
        processed = details_pattern.sub(lambda _: correct_details, processed)
    else:
        processed = f"{correct_details}\n\n{processed}"

    # 2. Resolve empty citations: [path.py:10-20]() or Sources: [path.py:10]()
    # into interactive code anchors: [path.py:10-20](#code:path.py:10-20)
    def _repl_citation(m: re.Match) -> str:
        fpath = m.group(1)
        start = m.group(2)
        end = m.group(3)
        line_part = f":{start}-{end}" if end else (f":{start}" if start else "")
        anchor = f"#code:{fpath}{line_part}"
        return f"[{fpath}{line_part}]({anchor})"

    # Match [path:start-end]()
    citation_re = re.compile(
        r"\[([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)(?::(\d+)(?:-(\d+))?)?\]\(\)"
    )
    processed = citation_re.sub(_repl_citation, processed)

    # Remove stray empty parens like ]()()
    processed = re.sub(r"(\]\([^)\s]+\))\(\)", r"\1", processed)

    return processed


def generate_fallback_structure(
    repo_path: Path,
    file_list: list[str],
    readme: str,
) -> WikiStructureModel:
    """
    Generates a deterministic, high-quality DeepWiki architecture structure
    when no AI provider is configured or offline.
    """
    repo_name = repo_path.name
    py_files = [f for f in file_list if f.endswith(".py")]

    # Identify logical groupings
    arch_files = [f for f in py_files if "architecture" in f]
    cli_files = [f for f in py_files if "cli" in f or "main" in f]
    core_files = [f for f in py_files if f not in arch_files and f not in cli_files and not f.startswith("tests/")]
    test_files = [f for f in py_files if f.startswith("tests/")]

    pages: list[WikiPage] = [
        WikiPage(
            id="architecture-overview",
            title="System Architecture & Overview",
            importance="high",
            file_paths=(cli_files[:2] + core_files[:3] + arch_files[:2]) or file_list[:5],
            related_pages=["core-components", "data-flows"],
            parent_section="sec-overview",
        ),
        WikiPage(
            id="core-components",
            title="Core Components & Subsystems",
            importance="high",
            file_paths=(core_files[:5] or py_files[:5]),
            related_pages=["architecture-overview", "interfaces-and-cli"],
            parent_section="sec-components",
        ),
        WikiPage(
            id="data-flows",
            title="Data Management & Dependency Flows",
            importance="medium",
            file_paths=(core_files[:4] + arch_files[:2]) or file_list[:5],
            related_pages=["core-components"],
            parent_section="sec-flows",
        ),
        WikiPage(
            id="interfaces-and-cli",
            title="Interfaces, CLI & Daemon Architecture",
            importance="high",
            file_paths=(cli_files + core_files[:2]) or file_list[:4],
            related_pages=["architecture-overview"],
            parent_section="sec-interfaces",
        ),
    ]

    if arch_files:
        pages.append(
            WikiPage(
                id="deepwiki-cartography",
                title="DeepWiki Architecture Cartography Engine",
                importance="medium",
                file_paths=arch_files[:6],
                related_pages=["architecture-overview"],
                parent_section="sec-components",
            )
        )

    sections: list[WikiSection] = [
        WikiSection(
            id="sec-overview",
            title="System Overview",
            pages=["architecture-overview"],
        ),
        WikiSection(
            id="sec-components",
            title="Core Subsystems",
            pages=["core-components"] + (["deepwiki-cartography"] if arch_files else []),
        ),
        WikiSection(
            id="sec-flows",
            title="Data & Control Flows",
            pages=["data-flows"],
        ),
        WikiSection(
            id="sec-interfaces",
            title="Interfaces & Services",
            pages=["interfaces-and-cli"],
        ),
    ]

    return WikiStructureModel(
        id="root",
        title=f"{repo_name} Architecture Wiki",
        description=f"DeepWiki architectural synthesis and subsystem breakdown for {repo_name}.",
        pages=pages,
        sections=sections,
        root_sections=["sec-overview", "sec-components", "sec-flows", "sec-interfaces"],
    )


def generate_fallback_page_content(
    repo_path: Path,
    page: WikiPage,
) -> str:
    """
    Synthesizes a source-grounded technical architecture wiki page deterministically.
    """
    lines = [
        f"# {page.title}\n",
        f"This page documents the technical architecture, responsibilities, and implementation structure of **{page.title}** within the repository.\n",
        "## Subsystem Responsibilities & Overview\n",
        "The components in this subsystem provide core infrastructure, data representations, and execution logic essential for repository operations.\n",
        "### Key Source Modules & Implementations\n",
    ]

    for rel_p in page.file_paths:
        full_p = repo_path / rel_p
        if full_p.exists() and full_p.is_file():
            try:
                content = full_p.read_text(encoding="utf-8", errors="replace")
                line_count = len(content.splitlines())
                # Extract first docstring or functions
                first_lines = [l for l in content.splitlines()[:20] if l.strip() and not l.startswith("#")]
                summary_sample = " ".join(first_lines[:4]) if first_lines else "Module implementation"
                lines.append(f"#### `{rel_p}`")
                lines.append(f"- **Lines**: {line_count}")
                lines.append(f"- **Source Reference**: Sources: [{rel_p}:1-{min(line_count, 30)}]()")
                lines.append(f"- **Summary**: Encapsulates subsystem logic for `{Path(rel_p).stem}`.\n")
            except Exception:
                pass

    lines.append("## Architectural Data Flow\n")
    lines.append("Data within this subsystem flows through directed pipelines:\n")
    lines.append("1. **Ingestion & Invocation**: Calls originate from top-level entrypoints or client requests.")
    lines.append("2. **Transformation & Validation**: Inputs are validated and transformed into structured domain models.")
    lines.append("3. **Persistence & Serialization**: Outputs are formatted and dispatched to consumers or visualizations.\n")

    lines.append("## Interface & Configuration Summary\n")
    lines.append("| Component | Primary File | Role |")
    lines.append("| :--- | :--- | :--- |")
    for rel_p in page.file_paths:
        lines.append(f"| `{Path(rel_p).stem}` | Sources: [{rel_p}]() | Subsystem Module |")

    return "\n".join(lines)


class DeepWikiEngine:
    """
    Orchestrates the DeepWiki architecture generation pipeline for local repositories.
    """

    def __init__(
        self,
        repo_path: str | Path,
        provider_config: AIProviderConfig | None = None,
        cache_dir: str | Path | None = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.provider_config = (provider_config or AIProviderConfig()).resolve()
        self.cache_dir = Path(cache_dir or (self.repo_path / ".karuvi" / "wikicache"))

    def get_cache_file_path(self, language: str = "en") -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", self.repo_path.name)
        return self.cache_dir / f"deepwiki_cache_local_{safe_name}_{language}.json"

    def load_cache(self, language: str = "en") -> WikiCacheData | None:
        cache_file = self.get_cache_file_path(language)
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                logger.info(f"[deepwiki] Loaded cached architecture wiki from {cache_file}")
                return WikiCacheData.from_dict(data)
            except Exception as e:
                logger.warning(f"Could not load cache from {cache_file}: {e}")
        return None

    def save_cache(self, cache_data: WikiCacheData, language: str = "en") -> None:
        cache_file = self.get_cache_file_path(language)
        try:
            cache_file.write_text(
                json.dumps(cache_data.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(f"[deepwiki] Saved architecture wiki cache to {cache_file}")
        except Exception as e:
            logger.warning(f"Could not save cache to {cache_file}: {e}")

    def determine_structure(
        self,
        file_list: list[str],
        readme: str,
        comprehensive: bool = True,
        language: str = "en",
    ) -> WikiStructureModel:
        """
        Determines the DeepWiki architecture structure using AI provider or fallback.
        """
        if is_provider_configured(self.provider_config):
            try:
                file_tree_str = "\n".join(file_list[:150])
                prompt = build_structure_prompt(
                    repo_name=self.repo_path.name,
                    file_tree=file_tree_str,
                    readme=readme,
                    comprehensive=comprehensive,
                    language=language,
                )
                logger.info(f"[deepwiki] Prompting {self.provider_config.provider} for architecture structure...")
                response_text = generate_completion(prompt, self.provider_config)
                structure = parse_wiki_structure(response_text, title_fallback=f"{self.repo_path.name} Architecture")
                if structure and structure.pages:
                    logger.info(f"[deepwiki] Successfully determined structure with {len(structure.pages)} pages.")
                    return structure
            except Exception as e:
                logger.warning(f"[deepwiki] AI structure determination failed: {e}. Falling back to deterministic structure.")

        return generate_fallback_structure(self.repo_path, file_list, readme)

    def generate_page(
        self,
        page: WikiPage,
        language: str = "en",
    ) -> WikiPage:
        """
        Generates content for a single DeepWiki architecture page.
        """
        file_links = "\n".join(f"- [{p}](#code:{p})" for p in page.file_paths)

        if is_provider_configured(self.provider_config):
            try:
                # Read source file contents up to 40KB budget
                file_contents = []
                total_bytes = 0
                for rel_p in page.file_paths:
                    full_p = self.repo_path / rel_p
                    if full_p.exists() and full_p.is_file():
                        try:
                            txt = full_p.read_text(encoding="utf-8", errors="replace")[:10000]
                            total_bytes += len(txt)
                            file_contents.append(f"### File: {rel_p}\n```\n{txt}\n```\n")
                            if total_bytes > 40000:
                                break
                        except Exception:
                            pass

                contents_block = "\n".join(file_contents)
                prompt = build_page_prompt(
                    title=page.title,
                    file_links=file_links,
                    file_contents_block=contents_block,
                    language=language,
                )
                logger.info(f"[deepwiki] Prompting {self.provider_config.provider} for page '{page.title}'...")
                raw_content = generate_completion(prompt, self.provider_config)
                processed = post_process_wiki_content(raw_content, page.file_paths, self.repo_path)
                return WikiPage(
                    id=page.id,
                    title=page.title,
                    content=processed,
                    file_paths=page.file_paths,
                    importance=page.importance,
                    related_pages=page.related_pages,
                    parent_section=page.parent_section,
                )
            except Exception as e:
                logger.warning(f"[deepwiki] AI page generation failed for '{page.title}': {e}. Using fallback content.")

        fallback_body = generate_fallback_page_content(self.repo_path, page)
        processed = post_process_wiki_content(fallback_body, page.file_paths, self.repo_path)
        return WikiPage(
            id=page.id,
            title=page.title,
            content=processed,
            file_paths=page.file_paths,
            importance=page.importance,
            related_pages=page.related_pages,
            parent_section=page.parent_section,
        )

    def generate_wiki(
        self,
        use_cache: bool = True,
        comprehensive: bool = True,
        language: str = "en",
    ) -> WikiCacheData:
        """
        Executes the full DeepWiki architecture generation pipeline.
        """
        if use_cache:
            cached = self.load_cache(language)
            if cached is not None:
                return cached

        logger.info(f"[deepwiki] Scanning local repository at {self.repo_path}...")
        file_list, readme = read_repo_file_tree(self.repo_path)

        structure = self.determine_structure(file_list, readme, comprehensive=comprehensive, language=language)

        generated_pages: dict[str, WikiPage] = {}
        for p in structure.pages:
            logger.info(f"[deepwiki] Generating page: {p.title} ({p.id})")
            gen_p = self.generate_page(p, language=language)
            generated_pages[p.id] = gen_p

        cache_data = WikiCacheData(
            wiki_structure=structure,
            generated_pages=generated_pages,
            provider=self.provider_config.provider,
            model=self.provider_config.model,
            timestamp=time.time(),
        )

        self.save_cache(cache_data, language=language)
        return cache_data

    def export_wiki_markdown(self, cache_data: WikiCacheData) -> str:
        """Exports the complete architecture wiki as a single Markdown document."""
        out = [
            f"# {cache_data.wiki_structure.title}\n",
            f"> {cache_data.wiki_structure.description}\n",
            f"*Generated by Karuvi DeepWiki Architecture Engine ({cache_data.provider} / {cache_data.model})*\n",
            "---\n",
        ]

        # Table of contents
        out.append("## Table of Contents\n")
        for s in cache_data.wiki_structure.sections:
            out.append(f"### {s.title}")
            for pid in s.pages:
                page = cache_data.generated_pages.get(pid)
                if page:
                    out.append(f"- [{page.title}](#{page.id})")
            out.append("")

        out.append("---\n")

        # Pages
        for pid, page in cache_data.generated_pages.items():
            out.append(f"<a id=\"{pid}\"></a>\n")
            out.append(page.content)
            out.append("\n---\n")

        return "\n".join(out)
