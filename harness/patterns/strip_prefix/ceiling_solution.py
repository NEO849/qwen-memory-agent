"""CEILING — the correct implementation with the remembered convention applied.

Project rule (recalled from memory): to remove a fixed PREFIX from a string, use
`str.removeprefix` — never `str.strip`, which removes a character *set* from both ends, not
a leading substring. `removeprefix` leaves strings that don't start with the prefix untouched.
"""


def clean_path(path):
    return path.removeprefix("/api/")
