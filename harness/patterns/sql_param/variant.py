"""UNSEEN variant of `sql_param` — same convention (parameterize queries; never string-format
SQL), a DIFFERENT operation. The memory was grounded on a SELECT (`find_user`); here it must
TRANSFER to a DELETE (`delete_session`).
"""

TASK = (
    "Implement the function `delete_session(conn, token)` for our auth service.\n"
    "- `conn` is an open sqlite3 connection to a DB with a table `sessions(token TEXT)`.\n"
    "- Delete the row whose token matches exactly and commit. Return the number of rows deleted.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

RECALL_CONTEXT = (
    "implementing delete_session(conn, token) that runs a DELETE against a sqlite sessions "
    "table matching a token value"
)
