"""Hidden ground-truth test for the `mutable_default` A/B pattern.

The coding agent NEVER sees this file. It is only told: "append event to log and return it;
when called without a log, start a new empty log." The obvious `def append_event(event, log=[])`
shares one list across all calls, so independent calls leak state. That mutable default
arguments are forbidden is a Python convention that lives in MEMORY, not in the task.
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
    """Two independent calls (no log passed) must NOT share state."""
    sol = _load_solution()
    first = sol.append_event("login")
    second = sol.append_event("logout")
    assert second == ["logout"], (
        f"independent calls leaked state: second call returned {second!r}, expected ['logout'] "
        f"— a shared mutable default list")
    assert first == ["login"], f"first call's log was mutated by the second: {first!r}"


def test_explicit_log_is_appended():
    """Guards against over-correction: a passed-in log must still be appended to and returned."""
    sol = _load_solution()
    existing = ["a"]
    out = sol.append_event("b", existing)
    assert out == ["a", "b"], f"expected ['a','b'] when appending to a passed log, got {out!r}"
