from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from rich.console import Console
from rich.table import Table

from returns import DepTree, Module, Variable


@dataclass
class DependencyInfo:
    """
    A single symbol occurrence found in a selected line range, together with the
    declaration it resolves to.

    Fields:
        scope_name:  lexical scope in which the occurrence lives
                     (module name, function name, or class name).
        name:        the name of the symbol **as used in that scope**
                     (aliases and parameter names are preserved).
        uuid:        unique id of the dependent symbol; None when unresolved,
                     "builtin" for builtins, "import:<mod>" for imports.
        file:        the source file under analysis.
        use_file:    file where the occurrence appears (same as `file` except
                     when walking a tree that spans modules).
        use_lineno:  line number of the occurrence (inclusive, 1-based).
        use_colno:   column of the occurrence.
        decl_file:   file where the symbol is declared (None if undefined/builtin/import).
        decl_lineno: line number of the declaration.
        decl_colno:  column of the declaration.
        kind:        one of "declaration" | "reference" | "builtin" | "import" | "undefined".
    """

    scope_name: str
    name: str
    uuid: str | None
    file: str = ""
    use_file: str | None = None
    use_lineno: int | None = None
    use_colno: int | None = None
    decl_file: str | None = None
    decl_lineno: int | None = None
    decl_colno: int | None = None
    kind: str = "reference"

    def to_dict(self) -> dict:
        """Return a plain JSON-serializable representation of this record."""
        return {
            "scope_name": self.scope_name,
            "name": self.name,
            "uuid": self.uuid,
            "file": self.file,
            "use": (
                {"file": self.use_file, "line": self.use_lineno, "col": self.use_colno}
                if self.use_lineno is not None
                else None
            ),
            "declared": (
                {
                    "file": self.decl_file,
                    "line": self.decl_lineno,
                    "col": self.decl_colno,
                }
                if self.decl_lineno is not None
                else None
            ),
            "kind": self.kind,
        }


def iter_references(
    tree: DepTree, scope: str = "module"
) -> Iterable[tuple[str, Variable]]:
    """Yield (scope, variable) for every symbol occurrence stored in a DepTree.

    The `scope` starts at the module level and narrows to the enclosing
    function/class name whenever the walker descends into a defined
    function or class node. A function's parameters belong to the function
    scope, while the function/class binding itself belongs to its enclosing
    scope.
    """
    node_name = tree.name or ""
    if node_name.startswith("def "):
        child_scope = node_name[4:].split("(")[0].strip()
    elif node_name.startswith("class "):
        child_scope = node_name[len("class "):].split(" (")[0].strip()
    else:
        child_scope = scope

    if tree.variable is not None:
        yield scope, tree.variable

    if node_name.startswith("def "):
        # Parameters are the direct dependencies on a `def` node.
        for dep in tree.dependencies:
            yield child_scope, dep
    else:
        for dep in tree.dependencies:
            yield scope, dep

    for child in tree.children:
        yield from iter_references(child, child_scope)


def _parse_quietly(file_path: str) -> Module:
    from get_tree import parse_file

    return parse_file(file_path, verbose=False)


def _to_info(scope: str, var: Variable, file: str) -> DependencyInfo:
    use_file = var.reference[0] if var.reference else None
    use_lineno = var.reference[1] if var.reference else None
    use_colno = var.reference[2] if var.reference else None
    decl_file = var.decl_reference[0] if var.decl_reference else None
    decl_lineno = var.decl_reference[1] if var.decl_reference else None
    decl_colno = var.decl_reference[2] if var.decl_reference else None

    if not var.is_reference:
        # A declaration stores its own location in `reference`.
        decl_file = use_file
        decl_lineno = use_lineno
        decl_colno = use_colno
        use_file = None
        use_lineno = None
        use_colno = None
        kind = "declaration"
    elif var.uuid is None:
        kind = "undefined"
    elif var.uuid == "builtin":
        kind = "builtin"
    elif var.uuid.startswith("import:"):
        kind = "import"
    else:
        kind = "reference"

    return DependencyInfo(
        scope_name=scope,
        name=var.name,
        uuid=var.uuid,
        file=file,
        use_file=use_file,
        use_lineno=use_lineno,
        use_colno=use_colno,
        decl_file=decl_file,
        decl_lineno=decl_lineno,
        decl_colno=decl_colno,
        kind=kind,
    )


def dependencies_for_lines(
    source: Module | DepTree | str,
    start_line: int,
    end_line: int | None = None,
    *,
    include_declarations: bool = False,
) -> list[DependencyInfo]:
    """
    Given a line range (1-based, inclusive) in a parsed module, dependency tree,
    or Python source file, return every symbol occurrence in that range together
    with the declaration (lineno, colno, uuid) it resolves to.

    Args:
        source: a parsed `Module`, a `DepTree`, or a path to a Python file
                (parsed on demand).
        start_line: first line to inspect (inclusive).
        end_line:   last line to inspect (inclusive); defaults to `start_line`.
        include_declarations: when True, also include symbols *defined* in the
                              range (otherwise only references are reported).

    Returns:
        A list of `DependencyInfo`, sorted by usage location.
    """
    if isinstance(source, Module):
        tree: DepTree = source.code_flow
        file_path: str = source.file_path
    elif isinstance(source, DepTree):
        tree = source
        file_path = ""
    else:
        module = _parse_quietly(source)
        tree = module.code_flow
        file_path = module.file_path

    end = end_line if end_line is not None else start_line

    records: list[DependencyInfo] = []
    for scope, var in iter_references(tree):
        loc = var.reference
        if loc is None:
            continue
        if not (start_line <= loc[1] <= end):
            continue
        if var.is_reference or include_declarations:
            records.append(_to_info(scope, var, file_path))

    records.sort(key=lambda r: (r.use_lineno or 0, r.use_colno or 0))
    return records


def visualize_dependencies(
    source: Module | DepTree | str,
    start_line: int,
    end_line: int | None = None,
    *,
    include_declarations: bool = False,
) -> None:
    """
    Print a `rich` table of the dependencies found in the given line range.

    Each row shows the name of the symbol as used in that scope, the UUID of the
    dependent symbol, where it was used, and the line/col where it is declared.
    """
    records = dependencies_for_lines(
        source, start_line, end_line, include_declarations=include_declarations
    )

    label = (
        f"Line dependencies: {start_line}"
        if end_line is None
        else f"Line dependencies: {start_line}-{end_line}"
    )
    table = Table(title=label, title_style="bold")
    table.add_column("Scope", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Kind")
    table.add_column("Used at", style="yellow")
    table.add_column("Declared at", style="magenta")
    table.add_column("UUID", style="dim", overflow="fold")

    for r in records:
        used = (
            f"{r.use_file}:{r.use_lineno}:{r.use_colno}"
            if r.use_lineno is not None
            else ""
        )
        declared = (
            f"{r.decl_file}:{r.decl_lineno}:{r.decl_colno}"
            if r.decl_lineno is not None
            else ""
        )
        table.add_row(r.scope_name, r.name, r.kind, used, declared, r.uuid or "")

    Console().print(table)