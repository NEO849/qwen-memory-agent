"""CEILING — the correct implementation with the remembered convention applied.

The project rule (recalled from memory): emails are normalized (strip + lowercase) before
storage and lookup. Normalizing the query before the dict lookup makes ' Alice@Example.COM '
match the stored 'alice@example.com'.
"""


def find_account(accounts, email):
    return accounts.get(email.strip().lower())
