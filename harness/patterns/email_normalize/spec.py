"""A/B pattern spec — `email_normalize` (raw email lookup vs normalized strip+lower).

Same shape as harness/patterns/money_rounding/spec.py. No imports, no tricky stdlib — the only
failure mode is the missing project convention (emails are normalized before storage + lookup).

Floor (no memory) -> accounts.get(email) with the raw client string -> misses the normalized
                     key ' Alice@Example.COM ' vs 'alice@example.com' -> hidden test RED.
Ceiling (memory)  -> accounts.get(email.strip().lower())                                  -> GREEN.
"""

# The under-specified task. It says NOTHING about normalization — that emails are stored
# stripped+lowercased is a project convention that must come from memory.
TASK = (
    "Implement the function `find_account(accounts, email)` for our accounts service.\n"
    "- `accounts` is a dict mapping an email address to an account dict.\n"
    "- Return the account whose email matches, or None if there is no match.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

# What arm B learns from FIRST (a prior red test + human fix), then recalls for TASK.
SEED_TEST_OUTPUT = (
    "FAILED test_lookup_is_case_and_space_insensitive - AssertionError: find_account returned "
    "None for ' Alice@Example.COM ', expected alice's account. Accounts are stored under the "
    "normalized email 'alice@example.com', but the lookup used the raw client-supplied string.\n"
    "Root cause + fix: emails in this codebase are normalized (strip whitespace + lowercase) "
    "before BOTH storage and lookup. Normalize the query before the dict lookup: "
    "accounts.get(email.strip().lower())."
)
SEED_DIFF = (
    "--- a/accounts.py\n+++ b/accounts.py\n"
    "-    return accounts.get(email)\n"
    "+    return accounts.get(email.strip().lower())"
)

# The context arm B uses to RECALL the lesson (mirrors the coding situation).
RECALL_CONTEXT = (
    "implementing find_account(accounts, email) that looks up an account in a dict keyed by an "
    "email address"
)

# Canonical form of the remembered convention (verbatim from the seeded human fix).
CANONICAL_LESSON = (
    "Emails are normalized (strip whitespace + lowercase) before storage AND lookup in this "
    "codebase. Never look up or compare a raw client-supplied email — a value like "
    "' Alice@Example.COM ' won't match the stored 'alice@example.com'. Normalize first: "
    "accounts.get(email.strip().lower())."
)
