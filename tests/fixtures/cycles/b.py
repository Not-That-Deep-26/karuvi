# tests/fixtures/cycles/b.py
import c

def step_b():
    return c.step_c()
