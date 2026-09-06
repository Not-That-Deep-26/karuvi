
class Variable:
    """
    A variable is the smallest unit of dependency
    Multiple variables may have the same name, but if they refer to different
    items their uuid will be different
    UUID is created **only** at assignment
    """
    name: str
    uuid: str
    is_reference: bool
    reference: tuple[str, int, int] # filename, lineno, colno 

class DepTree:
    """
    DepTree will represent the code flow and dependency chain in any non structural objects
    Structural objects will need extra metadata attached, and will have seperate classes which contain DepTree objects (Function, Class and Module classes)
    """
    children: list["DepTree"]
    dependencies: list[Variable]

class Function:
    """
    Will treat variables in the signatures as assignments and create uuids in  the function for them
    Flow will contain the body of the function
    """
    name: str
    signature: str
    flow: DepTree

class Class:
    """
    This will be implemented if we have time, it is pretty complicated
    """
    functions: list[Function]

class Module:
    code_flow: DepTree
    functions: list

def start_file(filename: str): ...

def get_tree() -> DepTree:
    ...

def find_tree(uuid: str)

