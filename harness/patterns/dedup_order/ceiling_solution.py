"""CEILING — the correct implementation with the remembered convention applied.

Project rule (recalled from memory): to de-duplicate a list while KEEPING first-seen order, use
`dict.fromkeys` — never `list(set(...))`, which drops the ordering the caller relies on.
"""


def unique(items):
    return list(dict.fromkeys(items))
