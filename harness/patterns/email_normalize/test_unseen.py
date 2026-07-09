"""Hidden test for the UNSEEN `email_normalize` variant — `is_registered(emails, email)`.

Same convention as the SEEN task (normalize strip+lower before comparing an email), a different
surface (set membership instead of dict lookup). A raw ' BOB@Example.com ' must match the
normalized stored 'bob@example.com'.
"""
import importlib.util
import pathlib


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EMAILS = {"alice@example.com", "bob@example.com"}


def test_registered_is_case_and_space_insensitive():
    sol = _load_solution()
    assert sol.is_registered(set(EMAILS), " BOB@Example.com ") is True, (
        "a registered email with stray case/whitespace must be recognised")


def test_unregistered_and_exact():
    sol = _load_solution()
    assert sol.is_registered(set(EMAILS), "alice@example.com") is True, "exact match must work"
    assert sol.is_registered(set(EMAILS), "carol@example.com") is False, "unknown email must be False"
