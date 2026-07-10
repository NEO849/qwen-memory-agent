"""CEILING — the correct implementation with the remembered convention applied.

Project rule (recalled from memory): boolean config/env values are STRINGS. Never coerce them
with `bool(value)` — every non-empty string is truthy, so "false" and "0" would read as True.
Compare against an explicit truthy set instead.
"""

_TRUTHY = {"1", "true", "yes", "on"}


def feature_enabled(config, key):
    return str(config.get(key, "")).strip().lower() in _TRUTHY
