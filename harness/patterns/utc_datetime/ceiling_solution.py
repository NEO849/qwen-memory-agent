"""CEILING — the correct implementation with the remembered convention applied.

The project rule (recalled from memory): timestamps are timezone-aware UTC. Using
datetime.now(timezone.utc) keeps both sides of the comparison aware, so an aware created_at
compares cleanly and the TTL check is correct regardless of the server's local timezone.
"""
from datetime import datetime, timedelta, timezone


def is_expired(token):
    created = datetime.fromisoformat(token["created_at"])
    return datetime.now(timezone.utc) > created + timedelta(seconds=token["ttl_seconds"])
