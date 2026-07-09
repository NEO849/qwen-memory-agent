"""CEILING — the correct implementation with the remembered convention applied.

The project rule (recalled from memory): never use a mutable default argument. Defaulting to
None and creating a fresh list inside gives each call its own log, so independent calls don't
leak state into one another.
"""


def append_event(event, log=None):
    if log is None:
        log = []
    log.append(event)
    return log
