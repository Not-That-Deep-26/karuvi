from __future__ import annotations

import builtins
import uuid
from argparse import ArgumentParser
from pathlib import Path

import tree_sitter as ts
import tree_sitter_python as tspython
from rich import print
from rich.text import Text
from rich.tree import Tree
from tree_sitter import Language, Parser

from pointers import DEFAULT_INDEX, GlobalIndex, Symbol, SymbolType
from returns import Class, DepTree, Function, Module, Variable

BUILTINS = set(dir(builtins))


class Scope:
    """Tracks variables, imports, and functions within a lexical scope."""

    def __init__(
        self,
        name: str = "module",
        parent: Scope | None = None,
        global_index: GlobalIndex | None = None,
    ):
        self.name = name
        self.parent = parent
        self.global_index = global_index
        self.symbols: dict[str, Variable] = {}
        self.imports: dict[str, str] = {}
        self.functions: dict[str, str] = {}
        self.children: dict[str, Scope] = {}
        if parent is not None:
            parent.children[name] = self

    def add_import(self, name: str, module: str):
        self.imports[name] = module

    def assign_variable(
        self, name: str, node: ts.Node | None = None, filename: str = ""
    ) -> Variable:
        """
        Creates a new declared variable at assignment with a unique UUID.
        UUID is created ONLY at assignment.
        """
        var_uuid = str(uuid.uuid4())
        ref = (filename, node.start_point[0] + 1, node.start_point[1]) if node else None
        var = Variable(name=name, uuid=var_uuid, is_reference=False, reference=ref)
        self.symbols[name] = var
        if self.global_index:
            self.global_index.register_declaration(var)
        return var

    def add_import_symbol(
        self,
        name: str,
        from_module: str,
        target_var: Variable | None = None,
        node: ts.Node | None = None,
        filename: str = "",
    ) -> Variable:
        """
        Registers an imported variable in this scope.
        If the variable was resolved from another module (e.g. daddy in a.py),
        it reuses the declaration's UUID with is_reference=True.
        """
        self.imports[name] = from_module
        ref = (filename, node.start_point[0] + 1, node.start_point[1]) if node else None

        if target_var is not None and target_var.uuid:
            var = Variable(
                name=name,
                uuid=target_var.uuid,
                is_reference=True,
                reference=ref,
                decl_reference=target_var.reference,
            )
        else:
            var = Variable(
                name=name,
                uuid=f"import:{from_module}",
                is_reference=True,
                reference=ref,
            )

        self.symbols[name] = var
        return var

    def resolve_variable(
        self, name: str, node: ts.Node | None = None, filename: str = ""
    ) -> Variable:
        """
        Resolves a referenced variable name to a Variable instance (with is_reference=True).
        Reuses the UUID of the declaration or import that it resolves to.
        """
        ref = (filename, node.start_point[0] + 1, node.start_point[1]) if node else None

        if name in self.symbols:
            target = self.symbols[name]
            decl_ref = target.decl_reference if target.is_reference else target.reference
            return Variable(
                name=name,
                uuid=target.uuid,
                is_reference=True,
                reference=ref,
                decl_reference=decl_ref,
            )

        if self.parent:
            return self.parent.resolve_variable(name, node, filename)

        if name in self.imports:
            mod_name = self.imports[name]
            return Variable(
                name=name,
                uuid=f"import:{mod_name}",
                is_reference=True,
                reference=ref,
            )

        if name in BUILTINS:
            return Variable(name=name, uuid="builtin", is_reference=True, reference=ref)

        # Undefined variable reference
        return Variable(name=name, uuid=None, is_reference=True, reference=ref)

    def resolve_attribute_variable(
        self, node: ts.Node, filename: str = ""
    ) -> Variable:
        """
        Resolves attribute access expressions such as a.daddy or socket.AF_INET.
        """
        full_text = node.text.decode()
        ref = (filename, node.start_point[0] + 1, node.start_point[1])

        root_node = node
        attr_chain: list[str] = []
        while root_node.type == "attribute":
            attr = root_node.child_by_field_name("attribute")
            if attr:
                attr_chain.append(attr.text.decode())
            obj = root_node.child_by_field_name("object")
            if obj is None:
                break
            root_node = obj

        if root_node and root_node.type == "identifier":
            root_name = root_node.text.decode()
            attr_chain.reverse()

            # Check if root is an imported module
            if root_name in self.imports:
                mod_name = self.imports[root_name]
                if self.global_index and attr_chain:
                    target_var = self.global_index.resolve_import(mod_name, attr_chain[0])
                    if target_var:
                        return Variable(
                            name=full_text,
                            uuid=target_var.uuid,
                            is_reference=True,
                            reference=ref,
                            decl_reference=target_var.reference,
                        )
                return Variable(
                    name=full_text,
                    uuid=f"import:{mod_name}",
                    is_reference=True,
                    reference=ref,
                )

            # Check if root is defined in scope
            if root_name in self.symbols:
                target = self.symbols[root_name]
                decl_ref = target.decl_reference if target.is_reference else target.reference
                return Variable(
                    name=full_text,
                    uuid=target.uuid,
                    is_reference=True,
                    reference=ref,
                    decl_reference=decl_ref,
                )

            if root_name in BUILTINS:
                return Variable(name=full_text, uuid="builtin", is_reference=True, reference=ref)

        return Variable(name=full_text, uuid=None, is_reference=True, reference=ref)

    def resolve(self, name: str) -> tuple[str, str | None]:
        """Backward-compatibility resolution method."""
        var = self.resolve_variable(name)
        if var.uuid is None:
            return ("undefined", None)
        elif var.uuid == "builtin":
            return ("builtin", None)
        elif var.uuid.startswith("import:"):
            return ("import", var.uuid.split(":", 1)[1])
        else:
            return ("symbol", var.uuid)

    def _print(self) -> Tree:
        """Render the scope and its contents as a rich Tree."""
        node = Tree(f"Scope: {self.name}")
        for name, var in self.symbols.items():
            node.add(Text(f"symbol: {name} -> {var.display_str()}"))
        for name, mod in self.imports.items():
            node.add(Text(f"import: {name} -> {mod}"))
        for name, fn_uuid in self.functions.items():
            node.add(Text(f"function: {name} (id={fn_uuid})"))
        for _, child in self.children.items():
            node.add(child._print())
        return node


def format_reference(name: str, scope: Scope) -> str:
    var = scope.resolve_variable(name)
    return var.display_str()


def format_attribute_reference(node: ts.Node, scope: Scope, filename: str = "") -> str:
    var = scope.resolve_attribute_variable(node, filename=filename)
    return var.display_str()


def extract_targets(node: ts.Node | None) -> list[tuple[str, ts.Node]]:
    """Recursively extract target variable identifiers from LHS of assignment."""
    if node is None:
        return []
    if node.type == "identifier":
        return [(node.text.decode(), node)]
    elif node.type in ("pattern_list", "tuple_pattern", "list_pattern"):
        targets = []
        for child in node.named_children:
            targets.extend(extract_targets(child))
        return targets
    elif node.type == "attribute":
        return [(node.text.decode(), node)]
    return []


def extract_param_name(param_node: ts.Node) -> str:
    if param_node.type == "identifier":
        return param_node.text.decode()
    elif param_node.type == "typed_parameter":
        return param_node.named_children[0].text.decode()
    elif param_node.type == "default_parameter":
        name_node = param_node.child_by_field_name("name")
        return name_node.text.decode() if name_node else param_node.named_children[0].text.decode()
    elif param_node.type == "typed_default_parameter":
        first = param_node.named_children[0]
        if first.type == "identifier":
            return first.text.decode()
        elif first.type == "typed_parameter":
            return first.named_children[0].text.decode()
    return param_node.text.decode()


def parse_call_node(node: ts.Node, scope: Scope, filename: str = "") -> DepTree:
    func_node = node.child_by_field_name("function")
    args_node = node.child_by_field_name("arguments")
    func_name = func_node.text.decode() if func_node else "anonymous"
    call_tree = DepTree(f"{func_name} (call)")

    if args_node:
        for child in args_node.named_children:
            if child.type == "identifier":
                var = scope.resolve_variable(child.text.decode(), node=child, filename=filename)
                call_tree.dependencies.append(var)
            elif child.type == "attribute":
                var = scope.resolve_attribute_variable(child, filename=filename)
                call_tree.dependencies.append(var)
            elif child.type == "call":
                sub_call = parse_call_node(child, scope, filename=filename)
                call_tree.children.append(sub_call)
            elif child.type == "keyword_argument":
                key = child.child_by_field_name("name")
                val = child.child_by_field_name("value")
                key_name = key.text.decode() if key else ""
                if val and val.type == "identifier":
                    var = scope.resolve_variable(val.text.decode(), node=val, filename=filename)
                    kw_var = Variable(
                        name=f"{key_name}={var.name}",
                        uuid=var.uuid,
                        is_reference=True,
                        reference=var.reference,
                        decl_reference=var.decl_reference,
                    )
                    call_tree.dependencies.append(kw_var)
                elif val and val.type == "attribute":
                    var = scope.resolve_attribute_variable(val, filename=filename)
                    kw_var = Variable(
                        name=f"{key_name}={var.name}",
                        uuid=var.uuid,
                        is_reference=True,
                        reference=var.reference,
                        decl_reference=var.decl_reference,
                    )
                    call_tree.dependencies.append(kw_var)
                elif val and val.type == "call":
                    sub_call = parse_call_node(val, scope, filename=filename)
                    sub_call.name = f"{key_name}={sub_call.name}"
                    call_tree.children.append(sub_call)
                elif val:
                    kw_var = Variable(
                        name=f"{key_name}={val.text.decode()}",
                        uuid=None,
                        is_reference=True,
                    )
                    call_tree.dependencies.append(kw_var)
            elif child.type == "comment":
                continue
            else:
                sub_expr = parse_expression_tree(child, scope, filename=filename)
                if sub_expr.dependencies or sub_expr.children:
                    if not sub_expr.children and len(sub_expr.dependencies) == 1:
                        call_tree.dependencies.extend(sub_expr.dependencies)
                    else:
                        call_tree.children.append(sub_expr)
    return call_tree


def collect_expression_deps(
    node: ts.Node, scope: Scope, parent: DepTree, filename: str = ""
):
    """Recursively traverses an expression and collects Variable dependencies and nested calls."""
    if node.type == "identifier":
        var = scope.resolve_variable(node.text.decode(), node=node, filename=filename)
        parent.dependencies.append(var)
    elif node.type == "attribute":
        var = scope.resolve_attribute_variable(node, filename=filename)
        parent.dependencies.append(var)
    elif node.type == "call":
        parent.children.append(parse_call_node(node, scope, filename=filename))
    elif node.type in (
        "binary_operator",
        "boolean_operator",
        "comparison_operator",
        "unary_operator",
        "parenthesized_expression",
        "tuple",
        "list",
        "set",
        "subscript",
        "argument_list",
        "pair",
        "dictionary",
    ):
        for child in node.named_children:
            collect_expression_deps(child, scope, parent, filename=filename)
    elif node.type in ("integer", "float", "string", "true", "false", "none", "comment"):
        pass
    else:
        for child in node.named_children:
            collect_expression_deps(child, scope, parent, filename=filename)


def parse_expression_tree(
    node: ts.Node, scope: Scope, filename: str = ""
) -> DepTree:
    """
    Parses an expression node into a DepTree.
    If the node is a call, returns the call tree directly.
    Otherwise, returns a DepTree('Node') containing leaf Variable dependencies and child subtrees.
    """
    if node.type == "call":
        return parse_call_node(node, scope, filename=filename)
    expr_tree = DepTree("Node")
    collect_expression_deps(node, scope, expr_tree, filename=filename)
    return expr_tree


def clone_deptree(tree: DepTree) -> DepTree:
    """Deep clone a DepTree instance."""
    cloned = DepTree(name=tree.name, variable=tree.variable)
    cloned.dependencies = list(tree.dependencies)
    cloned.children = [clone_deptree(c) for c in tree.children]
    return cloned


def parse_decorator(node: ts.Node, scope: Scope, filename: str = "") -> DepTree:
    dec_text = node.text.decode()
    dec_tree = DepTree(f"{dec_text} (decorator)")
    for child in node.named_children:
        collect_expression_deps(child, scope, dec_tree, filename=filename)
    return dec_tree


class ModuleParser:
    mod_name: str
    file_path: str
    src: bytes
    parser: ts.Parser
    root_deptree: DepTree
    scope: Scope
    global_index: GlobalIndex
    function_objs: list[Function]
    class_objs: list[Class]

    def __init__(
        self,
        filename: str,
        parser: ts.Parser,
        global_index: GlobalIndex | None = None,
    ):
        self.file_path = filename
        self.mod_name = Path(filename).stem if filename else ""
        self.parser = parser
        self.global_index = global_index if global_index is not None else DEFAULT_INDEX
        self.scope = Scope(name=self.mod_name, global_index=self.global_index)
        self.root_deptree = DepTree("Module Start")
        self.src = b""
        self.function_objs = []
        self.class_objs = []

    def parse_import(self, node: ts.Node):
        for child in node.named_children:
            if child.type == "dotted_name":
                mod = child.text.decode()
                self.scope.add_import(mod, mod)
                base_dir = Path(self.file_path).parent if self.file_path else Path(".")
                if self.global_index:
                    self.global_index.resolve_import(mod, "", relative_to=base_dir)
                if getattr(self, "verbose", True):
                    print("importing", mod)
            elif child.type == "aliased_import":
                name = child.child_by_field_name("name")
                alias = child.child_by_field_name("alias")
                mod_name = name.text.decode() if name else ""
                alias_name = alias.text.decode() if alias else mod_name
                self.scope.add_import(alias_name, mod_name)
                base_dir = Path(self.file_path).parent if self.file_path else Path(".")
                if self.global_index:
                    self.global_index.resolve_import(mod_name, "", relative_to=base_dir)
                if getattr(self, "verbose", True):
                    print(f"importing {mod_name} as {alias_name}")

    def parse_import_from(self, node: ts.Node):
        mod_node = node.child_by_field_name("module_name")
        mod_name = mod_node.text.decode() if mod_node else ""
        base_dir = Path(self.file_path).parent if self.file_path else Path(".")

        for child in node.named_children:
            if child == mod_node:
                continue
            if child.type == "dotted_name":
                name = child.text.decode()
                target_var = None
                if self.global_index:
                    target_var = self.global_index.resolve_import(
                        mod_name, name, relative_to=base_dir
                    )
                self.scope.add_import_symbol(
                    name,
                    mod_name,
                    target_var=target_var,
                    node=child,
                    filename=self.file_path,
                )
                if getattr(self, "verbose", True):
                    print(f"importing {name} from {mod_name}")
            elif child.type == "aliased_import":
                name = child.child_by_field_name("name")
                alias = child.child_by_field_name("alias")
                sym_name = name.text.decode() if name else ""
                alias_name = alias.text.decode() if alias else sym_name
                target_var = None
                if self.global_index:
                    target_var = self.global_index.resolve_import(
                        mod_name, sym_name, relative_to=base_dir
                    )
                self.scope.add_import_symbol(
                    alias_name,
                    mod_name,
                    target_var=target_var,
                    node=alias or child,
                    filename=self.file_path,
                )
                if getattr(self, "verbose", True):
                    print(f"importing {sym_name} as {alias_name} from {mod_name}")

    def parse_assignment(self, expr: ts.Node) -> DepTree:
        stmt_node = DepTree("Node")
        left_node = expr.child_by_field_name("left")
        right_node = expr.child_by_field_name("right")
        targets = extract_targets(left_node)

        # Evaluate RHS dependencies in current scope
        rhs_tree = (
            parse_expression_tree(right_node, self.scope, filename=self.file_path)
            if right_node
            else DepTree("Node")
        )

        # For each target, assign a new UUID (is_reference=False) and attach dependencies
        for target_name, target_n in targets:
            var = self.scope.assign_variable(
                target_name, node=target_n, filename=self.file_path
            )
            target_tree = DepTree(
                name=f"{target_name} (new assignment, id={var.uuid})",
                variable=var,
            )
            target_tree.children.append(clone_deptree(rhs_tree))
            stmt_node.children.append(target_tree)

        return stmt_node

    def parse_augmented_assignment(self, expr: ts.Node) -> DepTree:
        stmt_node = DepTree("Node")
        left_node = expr.child_by_field_name("left")
        right_node = expr.child_by_field_name("right")
        operator_node = expr.children[1] if len(expr.children) > 1 else None
        op_text = operator_node.text.decode() if operator_node else "*="

        target_name = left_node.text.decode() if left_node else ""

        # Dependency 1: target itself (before mutation, as a reference)
        target_dep = self.scope.resolve_variable(
            target_name, node=left_node, filename=self.file_path
        )

        # Dependency 2: RHS operand(s)
        rhs_tree = (
            parse_expression_tree(right_node, self.scope, filename=self.file_path)
            if right_node
            else DepTree("Node")
        )

        # Assign new UUID to target after evaluating inputs
        var = self.scope.assign_variable(target_name, node=left_node, filename=self.file_path)
        rhs_text = right_node.text.decode() if right_node else ""
        aug_tree = DepTree(
            name=f"{target_name} {op_text} {rhs_text} (new assignment, id={var.uuid})",
            variable=var,
        )
        aug_tree.dependencies.append(target_dep)

        if rhs_tree.name == "Node":
            aug_tree.dependencies.extend(rhs_tree.dependencies)
            aug_tree.children.extend(rhs_tree.children)
        else:
            aug_tree.children.append(rhs_tree)

        stmt_node.children.append(aug_tree)
        return stmt_node

    def parse_function_definition(
        self, node: ts.Node, scope: Scope | None = None
    ) -> DepTree:
        stmt_node = DepTree("Node")
        fn_name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        body_node = node.child_by_field_name("body")

        scope = scope if scope is not None else self.scope
        fn_name = fn_name_node.text.decode() if fn_name_node else "anonymous"
        fn_var = scope.assign_variable(fn_name, node=fn_name_node, filename=self.file_path)
        scope.functions[fn_name] = fn_var.uuid

        fn_scope = Scope(
            name=fn_name, parent=scope, global_index=self.global_index
        )
        param_names = []
        param_vars: list[Variable] = []
        if params_node:
            for p in params_node.named_children:
                p_name = extract_param_name(p)
                var = fn_scope.assign_variable(p_name, node=p, filename=self.file_path)
                param_names.append(p_name)
                param_vars.append(var)
                if p.type in ("default_parameter", "typed_default_parameter"):
                    default_node = p.child_by_field_name("value")
                    if default_node and default_node.type == "call":
                        fn_tree_defaults = parse_call_node(
                            default_node, fn_scope, filename=self.file_path
                        )
                        param_vars.append(fn_tree_defaults)
                    elif default_node:
                        default_tree = parse_expression_tree(
                            default_node, fn_scope, filename=self.file_path
                        )
                        param_vars.append(default_tree)

        fn_tree = DepTree(
            name=f"def {fn_name}({', '.join(param_names)}) (id={fn_var.uuid})",
            variable=fn_var,
        )
        for p_var in param_vars:
            if isinstance(p_var, Variable):
                fn_tree.dependencies.append(p_var)
            else:
                fn_tree.children.append(p_var)

        # Parse body statements in fn_scope
        if body_node:
            for stmt in body_node.named_children:
                parsed_stmt = self._parse_statement_in_scope(stmt, fn_scope)
                if parsed_stmt:
                    fn_tree.children.append(parsed_stmt)

        fn_obj = Function(
            name=fn_name,
            signature=f"({', '.join(param_names)})",
            flow=fn_tree,
            uuid=fn_var.uuid,
            line=fn_var.reference[1] if fn_var.reference else None,
        )
        self.function_objs.append(fn_obj)

        stmt_node.children.append(fn_tree)
        return stmt_node

    def parse_decorated_definition(
        self, node: ts.Node, scope: Scope | None = None
    ) -> DepTree:
        stmt_node = DepTree("Node")
        inner_tree: DepTree | None = None
        decorators: list[DepTree] = []

        scope = scope if scope is not None else self.scope

        for child in node.named_children:
            if child.type == "decorator":
                decorators.append(parse_decorator(child, scope, filename=self.file_path))
            elif child.type == "function_definition":
                fn_wrapper = self.parse_function_definition(child, scope=scope)
                inner_tree = fn_wrapper.children[0] if fn_wrapper.children else fn_wrapper
            elif child.type == "class_definition":
                cls_wrapper = self.parse_class_definition(child, scope=scope)
                inner_tree = cls_wrapper.children[0] if cls_wrapper.children else cls_wrapper

        if inner_tree:
            for dec in decorators:
                inner_tree.children.insert(0, dec)
            stmt_node.children.append(inner_tree)
        else:
            for dec in decorators:
                stmt_node.children.append(dec)

        return stmt_node

    def parse_class_definition(
        self, node: ts.Node, scope: Scope | None = None
    ) -> DepTree:
        stmt_node = DepTree("Node")
        cls_name_node = node.child_by_field_name("name")
        body_node = node.child_by_field_name("body")
        scope = scope if scope is not None else self.scope
        cls_name = cls_name_node.text.decode() if cls_name_node else "anonymous"
        cls_var = scope.assign_variable(cls_name, node=cls_name_node, filename=self.file_path)

        cls_tree = DepTree(
            name=f"class {cls_name} (id={cls_var.uuid})",
            variable=cls_var,
        )
        cls_scope = Scope(
            name=cls_name, parent=scope, global_index=self.global_index
        )

        cls_functions: list[Function] = []
        if body_node:
            for stmt in body_node.named_children:
                if stmt.type == "function_definition":
                    fn_stmt = self.parse_function_definition(stmt, scope=cls_scope)
                    if fn_stmt and fn_stmt.children:
                        cls_tree.children.append(fn_stmt)
                        fn_name_node = stmt.child_by_field_name("name")
                        fn_name = fn_name_node.text.decode() if fn_name_node else ""
                        for func in self.function_objs:
                            if func.name == fn_name:
                                cls_functions.append(func)
                elif stmt.type == "decorated_definition":
                    dec_stmt = self.parse_decorated_definition(stmt, scope=cls_scope)
                    if dec_stmt and dec_stmt.children:
                        cls_tree.children.append(dec_stmt)
                        fn_node = stmt.child_by_field_name("definition")
                        fn_name_node = (
                            fn_node.child_by_field_name("name") if fn_node else None
                        )
                        fn_name = fn_name_node.text.decode() if fn_name_node else ""
                        for func in self.function_objs:
                            if func.name == fn_name:
                                cls_functions.append(func)
                else:
                    parsed_stmt = self._parse_statement_in_scope(stmt, cls_scope)
                    if parsed_stmt:
                        cls_tree.children.append(parsed_stmt)

        cls_obj = Class(name=cls_name, functions=cls_functions, uuid=cls_var.uuid, line=cls_var.reference[1] if cls_var.reference else None)
        self.class_objs.append(cls_obj)

        stmt_node.children.append(cls_tree)
        return stmt_node

    def _parse_statement_in_scope(self, node: ts.Node, scope: Scope) -> DepTree | None:
        if node.type == "expression_statement":
            expr = node.named_children[0] if node.named_children else None
            if not expr:
                return None
            if expr.type == "assignment":
                left_node = expr.child_by_field_name("left")
                right_node = expr.child_by_field_name("right")
                targets = extract_targets(left_node)
                rhs_tree = (
                    parse_expression_tree(right_node, scope, filename=self.file_path)
                    if right_node
                    else DepTree("Node")
                )
                stmt_node = DepTree("Node")
                for target_name, target_n in targets:
                    var = scope.assign_variable(
                        target_name, node=target_n, filename=self.file_path
                    )
                    target_tree = DepTree(
                        name=f"{target_name} (new assignment, id={var.uuid})",
                        variable=var,
                    )
                    target_tree.children.append(clone_deptree(rhs_tree))
                    stmt_node.children.append(target_tree)
                return stmt_node
            elif expr.type == "call":
                call_tree = parse_call_node(expr, scope, filename=self.file_path)
                stmt_node = DepTree("Node")
                stmt_node.children.append(call_tree)
                return stmt_node
            elif expr.type == "augmented_assignment":
                left_node = expr.child_by_field_name("left")
                right_node = expr.child_by_field_name("right")
                operator_node = expr.children[1] if len(expr.children) > 1 else None
                op_text = operator_node.text.decode() if operator_node else "*="
                target_name = left_node.text.decode() if left_node else ""
                target_dep = scope.resolve_variable(
                    target_name, node=left_node, filename=self.file_path
                )
                rhs_tree = (
                    parse_expression_tree(right_node, scope, filename=self.file_path)
                    if right_node
                    else DepTree("Node")
                )
                var = scope.assign_variable(target_name, node=left_node, filename=self.file_path)
                rhs_text = right_node.text.decode() if right_node else ""
                aug_tree = DepTree(
                    name=f"{target_name} {op_text} {rhs_text} (new assignment, id={var.uuid})",
                    variable=var,
                )
                aug_tree.dependencies.append(target_dep)
                if rhs_tree.name == "Node":
                    aug_tree.dependencies.extend(rhs_tree.dependencies)
                    aug_tree.children.extend(rhs_tree.children)
                else:
                    aug_tree.children.append(rhs_tree)
                stmt_node = DepTree("Node")
                stmt_node.children.append(aug_tree)
                return stmt_node
            else:
                sub_tree = parse_expression_tree(expr, scope, filename=self.file_path)
                if sub_tree.dependencies or sub_tree.children:
                    stmt_node = DepTree("Node")
                    stmt_node.children.append(sub_tree)
                    return stmt_node
        elif node.type == "return_statement":
            ret_tree = DepTree("return")
            for child in node.named_children:
                collect_expression_deps(child, scope, ret_tree, filename=self.file_path)
            stmt_node = DepTree("Node")
            stmt_node.children.append(ret_tree)
            return stmt_node
        elif node.type == "function_definition":
            fn_stmt = self.parse_function_definition(node, scope=scope)
            if fn_stmt and fn_stmt.children:
                stmt_node = DepTree("Node")
                stmt_node.children.append(fn_stmt)
                return stmt_node
        return None

    def parse_expression_statement(self, node: ts.Node) -> DepTree | None:
        expr = node.named_children[0] if node.named_children else None
        if not expr:
            return None

        if expr.type == "assignment":
            return self.parse_assignment(expr)
        elif expr.type == "augmented_assignment":
            return self.parse_augmented_assignment(expr)
        elif expr.type == "call":
            call_tree = parse_call_node(expr, self.scope, filename=self.file_path)
            stmt_node = DepTree("Node")
            stmt_node.children.append(call_tree)
            return stmt_node
        else:
            sub_tree = parse_expression_tree(expr, self.scope, filename=self.file_path)
            if sub_tree.dependencies or sub_tree.children:
                stmt_node = DepTree("Node")
                stmt_node.children.append(sub_tree)
                return stmt_node
            return None

    def parse(self, verbose: bool = True):
        self.verbose = verbose
        self.tree = self.parser.parse(self.src)
        self.root_deptree = DepTree("Module Start")

        # Iterate directly over root_node children to guarantee no statements are skipped
        for child in self.tree.root_node.children:
            if child.type == "comment":
                continue
            elif child.type == "import_statement":
                self.parse_import(child)
            elif child.type == "import_from_statement":
                self.parse_import_from(child)
            elif child.type == "function_definition":
                fn_stmt = self.parse_function_definition(child)
                self.root_deptree.children.append(fn_stmt)
            elif child.type == "class_definition":
                cls_stmt = self.parse_class_definition(child)
                self.root_deptree.children.append(cls_stmt)
            elif child.type == "decorated_definition":
                dec_stmt = self.parse_decorated_definition(child)
                self.root_deptree.children.append(dec_stmt)
            elif child.type == "expression_statement":
                stmt_node = self.parse_expression_statement(child)
                if stmt_node and (stmt_node.children or stmt_node.dependencies):
                    self.root_deptree.children.append(stmt_node)
            else:
                if getattr(self, "verbose", True):
                    print(f"[red]unknown top-level statement:[/red] {child.type}")

        if self.global_index:
            self.global_index.register_module(self.mod_name, self)

        if not self.verbose:
            return

        print("Parsing complete")
        print(self.root_deptree._print())

        print("\nClasses:")
        if self.class_objs:
            for cls in self.class_objs:
                print(f"  class {cls.name} (id={cls.uuid})")
                for func in cls.functions:
                    print(f"    def {func.name}{func.signature} (id={func.uuid})")
        else:
            print("  (none)")

        print("\nFunctions:")
        if self.function_objs:
            for func in self.function_objs:
                print(f"  def {func.name}{func.signature} (id={func.uuid})")
        else:
            print("  (none)")

        print("\nScopes:")
        print(self.scope._print())


def parse_file(
    file_path: str, global_index: GlobalIndex | None = None, verbose: bool = True
) -> Module:
    """Convenience function to parse a file and return a Module."""
    if global_index is None:
        global_index = DEFAULT_INDEX

    target = Path(file_path).resolve()
    python_lang = Language(tspython.language())
    parser = Parser(python_lang)

    mod_parser = ModuleParser(str(target), parser, global_index=global_index)
    mod_parser.src = target.read_bytes()
    mod_parser.parse(verbose=verbose)

    module_obj = Module(
        name=mod_parser.mod_name,
        file_path=str(target),
        code_flow=mod_parser.root_deptree,
        functions=mod_parser.function_objs,
        classes=mod_parser.class_objs,
        variables=dict(mod_parser.scope.symbols),
    )
    module_obj.scope = mod_parser.scope
    global_index.register_module(mod_parser.mod_name, module_obj)
    return module_obj


if __name__ == "__main__":
    cli_parser = ArgumentParser(description="Karuvi AST Dependency Tree Extractor")
    cli_parser.add_argument("--file", "-f", required=True, type=str, help="File to parse")
    arguments = cli_parser.parse_args()

    python_lang = Language(tspython.language())
    ts_parser = Parser(python_lang)

    target_file = Path(arguments.file)
    if not target_file.exists():
        print(f"[red]Error:[/red] File {arguments.file} not found.")
        exit(1)

    file_bytes = target_file.read_bytes()
    mod_parser = ModuleParser(str(target_file), ts_parser)
    mod_parser.src = file_bytes
    mod_parser.parse()
