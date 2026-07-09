"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

`def append_event(event, log=[])` reads like the obvious default. But the default list is
created once at definition time and shared across every call, so independent calls leak state
into each other. A classic, genuinely-shipped Python bug; not deliberately broken.
"""


def append_event(event, log=[]):
    log.append(event)
    return log
