# tests/fixtures/cycles/c.py
import a

def step_c():
    return a.step_a()
