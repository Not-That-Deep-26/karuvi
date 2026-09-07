# tests/fixtures/cycles/a.py
import b

def step_a():
    return b.step_b()
