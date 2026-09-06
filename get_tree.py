import tree_sitter_python as tspython
import tree_sitter as ts
from rich import print
from rich.text import Text
from rich.tree import Tree
from tree_sitter import Language, Parser
from argparse import ArgumentParser
from pathlib import Path
import dataclasses

# from import_resolver import root_tree, recurse_tree

parser = ArgumentParser("lsc")
parser.add_argument("--file", "-f", required=True, type=str, help="File to parse")

arguments = parser.parse_args()

PYTHON = Language(tspython.language())
parser = Parser(PYTHON)

file = Path(arguments.file)
tree = parser.parse(file.read_bytes())

cursor = tree.walk()

class DepTree:
    name: str
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
        if len(self.children) == 0:
            return node
        else:
            for child in self.children:
                node.add(child._print())

            return node

class FunctionMeta:
    name: str
    is_async: bool
    parameters: list[str]
    dependencies: list[str]

    def __init__(self):
        self.is_async = False

def parse_parameters(tree: ts.Node):
    params = []
    for node in tree.children:
        if node.type == "identifier":
            params.append(node.text)
        elif node.type == "typed_parameter":
            params.append(node.named_children[0].text)
        elif node.type == "list_splat_pattern":
            print("[red]list comprehension not supported[/red]")
        elif node.type == "dictionary_splat_pattern":
            print("[red]dicitonary comprehension not supported[/red]")

    return params

def parse_function(tree: ts.Node):
    meta = FunctionMeta()
    for item in tree.children:
        if item.type == "async":
            meta.is_async = True
        elif item.type == "identifier":
            meta.name = item.text
        elif item.type == "parameters":
            params = parse_parameters(item)
            meta.parameters = params

    return meta

def get_function_call_dependants(tree: ts.Node):
    node = DepTree()
    function_name = None
    params = []
    for item in tree.children:
        if item.type == "attribute" or item.type == "identifier":
            function_name = item.text.decode()
            node.name = function_name
        else:
            params = item
            break
    for item in params.named_children:
        # print(item.text, item.type)
        # scan for `call`s and `identifiers`s
        if item.type == "identifier":
            node.dependencies.append(item.text.decode())
        elif item.type == "call":
            fn_name = item.children[0].text.decode()
            _, deps = get_function_call_dependants(item)
            deps.name = f"call ({fn_name})"
            node.children.append(deps)

        elif item.type == "tuple":
            _, deps = parse_expression(item)
            node.dependencies.extend(deps)
        elif item.type == "comment":
            continue
        else:
            print("[red]unknown[/red]", item, item.text.decode())


    return function_name, node

def parse_expression(tree: ts.Node):
    name = None
    node = DepTree()
    node.name = "Expression"
    dependencies = []
    for child in tree.children:
        if child.type == "call":
            name, dependencies = get_function_call_dependants(child)
            dependencies.name = f"call ({name})"
            node.children.append(dependencies)
        elif child.type == "assignment":
            left_tree = child.children_by_field_name("left")
            right_tree = child.children_by_field_name("right")

            for child in left_tree:
                if child.type != "identifier":
                    continue
                node.dependencies.append(child.text.decode() + " (dependant)")

            for expr in right_tree:
                n = parse_expression(expr)
                node.children.append(n)

        elif child.type == "identifier":
            node.dependencies.append(child.text.decode())
            dependencies.append(child.text.decode())

    # return f"[green]expr[/green] calls [violet]{name}[/violet]", node
    return node
#
# while True:
#     if cursor.node.type == "module":
#         cursor.goto_first_child()
#         continue
#
#     if not cursor.goto_next_sibling():
#         break
#
#     if cursor.node.type == "import_from_statement":
#         ...
#
#     elif cursor.node.type == "import_statement":
#         imports = []
#         for child in cursor.node.named_children:
#             if b"as" in child.text:
#                 raise Exception("`import ... as ...` syntax not supported")
#             imports.append(child.text.decode())
#         print(imports)
#         for mod in imports:
#             if mod not in root_tree:
#                 print(f"Cannot find definitions for {mod}")
#                 continue
#             print(f"loading pointers for: {mod}")
# #                recurse_tree(root_tree[mod])
#
#     elif cursor.node.type == "function_definition":
#         meta = parse_function(cursor.node)
#         print(f"function: [blue]{meta.name.decode()}[/blue] params: [violet]{(b','.join(meta.parameters)).decode()}[/violet]", "[red]async[/red]" if meta.is_async else "")
#     elif cursor.node.type == "expression_statement":
#         name, deps = parse_expression(cursor.node)
#         print(deps._print())
#     else:
#         print("[red]unknown[/red]", cursor.node.type, cursor.node.text.decode())
# #

from pointers import Symbol

class ModuleParser():
    mod_name: str
    symbol_tree: list[Symbol]
    src: str
    parser: ts.Parser
    cursor: ts.TreeCursor
    root_deptree: DepTree

    def __init__(self, id: str, parser: ts.Parser | None = None):
        self.mod_name = id
        self.parser = parser

    def _cycle(self):
        if self.cursor.node.type == "module":
            self.cursor.goto_first_child()
            return True

        if not self.cursor.goto_next_sibling():
            return False

        if self.cursor.node.type == "import_from_statement":
            raise Exception("`import ... from ...` syntax not supported")

        elif self.cursor.node.type == "import_statement":
            print()
            # imports = []
            if b"as" in self.cursor.node.text:
                raise Exception("`import ... as ...` syntax not supported")

            for child in self.cursor.node.named_children:
                print("importing", child.text.decode())
            #
            # print(imports)
            # for mod in imports:
            #     if mod not in root_tree:
            #         print(f"Cannot find definitions for {mod}")
            #         continue
            #     print(recurse_tree(root_tree[mod], f"Pointers for {mod}"))
            #
        elif self.cursor.node.type == "function_definition":
            meta = parse_function(self.cursor.node)
            print(f"function: [blue]{meta.name.decode()}[/blue] params: [violet]{(b','.join(meta.parameters)).decode()}[/violet]", "[red]async[/red]" if meta.is_async else "")
        elif self.cursor.node.type == "expression_statement":
            dependencies = self._parse_expression(self.cursor.node)
            self.root_deptree.children.append(dependencies)
        else:
            print("[red]unknown[/red]", self.cursor.node.type, self.cursor.node.text.decode())

        return True

    def _get_assignment_fields(self, left, right):
        dependants = []

        for child in left:
            if child.type != "identifier":
                print(f"skipping {child.type} {child.text}")
                continue
            name = child.text.decode()
            dependants.append(name)
            self.symbol_tree

        independants = []
        for expr in right:
            n = self._parse_expression(expr)
            independants.append(n)

        return dependants, independants

    def _parse_expression(self, tree: ts.Tree):
        node = DepTree()
        # node.name = "Expression"  # Default

        for child in tree.named_children:
            if child.type == "call":
                name, subtree = get_function_call_dependants(child)
                subtree.name = f"{name} (call)"
                node.children.append(subtree)

            elif child.type == "assignment":
                left = child.children_by_field_name("left")
                right = child.children_by_field_name("right")
                # deps and indeps from a mathematical sense
                deps, indeps = self._get_assignment_fields(left, right)

                for name in deps:
                    subnode = DepTree(name)
                    subnode.children.extend(indeps)
                    node.children.append(subnode)

            elif child.type == "identifier":
                node.dependencies.append(child.text.decode())
            elif child.type == "augmented_assignment":
                node.dependencies.append(child.text.decode())
            elif child.type == "attribute":
                print(child.text, child)
            else:
                print(f"[red]unknown:[/red]", child.type)

        return node

    def parse(self):
        self.tree = self.parser.parse(self.src)
        self.cursor = self.tree.walk()
        self.root_deptree = DepTree()
        self.root_deptree.name = "Module Start"
        self.symbol_tree = {}

        while self._cycle():
            ...
        print("Parsing complete")


p = ModuleParser("", parser)
p.src = file.read_bytes()
p.parse()
