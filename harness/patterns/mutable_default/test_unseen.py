"""Hidden test for the UNSEEN `mutable_default` variant — `register(key, value, store=None)`.

Same convention as the SEEN task (no mutable default arg; default None + fresh object inside),
a different container (dict instead of list). A shared `store={}` default leaks across calls.
"""
import importlib.util
import pathlib


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_each_call_starts_fresh():
    sol = _load_solution()
    first = sol.register("a", 1)
    second = sol.register("b", 2)
    assert second == {"b": 2}, (
        f"independent calls leaked state: second call returned {second!r}, expected {{'b': 2}} "
        f"— a shared mutable default dict")
    assert first == {"a": 1}, f"first call's store was mutated by the second: {first!r}"


def test_explicit_store_is_used():
    sol = _load_solution()
    existing = {"a": 1}
    out = sol.register("b", 2, existing)
    assert out == {"a": 1, "b": 2}, f"expected both keys when passing a store, got {out!r}"
