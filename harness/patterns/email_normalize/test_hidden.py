"""Hidden ground-truth test for the `email_normalize` A/B pattern.

The coding agent NEVER sees this file. It is only told: "return the account whose email
matches, or None." The obvious implementation is a plain accounts.get(email), which misses a
client-supplied email with stray case/whitespace. That emails are normalized (strip+lower)
before storage and lookup is a project convention that lives in MEMORY, not the task.
"""
import importlib.util
import pathlib


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ACCOUNTS = {"alice@example.com": {"id": 1}, "bob@example.com": {"id": 2}}


def test_lookup_is_case_and_space_insensitive():
    """A client-supplied email with stray case/whitespace must still find the account."""
    sol = _load_solution()
    got = sol.find_account(dict(ACCOUNTS), " Alice@Example.COM ")
    assert got == {"id": 1}, (
        f"normalization missing: find_account returned {got!r} for ' Alice@Example.COM ', "
        f"expected alice's account (stored under 'alice@example.com')")


def test_exact_match_and_missing():
    """Guards against over-correction: exact matches still work and unknowns return None."""
    sol = _load_solution()
    assert sol.find_account(dict(ACCOUNTS), "bob@example.com") == {"id": 2}, "exact match failed"
    assert sol.find_account(dict(ACCOUNTS), "carol@example.com") is None, "unknown email must be None"
