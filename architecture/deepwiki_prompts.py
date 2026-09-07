"""
DeepWiki Architecture Prompts
=============================

Exact prompt templates ported from DeepWiki (AsyncFuncAI/deepwiki-open).
Generates structured repository architecture wikis with:
- XML-based comprehensive architecture structure
- Source-grounded technical pages with <details> source files blocks
- Architectural flow breakdowns & relationship tables
- Precise file citations: Sources: [path:line-line]()
"""
from __future__ import annotations


_COMPREHENSIVE_STRUCTURE = """
Create a structured architecture wiki with the following main sections:
- Overview (general information about the project and its goals)
- System Architecture (subsystems, layers, component boundaries, and overall design)
- Core Components (key functionality, services, and modules)
- Data Management & Flow (how data is structured, transformed, processed, and accessed)
- Integration & Interfaces (APIs, entry points, CLI, and external connections)
- Deployment & Runtime (execution models, daemon services, configuration)
- Extensibility & Customization (plugins, customization hooks, adding new capabilities)

Each section should contain relevant pages. For example, "System Architecture" might include pages for "Layered Architecture", "Component Dependency Graph", "Data Pipeline", etc.

Return your analysis in the following XML format:

<wiki_structure>
  <title>[Overall title for the architecture wiki]</title>
  <description>[Brief description of the repository architecture]</description>
  <sections>
    <section id="section-1">
      <title>[Section title]</title>
      <pages>
        <page_ref>page-1</page_ref>
        <page_ref>page-2</page_ref>
      </pages>
      <subsections>
        <section_ref>section-2</section_ref>
      </subsections>
    </section>
    <!-- More sections as needed -->
  </sections>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
      <parent_section>section-1</parent_section>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>
"""


def build_structure_prompt(
    repo_name: str,
    file_tree: str,
    readme: str,
    comprehensive: bool = True,
    language: str = "en",
) -> str:
    """Prompt for determining the DeepWiki architecture structure."""
    page_count = "6-10" if comprehensive else "4-6"
    kind = "comprehensive" if comprehensive else "concise"

    return f"""Analyze this local repository '{repo_name}' and create a DeepWiki architecture wiki structure for it.

1. The complete file tree of the project:
<file_tree>
{file_tree}
</file_tree>

2. The README file of the project:
<readme>
{readme}
</readme>

Determine the most logical architectural structure for a technical wiki based on the repository's content.

When designing the wiki structure, include pages that focus on technical architecture, such as:
- Architecture overview & subsystem topology
- Data flow descriptions & processing pipelines
- Component relationships & dependencies
- Core abstractions & domain models
- Interfaces, CLI commands, and public APIs

{_COMPREHENSIVE_STRUCTURE}

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid XML structure specified above
- DO NOT wrap the XML in markdown code blocks (no ``` or ```xml)
- DO NOT include any explanation text before or after the XML
- Ensure the XML is properly formatted and valid
- Start directly with <wiki_structure> and end with </wiki_structure>

IMPORTANT:
1. Create {page_count} pages that would make a {kind} architecture wiki for this repository
2. Each page should focus on a specific aspect of the codebase architecture
3. The relevant_files should be actual files from the repository that are used to explain that page
4. Return ONLY valid XML with the structure specified above, with no markdown code block delimiters.
"""


def build_page_prompt(
    title: str,
    file_links: str,
    file_contents_block: str,
    language: str = "en",
) -> str:
    """
    Prompt for generating a single DeepWiki technical architecture page grounded in local source files.
    """
    return f"""You are an expert technical writer and software architect.
Your task is to generate a comprehensive, accurate technical architecture wiki page in Markdown format about "{title}" within this software project.

You will be given:
1. The "[WIKI_PAGE_TOPIC]" for the page you need to create: "{title}".
2. The "[RELEVANT_SOURCE_FILES]" from the project.
3. The actual contents of the relevant source files:
{file_contents_block}

CRITICAL STARTING INSTRUCTION:
The very first thing on the page MUST be a `<details>` block listing ALL the `[RELEVANT_SOURCE_FILES]` you used to generate the content.
Do not provide any acknowledgements, disclaimers, apologies, or any other preface before the `<details>` block. JUST START with the `<details>` block.
Format the block EXACTLY like the following template, reproducing it verbatim:
<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

{file_links}
</details>

Immediately after the `<details>` block, the main title of the page should be a H1 Markdown heading: `# {title}`.

Based ONLY on the content of the `[RELEVANT_SOURCE_FILES]`:

1.  **Introduction:** Start with a concise introduction (1-2 paragraphs) explaining the purpose, architectural role, and high-level overview of "{title}" within the context of the overall project.

2.  **Detailed Sections:** Break down "{title}" into logical sections using H2 (`##`) and H3 (`###`) Markdown headings. For each section:
    *   Explain the architecture, components, data flow, or logic relevant to the section's focus, as evidenced in the source files.
    *   Identify key functions, classes, data structures, API endpoints, or configuration elements pertinent to that section.

3.  **Architecture & Flow Breakdowns:**
    *   Clearly describe the architectural data flows, component relationships, and lifecycle states found in the source files.
    *   Explain how data moves from entry points through internal components to downstream sinks or outputs.

4.  **Tables:**
    *   Use Markdown tables to summarize information such as:
        *   Key features or components and their descriptions.
        *   API endpoint parameters, types, and descriptions.
        *   Configuration options, types, and default values.
        *   Data model fields, types, constraints, and descriptions.

5.  **Code Snippets:**
    *   Include short, relevant code snippets directly from the `[RELEVANT_SOURCE_FILES]` to illustrate key implementation details, data structures, or configurations.
    *   Ensure snippets are well-formatted within Markdown code blocks with appropriate language identifiers.

6.  **Source Citations (EXTREMELY IMPORTANT):**
    *   For EVERY piece of significant information, explanation, table entry, or code snippet, you MUST cite the specific source file(s) and relevant line numbers from which the information was derived.
    *   Place citations at the end of the paragraph, under the table, or after the code snippet.
    *   Use the EXACT format below, and ALWAYS use the FULL repository-relative path exactly as it appears in the "Relevant source files" list above — NEVER a bare filename:
        *   Range: `Sources: [src/full/path/file.py:start_line-end_line]()`
        *   Single line: `Sources: [src/full/path/file.py:line_number]()`
        *   Multiple files: `Sources: [path/a.py:1-10](), [path/b.py:5](), [path/c.py]()`
    *   The word `Sources:` MUST be placed BEFORE the opening bracket, never inside it (write `Sources: [path]()`, NOT `[Sources: path]()`).
    *   Leave the parentheses `()` EMPTY — they are resolved into real local interactive links automatically. Do not put a URL inside them.

7.  **Technical Accuracy:** All information must be derived SOLELY from the `[RELEVANT_SOURCE_FILES]`. Do not infer, invent, or use external knowledge about other systems unless directly supported by the provided code.

8.  **Conclusion/Summary:** End with a brief summary paragraph reiterating the key architectural takeaways and their significance within the project.

Remember:
- Ground every claim in the provided source files.
- Prioritize architectural clarity and direct representation of the code's functionality.
"""
