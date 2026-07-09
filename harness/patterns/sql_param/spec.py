"""A/B pattern spec — `sql_param` (f-string SQL vs parameterized query).

Same shape as harness/patterns/money_rounding/spec.py.

Floor (no memory) -> builds SQL with an f-string -> a username with an apostrophe ("o'brien")
                     breaks the query (OperationalError) and the pattern is injectable -> RED.
Ceiling (memory)  -> parameterized query with a `?` placeholder + params tuple             -> GREEN.
"""

# The under-specified task. It says NOTHING about parameterization — that queries must be
# parameterized (never string-formatted) is a project/security convention from memory.
TASK = (
    "Implement the function `find_user(conn, username)` for our accounts service.\n"
    "- `conn` is an open sqlite3 connection to a DB with a table `users(id INTEGER, "
    "username TEXT)`.\n"
    "- Return the single row (id, username) whose username matches exactly, or None if there "
    "is no match.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

# What arm B learns from FIRST (a prior red test + human fix), then recalls for TASK. The
# convention (parameterize queries; never build SQL by string formatting) enters here.
SEED_TEST_OUTPUT = (
    "FAILED test_username_with_apostrophe - sqlite3.OperationalError: near \"brien\": syntax "
    "error. find_user built the query with an f-string: \n"
    "  f\"SELECT id, username FROM users WHERE username = '{username}'\"\n"
    "so username \"o'brien\" closed the string literal and broke the SQL (and is injectable).\n"
    "Root cause + fix: NEVER interpolate values into SQL. Use a parameterized query with a `?` "
    "placeholder and pass the value in the params tuple: "
    "conn.execute('SELECT id, username FROM users WHERE username = ?', (username,))."
)
SEED_DIFF = (
    "--- a/accounts.py\n+++ b/accounts.py\n"
    "-    cur = conn.execute(\n"
    "-        f\"SELECT id, username FROM users WHERE username = '{username}'\")\n"
    "+    cur = conn.execute(\n"
    "+        \"SELECT id, username FROM users WHERE username = ?\", (username,))\n"
    "     return cur.fetchone()"
)

# The context arm B uses to RECALL the lesson (mirrors the coding situation).
RECALL_CONTEXT = (
    "implementing find_user(conn, username) that runs a SELECT against a sqlite users table "
    "filtering rows by a username value"
)

# Canonical form of the remembered convention (verbatim from the seeded human fix).
CANONICAL_LESSON = (
    "Never build SQL by interpolating values (f-strings/.format/%/+ concatenation) — it breaks "
    "on values like \"o'brien\" and is injectable. Use a parameterized query: pass the value via "
    "a `?` placeholder and a params tuple, e.g. "
    "conn.execute('SELECT id, username FROM users WHERE username = ?', (username,))."
)
