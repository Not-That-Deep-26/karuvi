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

from pointers import Symbol, SymbolType
from returns import Variable

BUILTINS = set(dir(builtins))


class DepTree:
    name: str | None
    dependencies: list[str]
    children: list["DepTree"]

    def __init__(self, name: str | None = None, children: list["DepTree"] | None = None):
        self.name = name
        self.children = children if children is not None else []
        self.dependencies = []

    def _print(self) -> Tree:
        node = Tree(Text("Node" if self.name is None else self.name))
        for dep in self.dependencies:
            node.add(Text(dep))
        for child in self.children:
            node.add(child._print())
        return node


class Scope:
    """Tracks variables, imports, and functions within a lexical scope."""

    def __init__(self, name: str = "module", parent: Scope | None = None):
        self.name = name
        self.parent = parent
        self.symbols: dict[str, Variable] = {}
        self.imports: dict[str, str] = {}
        self.functions: dict[str, str] = {}

    def add_import(self, name: str, module: str):
        self.imports[name] = module

    def assign_variable(
        self, name: str, node: ts.Node | None = None, filename: str = ""
    ) -> Variable:
        var_uuid = str(uuid.uuid4())
        ref = (filename, node.start_point[0] + 1, node.start_point[1]) if node else None
        var = Variable(name=name, uuid=var_uuid, is_reference=False, reference=ref)
        self.symbols[name] = var
        return var

    def resolve(self, name: str) -> tuple[str, str | None]:
        """
        Resolves a symbol name in this scope or parent scopes.
        Returns:
            ('symbol', uuid) if defined variable
            ('import', module) if imported
            ('builtin', None) if python builtin
            ('undefined', None) if not found
        """
        if name in self.symbols:
            return ("symbol", self.symbols[name].uuid)
        if name in self.imports:
            return ("import", self.imports[name])
        if self.parent:
            return self.parent.resolve(name)
        if name in BUILTINS:
            return ("builtin", None)
        return ("undefined", None)


def format_reference(name: str, scope: Scope) -> str:
    kind, meta = scope.resolve(name)
    if kind == "symbol":
        return f"{name} (reference to id={meta})"
    elif kind == "import":
        return f"{name} (imported from {meta})"
    elif kind == "builtin":
        return f"{name} (builtin)"
    else:
        return f"{name} (undefined!)"


def format_attribute_reference(node: ts.Node, scope: Scope) -> str:
    full_text = node.text.decode()
    root_node = node
    while root_node.type == "attribute":
        obj = root_node.child_by_field_name("object")
        if obj is None:
            break
        root_node = obj

    if root_node and root_node.type == "identifier":
        root_name = root_node.text.decode()
        kind, meta = scope.resolve(root_name)
        if kind == "import":
            return f"{full_text} (imported from {meta})"
        elif kind == "symbol":
            return f"{full_text} (reference to id={meta})"
        elif kind == "builtin":
            return f"{full_text} (builtin)"
        else:
            return f"{full_text} (undefined!)"
    return f"{full_text} (undefined!)"


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


def parse_call_node(node: ts.Node, scope: Scope) -> DepTree:
    func_node = node.child_by_field_name("function")
    args_node = node.child_by_field_name("arguments")
    func_name = func_node.text.decode() if func_node else "anonymous"
    call_tree = DepTree(f"{func_name} (call)")

    if args_node:
        for child in args_node.named_children:
            if child.type == "identifier":
                call_tree.dependencies.append(format_reference(child.text.decode(), scope))
            elif child.type == "attribute":
                call_tree.dependencies.append(format_attribute_reference(child, scope))
            elif child.type == "call":
                sub_call = parse_call_node(child, scope)
                call_tree.children.append(sub_call)
            elif child.type == "keyword_argument":
                key = child.child_by_field_name("name")
                val = child.child_by_field_name("value")
                key_name = key.text.decode() if key else ""
                if val and val.type == "identifier":
                    ref = format_reference(val.text.decode(), scope)
                    call_tree.dependencies.append(f"{key_name}={ref}")
                elif val and val.type == "attribute":
                    ref = format_attribute_reference(val, scope)
                    call_tree.dependencies.append(f"{key_name}={ref}")
                elif val and val.type == "call":
                    sub_call = parse_call_node(val, scope)
                    sub_call.name = f"{key_name}={sub_call.name}"
                    call_tree.children.append(sub_call)
                elif val:
                    call_tree.dependencies.append(f"{key_name}={val.text.decode()}")
            elif child.type == "comment":
                continue
            else:
                sub_expr = parse_expression_tree(child, scope)
                if sub_expr.dependencies or sub_expr.children:
                    if not sub_expr.children and len(sub_expr.dependencies) == 1:
                        call_tree.dependencies.extend(sub_expr.dependencies)
                    else:
                        call_tree.children.append(sub_expr)
    return call_tree


def collect_expression_deps(node: ts.Node, scope: Scope, parent: DepTree):
    """Recursively traverses an expression and collects dependencies and nested calls."""
    if node.type == "identifier":
        parent.dependencies.append(format_reference(node.text.decode(), scope))
    elif node.type == "attribute":
        parent.dependencies.append(format_attribute_reference(node, scope))
    elif node.type == "call":
        parent.children.append(parse_call_node(node, scope))
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
            collect_expression_deps(child, scope, parent)
    elif node.type in ("integer", "float", "string", "true", "false", "none", "comment"):
        pass
    else:
        for child in node.named_children:
            collect_expression_deps(child, scope, parent)


def parse_expression_tree(node: ts.Node, scope: Scope) -> DepTree:
    """
    Parses an expression node into a DepTree.
    If the node is a call, returns the call tree directly.
    Otherwise, returns a DepTree('Node') containing leaf dependencies and child subtrees.
    """
    if node.type == "call":
        return parse_call_node(node, scope)
    expr_tree = DepTree("Node")
    collect_expression_deps(node, scope, expr_tree)
    return expr_tree


def clone_deptree(tree: DepTree) -> DepTree:
    """Deep clone a DepTree instance."""
    cloned = DepTree(tree.name)
    cloned.dependencies = list(tree.dependencies)
    cloned.children = [clone_deptree(c) for c in tree.children]
    return cloned


def parse_decorator(node: ts.Node, scope: Scope) -> DepTree:
    dec_text = node.text.decode()
    dec_tree = DepTree(f"{dec_text} (decorator)")
    for child in node.named_children:
        collect_expression_deps(child, scope, dec_tree)
    return dec_tree


class ModuleParser:
    mod_name: str
    file_path: str
    src: bytes
    parser: ts.Parser
    root_deptree: DepTree
    scope: Scope

    def __init__(self, filename: str, parser: ts.Parser):
        self.file_path = filename
        self.mod_name = Path(filename).stem if filename else ""
        self.parser = parser
        self.scope = Scope(name=self.mod_name)
        self.root_deptree = DepTree("Module Start")
        self.src = b""

    def parse_import(self, node: ts.Node):
        for child in node.named_children:
            if child.type == "dotted_name":
                mod = child.text.decode()
                self.scope.add_import(mod, mod)
                print("importing", mod)
            elif child.type == "aliased_import":
                name = child.child_by_field_name("name")
                alias = child.child_by_field_name("alias")
                mod_name = name.text.decode() if name else ""
                alias_name = alias.text.decode() if alias else mod_name
                self.scope.add_import(alias_name, mod_name)
                print(f"importing {mod_name} as {alias_name}")

    def parse_import_from(self, node: ts.Node):
        mod_node = node.child_by_field_name("module_name")
        mod_name = mod_node.text.decode() if mod_node else ""
        for child in node.named_children:
            if child == mod_node:
                continue
            if child.type == "dotted_name":
                name = child.text.decode()
                self.scope.add_import(name, mod_name)
                print(f"importing {name} from {mod_name}")
            elif child.type == "aliased_import":
                name = child.child_by_field_name("name")
                alias = child.child_by_field_name("alias")
                sym_name = name.text.decode() if name else ""
                alias_name = alias.text.decode() if alias else sym_name
                self.scope.add_import(alias_name, mod_name)
                print(f"importing {sym_name} as {alias_name} from {mod_name}")

    def parse_assignment(self, expr: ts.Node) -> DepTree:
        stmt_node = DepTree("Node")
        left_node = expr.child_by_field_name("left")
        right_node = expr.child_by_field_name("right")
        targets = extract_targets(left_node)

        # Evaluate RHS dependencies in current scope
        rhs_tree = (
            parse_expression_tree(right_node, self.scope) if right_node else DepTree("Node")
        )

        # For each target, assign a new UUID and attach dependencies
        for target_name, target_n in targets:
            var = self.scope.assign_variable(target_name, node=target_n, filename=self.file_path)
            target_tree = DepTree(f"{target_name} (new assignment, id={var.uuid})")
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

        # Dependency 1: target itself (before mutation)
        target_dep = format_reference(target_name, self.scope)

        # Dependency 2: RHS operand(s)
        rhs_tree = (
            parse_expression_tree(right_node, self.scope) if right_node else DepTree("Node")
        )

        # Assign new UUID to target after evaluating inputs
        var = self.scope.assign_variable(target_name, node=left_node, filename=self.file_path)
        rhs_text = right_node.text.decode() if right_node else ""
        aug_tree = DepTree(f"{target_name} {op_text} {rhs_text} (new assignment, id={var.uuid})")
        aug_tree.dependencies.append(target_dep)

        if rhs_tree.name == "Node":
            aug_tree.dependencies.extend(rhs_tree.dependencies)
            aug_tree.children.extend(rhs_tree.children)
        else:
            aug_tree.children.append(rhs_tree)

        stmt_node.children.append(aug_tree)
        return stmt_node

    def parse_function_definition(self, node: ts.Node) -> DepTree:
        stmt_node = DepTree("Node")
        fn_name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        body_node = node.child_by_field_name("body")

        fn_name = fn_name_node.text.decode() if fn_name_node else "anonymous"
        fn_uuid = str(uuid.uuid4())
        self.scope.functions[fn_name] = fn_uuid
        self.scope.symbols[fn_name] = Variable(name=fn_name, uuid=fn_uuid, is_reference=False)

        fn_scope = Scope(name=fn_name, parent=self.scope)
        param_names = []
        param_nodes = []
        if params_node:
            for p in params_node.named_children:
                p_name = extract_param_name(p)
                var = fn_scope.assign_variable(p_name, node=p, filename=self.file_path)
                param_names.append(p_name)
                param_nodes.append(f"{p_name} (parameter, id={var.uuid})")

        fn_tree = DepTree(f"def {fn_name}({', '.join(param_names)}) (id={fn_uuid})")
        for p_dep in param_nodes:
            fn_tree.dependencies.append(p_dep)

        # Parse body statements in fn_scope
        if body_node:
            for stmt in body_node.named_children:
                parsed_stmt = self._parse_statement_in_scope(stmt, fn_scope)
                if parsed_stmt:
                    fn_tree.children.append(parsed_stmt)

        stmt_node.children.append(fn_tree)
        return stmt_node

    def parse_decorated_definition(self, node: ts.Node) -> DepTree:
        stmt_node = DepTree("Node")
        inner_tree: DepTree | None = None
        decorators: list[DepTree] = []

        for child in node.named_children:
            if child.type == "decorator":
                decorators.append(parse_decorator(child, self.scope))
            elif child.type == "function_definition":
                fn_wrapper = self.parse_function_definition(child)
                # fn_wrapper contains [fn_tree]
                inner_tree = fn_wrapper.children[0] if fn_wrapper.children else fn_wrapper
            elif child.type == "class_definition":
                cls_wrapper = self.parse_class_definition(child)
                inner_tree = cls_wrapper.children[0] if cls_wrapper.children else cls_wrapper

        if inner_tree:
            for dec in decorators:
                inner_tree.children.insert(0, dec)
            stmt_node.children.append(inner_tree)
        else:
            for dec in decorators:
                stmt_node.children.append(dec)

        return stmt_node

    def parse_class_definition(self, node: ts.Node) -> DepTree:
        stmt_node = DepTree("Node")
        cls_name_node = node.child_by_field_name("name")
        body_node = node.child_by_field_name("body")
        cls_name = cls_name_node.text.decode() if cls_name_node else "anonymous"
        cls_uuid = str(uuid.uuid4())
        self.scope.symbols[cls_name] = Variable(name=cls_name, uuid=cls_uuid, is_reference=False)

        cls_tree = DepTree(f"class {cls_name} (id={cls_uuid})")
        cls_scope = Scope(name=cls_name, parent=self.scope)

        if body_node:
            for stmt in body_node.named_children:
                parsed_stmt = self._parse_statement_in_scope(stmt, cls_scope)
                if parsed_stmt:
                    cls_tree.children.append(parsed_stmt)

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
                    parse_expression_tree(right_node, scope) if right_node else DepTree("Node")
                )
                stmt_node = DepTree("Node")
                for target_name, target_n in targets:
                    var = scope.assign_variable(
                        target_name, node=target_n, filename=self.file_path
                    )
                    target_tree = DepTree(f"{target_name} (new assignment, id={var.uuid})")
                    target_tree.children.append(clone_deptree(rhs_tree))
                    stmt_node.children.append(target_tree)
                return stmt_node
            elif expr.type == "call":
                call_tree = parse_call_node(expr, scope)
                stmt_node = DepTree("Node")
                stmt_node.children.append(call_tree)
                return stmt_node
            elif expr.type == "augmented_assignment":
                left_node = expr.child_by_field_name("left")
                right_node = expr.child_by_field_name("right")
                operator_node = expr.children[1] if len(expr.children) > 1 else None
                op_text = operator_node.text.decode() if operator_node else "*="
                target_name = left_node.text.decode() if left_node else ""
                target_dep = format_reference(target_name, scope)
                rhs_tree = (
                    parse_expression_tree(right_node, scope) if right_node else DepTree("Node")
                )
                var = scope.assign_variable(target_name, node=left_node, filename=self.file_path)
                rhs_text = right_node.text.decode() if right_node else ""
                aug_tree = DepTree(
                    f"{target_name} {op_text} {rhs_text} (new assignment, id={var.uuid})"
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
                sub_tree = parse_expression_tree(expr, scope)
                if sub_tree.dependencies or sub_tree.children:
                    stmt_node = DepTree("Node")
                    stmt_node.children.append(sub_tree)
                    return stmt_node
        elif node.type == "return_statement":
            ret_tree = DepTree("return")
            for child in node.named_children:
                collect_expression_deps(child, scope, ret_tree)
            stmt_node = DepTree("Node")
            stmt_node.children.append(ret_tree)
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
            call_tree = parse_call_node(expr, self.scope)
            stmt_node = DepTree("Node")
            stmt_node.children.append(call_tree)
            return stmt_node
        else:
            sub_tree = parse_expression_tree(expr, self.scope)
            if sub_tree.dependencies or sub_tree.children:
                stmt_node = DepTree("Node")
                stmt_node.children.append(sub_tree)
                return stmt_node
            return None

    def parse(self):
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
                print(f"[red]unknown top-level statement:[/red] {child.type}")

        print("Parsing complete")
        print(self.root_deptree._print())


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
