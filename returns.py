from __future__ import annotations

from typing import TYPE_CHECKING
from rich.text import Text
from rich.tree import Tree

if TYPE_CHECKING:
    import tree_sitter as ts


class Variable:
    """
    A variable is the smallest unit of dependency.
    Multiple variables may have the same name, but if they refer to different
    items their uuid will be different.
    UUID is created **only** at assignment.
    """
    name: str
    uuid: str | None
    is_reference: bool
    reference: tuple[str, int, int] | None  # filename, lineno, colno
    decl_reference: tuple[str, int, int] | None  # declaration filename, lineno, colno if reference

    def __init__(
        self,
        name: str,
        uuid: str | None,
        is_reference: bool = False,
        reference: tuple[str, int, int] | None = None,
        decl_reference: tuple[str, int, int] | None = None,
    ):
        self.name = name
        self.uuid = uuid
        self.is_reference = is_reference
        self.reference = reference
        self.decl_reference = decl_reference

    def __repr__(self) -> str:
        kind = "reference" if self.is_reference else "declaration"
        return f"Variable(name={self.name!r}, uuid={self.uuid!r}, is_reference={self.is_reference}, ref={self.reference})"

    def display_str(self) -> str:
        if self.is_reference:
            if not self.uuid:
                return f"{self.name} (undefined!)"
            elif self.uuid == "builtin":
                return f"{self.name} (builtin)"
            elif self.uuid.startswith("import:"):
                mod = self.uuid.split(":", 1)[1]
                return f"{self.name} (imported from {mod})"
            else:
                decl_info = f", declared in {self.decl_reference[0]}:{self.decl_reference[1]}" if self.decl_reference else ""
                return f"{self.name} (reference to id={self.uuid}{decl_info})"
        else:
            return f"{self.name} (new assignment, id={self.uuid})"


class DepTree:
    """
    DepTree represents the code flow and dependency chain in non-structural objects.
    Structural objects will have separate classes which contain DepTree objects (Function, Class, and Module).
    """
    name: str | None
    variable: Variable | None
    children: list["DepTree"]
    dependencies: list[Variable]

    def __init__(
        self,
        name: str | None = None,
        children: list["DepTree"] | None = None,
        variable: Variable | None = None,
        dependencies: list[Variable] | None = None,
    ):
        self.name = name
        self.variable = variable
        self.children = children if children is not None else []
        self.dependencies = dependencies if dependencies is not None else []

    def _print(self) -> Tree:
        label = Text()
        if self.name is not None:
            label.append(self.name)
        elif self.variable:
            if not self.variable.is_reference:
                label.append(f"{self.variable.name} (new assignment, id={self.variable.uuid})")
            else:
                label.append(self.variable.display_str())
        else:
            label.append("Node")

        node = Tree(label)
        for dep in self.dependencies:
            if isinstance(dep, Variable):
                node.add(Text(dep.display_str()))
            else:
                node.add(Text(str(dep)))
        for child in self.children:
            node.add(child._print())
        return node


class Function:
    """
    Will treat variables in the signatures as assignments and create uuids in the function for them.
    Flow will contain the body of the function.
    """
    name: str
    signature: str
    flow: DepTree
    uuid: str | None

    def __init__(
        self,
        name: str,
        signature: str,
        flow: DepTree,
        uuid: str | None = None,
    ):
        self.name = name
        self.signature = signature
        self.flow = flow
        self.uuid = uuid


class Class:
    """
    Represents a class containing functions and methods.
    """
    name: str
    functions: list[Function]
    uuid: str | None

    def __init__(
        self,
        name: str,
        functions: list[Function] | None = None,
        uuid: str | None = None,
    ):
        self.name = name
        self.functions = functions if functions is not None else []
        self.uuid = uuid


class Module:
    name: str
    file_path: str
    code_flow: DepTree
    functions: list[Function]
    classes: list[Class]
    variables: dict[str, Variable]
    scope: "Scope | None"

    def __init__(
        self,
        name: str = "",
        file_path: str = "",
        code_flow: DepTree | None = None,
        functions: list[Function] | None = None,
        classes: list[Class] | None = None,
        variables: dict[str, Variable] | None = None,
        scope: "Scope | None" = None,
    ):
        self.name = name
        self.file_path = file_path
        self.code_flow = code_flow if code_flow is not None else DepTree("Module Start")
        self.functions = functions if functions is not None else []
        self.classes = classes if classes is not None else []
        self.variables = variables if variables is not None else {}
        self.scope = scope


_ACTIVE_MODULE: Module | None = None


def start_file(filename: str) -> Module:
    """Parse a file and initialize its dependency tree and symbol tracking."""
    global _ACTIVE_MODULE
    from get_tree import parse_file
    _ACTIVE_MODULE = parse_file(filename)
    return _ACTIVE_MODULE


def get_tree() -> DepTree:
    """Returns the current module's dependency tree."""
    global _ACTIVE_MODULE
    if _ACTIVE_MODULE is not None:
        return _ACTIVE_MODULE.code_flow
    return DepTree("Empty Tree")


def find_tree(uuid: str, tree: DepTree | None = None) -> DepTree | None:
    """
    Recursively search for a tree node matching a given variable UUID
    (either as a declared variable or as a referenced dependency).
    """
    if tree is None:
        tree = get_tree()

    if tree.variable and tree.variable.uuid == uuid:
        return tree

    for dep in tree.dependencies:
        if isinstance(dep, Variable) and dep.uuid == uuid:
            return tree

    for child in tree.children:
        found = find_tree(uuid, child)
        if found is not None:
            return found

    return None


# ---------------------------------------------------------------------------
# JSON-serializable representations
# ---------------------------------------------------------------------------

def _loc(t: tuple | None) -> dict | None:
    if t is None:
        return None
    return {"file": t[0], "line": t[1], "col": t[2]}


def variable_to_dict(var: Variable | None) -> dict | None:
    if var is None:
        return None
    return {
        "name": var.name,
        "uuid": var.uuid,
        "is_reference": var.is_reference,
        "reference": _loc(var.reference),
        "decl_reference": _loc(var.decl_reference),
        "display": var.display_str(),
    }


def deptree_to_dict(tree: DepTree) -> dict:
    return {
        "name": tree.name,
        "variable": variable_to_dict(tree.variable),
        "dependencies": [variable_to_dict(d) for d in tree.dependencies],
        "children": [deptree_to_dict(c) for c in tree.children],
    }


def function_to_dict(fn: Function) -> dict:
    return {
        "name": fn.name,
        "signature": fn.signature,
        "uuid": fn.uuid,
        "flow": deptree_to_dict(fn.flow),
    }


def class_to_dict(cls: Class) -> dict:
    return {
        "name": cls.name,
        "uuid": cls.uuid,
        "functions": [function_to_dict(f) for f in cls.functions],
    }


def scope_to_dict(scope) -> dict:
    """Serialise a `Scope` (from get_tree) into a plain dict tree."""
    return {
        "name": scope.name,
        "symbols": {
            name: variable_to_dict(var)
            for name, var in scope.symbols.items()
        },
        "imports": dict(scope.imports),
        "functions": dict(scope.functions),
        "children": {
            name: scope_to_dict(child)
            for name, child in scope.children.items()
        },
    }


def module_to_dict(module: Module) -> dict:
    return {
        "name": module.name,
        "file_path": module.file_path,
        "code_flow": deptree_to_dict(module.code_flow),
        "functions": [function_to_dict(f) for f in module.functions],
        "classes": [class_to_dict(c) for c in module.classes],
        "variables": {
            name: variable_to_dict(var)
            for name, var in module.variables.items()
        },
        "scopes": scope_to_dict(module.scope) if module.scope else None,
    }
