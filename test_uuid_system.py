from pathlib import Path
from returns import start_file, get_tree, find_tree, Variable
from pointers import DEFAULT_INDEX

def test_cross_module_uuid_differentiation():
    # Parse example_b.py via start_file
    mod_b = start_file("example_b.py")
    tree = get_tree()

    assert tree is not None
    assert tree.name == "Module Start"

    # Find assignments in tree
    # first_ref node
    node_first_ref = tree.children[0].children[0]
    assert node_first_ref.variable is not None
    assert node_first_ref.variable.name == "first_ref"
    assert node_first_ref.variable.is_reference is False

    # Check dependency of first_ref (should be daddy from example_a)
    dep_daddy_a = node_first_ref.children[0].dependencies[0]
    assert isinstance(dep_daddy_a, Variable)
    assert dep_daddy_a.name == "daddy"
    assert dep_daddy_a.is_reference is True
    assert dep_daddy_a.uuid is not None

    # daddy assignment node in example_b
    node_daddy_b = tree.children[1].children[0]
    assert node_daddy_b.variable is not None
    assert node_daddy_b.variable.name == "daddy"
    assert node_daddy_b.variable.is_reference is False
    uuid_daddy_b = node_daddy_b.variable.uuid
    assert uuid_daddy_b is not None

    # Assert that daddy declared in b has a DIFFERENT UUID than daddy from a
    assert uuid_daddy_b != dep_daddy_a.uuid, "Declared daddy in b must have different UUID from daddy in a"

    # Check dependency of second_ref (should be daddy from example_b)
    node_second_ref = tree.children[2].children[0]
    dep_daddy_b = node_second_ref.children[0].dependencies[0]
    assert isinstance(dep_daddy_b, Variable)
    assert dep_daddy_b.name == "daddy"
    assert dep_daddy_b.is_reference is True
    assert dep_daddy_b.uuid == uuid_daddy_b, "second_ref must reference the local daddy UUID"

    # Test find_tree by UUID
    found_node_a = find_tree(dep_daddy_a.uuid, tree)
    assert found_node_a is not None, "find_tree should find the subtree referencing daddy from a"

    found_node_b = find_tree(uuid_daddy_b, tree)
    assert found_node_b is not None, "find_tree should find the node declaring daddy in b"
    assert found_node_b.variable.uuid == uuid_daddy_b

    print("[PASS] test_cross_module_uuid_differentiation passed successfully!")


def test_function_scope_uuid_differentiation():
    mod_c = start_file("example_c.py")
    tree = get_tree()

    # global_daddy_ref depends on daddy from example_a
    node_global_ref = tree.children[0].children[0]
    dep_global_daddy = node_global_ref.children[0].dependencies[0]
    assert dep_global_daddy.name == "daddy"
    assert dep_global_daddy.is_reference is True

    # Function def node
    fn_node = tree.children[1].children[0]
    assert fn_node.variable.name == "my_func"
    param_daddy = fn_node.dependencies[0]
    assert param_daddy.name == "daddy"
    assert param_daddy.is_reference is False
    assert param_daddy.uuid != dep_global_daddy.uuid

    # local_ref inside my_func references param_daddy
    node_local_ref = fn_node.children[0].children[0]
    dep_local_ref = node_local_ref.children[0].dependencies[0]
    assert dep_local_ref.name == "daddy"
    assert dep_local_ref.is_reference is True
    assert dep_local_ref.uuid == param_daddy.uuid

    # daddy = 99 inside my_func declares a new UUID
    node_local_daddy_decl = fn_node.children[1].children[0]
    assert node_local_daddy_decl.variable.name == "daddy"
    assert node_local_daddy_decl.variable.is_reference is False
    assert node_local_daddy_decl.variable.uuid != param_daddy.uuid
    assert node_local_daddy_decl.variable.uuid != dep_global_daddy.uuid

    # reassigned_ref inside my_func references the local reassigned daddy
    node_reassigned_ref = fn_node.children[2].children[0]
    dep_reassigned = node_reassigned_ref.children[0].dependencies[0]
    assert dep_reassigned.name == "daddy"
    assert dep_reassigned.is_reference is True
    assert dep_reassigned.uuid == node_local_daddy_decl.variable.uuid

    print("[PASS] test_function_scope_uuid_differentiation passed successfully!")


if __name__ == "__main__":
    test_cross_module_uuid_differentiation()
    test_function_scope_uuid_differentiation()
