"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

Asked whether a feature flag is on, the obvious move is `bool(config.get(key))`. It passes a
hand-check with values like "" and "true" — but every non-empty string is truthy in Python, so
"false", "0" and "no" all read as ENABLED. Genuinely how config bugs ship; not deliberately broken.
"""


def feature_enabled(config, key):
    return bool(config.get(key))
