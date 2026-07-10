"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

Asked to "return the list with duplicates removed", the obvious move is `list(set(items))`. It
dedups correctly and passes a hand-check that only inspects membership — but a set has no order,
so the first-seen ordering the caller depends on is lost. Genuinely how ordering bugs ship; not
deliberately broken.
"""


def unique(items):
    return list(set(items))
