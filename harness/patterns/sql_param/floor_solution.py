"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

Interpolating the value straight into the SQL string reads clean and works on tidy inputs
like "alice". But a username with an apostrophe ("o'brien") closes the string literal and
raises sqlite3.OperationalError — and the pattern is a textbook SQL-injection. Genuinely how
these bugs ship; not deliberately broken.
"""


def find_user(conn, username):
    cur = conn.execute(
        f"SELECT id, username FROM users WHERE username = '{username}'")
    return cur.fetchone()
