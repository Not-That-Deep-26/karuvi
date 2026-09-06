from example_a import daddy

global_daddy_ref = daddy

def my_func(daddy):
    local_ref = daddy
    daddy = 99
    reassigned_ref = daddy
    return reassigned_ref
