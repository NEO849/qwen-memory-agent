"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

"Parse created_at, add the ttl, compare to now" reads clean and passes a hand-check with a
naive-local created_at. But real tokens carry an AWARE UTC timestamp, and datetime.now() is
NAIVE — so the comparison raises 'can't compare offset-naive and offset-aware datetimes'.
Genuinely how timezone bugs ship; not deliberately broken.
"""
from datetime import datetime, timedelta


def is_expired(token):
    created = datetime.fromisoformat(token["created_at"])
    return datetime.now() > created + timedelta(seconds=token["ttl_seconds"])
