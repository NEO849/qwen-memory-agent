"""Hidden ground-truth test for the `sql_param` A/B pattern.

The coding agent NEVER sees this file. It is only told: "return the row whose username
matches, or None." The obvious implementation builds the query with an f-string, which breaks
on a username containing an apostrophe ("o'brien") and is injectable. That queries must be
parameterized is a project/security convention that lives in MEMORY, never stated in the task.
"""
import importlib.util
import pathlib
import sqlite3


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (id INTEGER, username TEXT)")
    conn.executemany("INSERT INTO users VALUES (?, ?)",
                     [(1, "alice"), (2, "o'brien"), (3, "bob")])
    conn.commit()
    return conn


def test_username_with_apostrophe():
    """The real-world value that breaks f-string SQL must be found correctly."""
    sol = _load_solution()
    row = sol.find_user(_db(), "o'brien")
    assert row is not None and row[1] == "o'brien", (
        f"expected the o'brien row, got {row!r} — f-string SQL breaks on the apostrophe")


def test_plain_username_and_no_injection():
    """Guards against over-correction: normal lookups still work, and an injection payload
    returns no spurious rows (parameterization treats it as literal data)."""
    sol = _load_solution()
    conn = _db()
    assert sol.find_user(conn, "alice")[0] == 1, "alice must be found by exact username"
    assert sol.find_user(conn, "nope") is None, "a non-existent username must return None"
    assert sol.find_user(conn, "x' OR '1'='1") is None, (
        "an injection payload must match no user, not return an arbitrary row")
