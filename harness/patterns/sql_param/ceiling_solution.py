"""CEILING — the correct implementation with the remembered convention applied.

The project rule (recalled from memory): never build SQL by string formatting. A `?`
placeholder with a params tuple lets sqlite bind the value safely — "o'brien" matches
exactly and injection payloads are treated as literal data, not SQL.
"""


def find_user(conn, username):
    cur = conn.execute(
        "SELECT id, username FROM users WHERE username = ?", (username,))
    return cur.fetchone()
