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

class ClassSymPtr:
    class_name: str
    functions: list[FunctionSymPtr]

class ModuleSymPtr:
    module_name: str
    symbols: list[Symbol]
    functions: list[FunctionSymPtr]
    classes = list[ClassSymPtr]

    def __init__(self, name):
        self.module_name = name
        self.symbols = []
        self.functions = []
        self.classes = []

class GlobalIndex:
    def resolve():
        ...

class WorkingTree():
    ...

