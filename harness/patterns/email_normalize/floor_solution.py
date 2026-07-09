"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

"Return the account whose email matches" reads like a plain dict lookup: accounts.get(email).
It passes a hand-check with a tidy 'alice@example.com', but real inputs arrive with stray case
and whitespace (' Alice@Example.COM ') and miss the normalized stored key. Genuinely how these
bugs ship; not deliberately broken.
"""


def find_account(accounts, email):
    return accounts.get(email)
