from __future__ import annotations

from pathlib import Path
from typing import Any


class SymbolType:
    VARIABLE = 0
    CLASS = 1
    FUNCTION = 3


class Symbol:
    name: str
    type: int

    def __init__(self, name: str, type_: int):
        self.name = name
        self.type = type_


class FunctionSymPtr:
    function_name: str
    symbols: list

    def __init__(self, name: str):
        self.function_name = name
        self.symbols = []


class ClassSymPtr:
    class_name: str
    functions: list[FunctionSymPtr]

    def __init__(self, name: str):
        self.class_name = name
        self.functions = []


class ModuleSymPtr:
    module_name: str
    symbols: list[Symbol]
    functions: list[FunctionSymPtr]
    classes: list[ClassSymPtr]

    def __init__(self, name: str):
        self.module_name = name
        self.symbols = []
        self.functions = []
        self.classes = []


class GlobalIndex:
    """
    Global repository of parsed modules, their symbol tables, and declared variables.
    Provides cross-file symbol resolution for imports (e.g., from a import daddy).
    """

    def __init__(self):
        self.modules: dict[str, Any] = {}
        self.declarations_by_uuid: dict[str, Any] = {}
        self.search_paths: list[Path] = [Path(".")]

    def add_search_path(self, path: Path | str):
        p = Path(path).resolve()
        if p not in self.search_paths:
            self.search_paths.append(p)

    def register_module(self, name: str, module_or_parser: Any):
        self.modules[name] = module_or_parser

    def register_declaration(self, variable: Any):
        if getattr(variable, "uuid", None):
            self.declarations_by_uuid[variable.uuid] = variable

    def get_declaration(self, uuid: str) -> Any | None:
        return self.declarations_by_uuid.get(uuid)

    def find_module_file(self, mod_name: str, relative_to: Path | None = None) -> Path | None:
        candidates = []
        if relative_to is not None:
            rel_dir = relative_to if relative_to.is_dir() else relative_to.parent
            candidates.append(rel_dir / f"{mod_name}.py")
            candidates.append(rel_dir / mod_name / "__init__.py")

        for sp in self.search_paths:
            candidates.append(sp / f"{mod_name}.py")
            candidates.append(sp / mod_name / "__init__.py")

        for c in candidates:
            if c.exists() and c.is_file():
                return c.resolve()
        return None

    def resolve_import(
        self, from_module: str, symbol_name: str, relative_to: Path | None = None
    ) -> Any | None:
        """
        Resolves a symbol imported from another module (e.g. from a import daddy).
        If the module is not yet parsed, finds and parses it.
        Returns the declared Variable object or None if not found.
        """
        mod = self.modules.get(from_module)
        if mod is None:
            file_path = self.find_module_file(from_module, relative_to=relative_to)
            if file_path is not None:
                from get_tree import parse_file
                mod = parse_file(str(file_path), global_index=self, verbose=False)
                self.modules[from_module] = mod

        if mod is not None:
            # Check module's variables dictionary
            if hasattr(mod, "variables") and symbol_name in mod.variables:
                return mod.variables[symbol_name]
            # Check if mod has a scope
            if hasattr(mod, "scope") and symbol_name in mod.scope.symbols:
                return mod.scope.symbols[symbol_name]
            # Check module parser scope
            if hasattr(mod, "parser") and hasattr(mod.parser, "scope"):
                if symbol_name in mod.parser.scope.symbols:
                    return mod.parser.scope.symbols[symbol_name]

        return None


DEFAULT_INDEX = GlobalIndex()


class WorkingTree:
    def __init__(self):
        self.index = DEFAULT_INDEX
