"""Hidden test for the UNSEEN `sql_param` variant — `delete_session(conn, token)`.

Same convention as the SEEN task (parameterize; never string-format SQL), a different
operation (DELETE). A token containing an apostrophe ("a'b") breaks f-string SQL.
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
    conn.execute("CREATE TABLE sessions (token TEXT)")
    conn.executemany("INSERT INTO sessions VALUES (?)", [("keep",), ("a'b",), ("other",)])
    conn.commit()
    return conn


def test_delete_token_with_apostrophe():
    sol = _load_solution()
    conn = _db()
    n = sol.delete_session(conn, "a'b")
    assert n == 1, f"expected to delete exactly the a'b session, deleted {n!r}"
    remaining = {r[0] for r in conn.execute("SELECT token FROM sessions")}
    assert remaining == {"keep", "other"}, f"wrong rows deleted; remaining={remaining!r}"


def test_plain_delete_and_no_injection():
    sol = _load_solution()
    conn = _db()
    assert sol.delete_session(conn, "keep") == 1, "a normal token must be deletable"
    # an injection payload matches no token → deletes nothing (not the whole table)
    assert sol.delete_session(conn, "x' OR '1'='1") == 0, "injection payload must delete nothing"
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 2, "table was over-deleted"
