"""Hidden ground-truth test for the `utc_datetime` A/B pattern.

The coding agent NEVER sees this file. It is only told: "token has created_at (ISO string)
and ttl_seconds; return whether it has expired." The obvious implementation compares
datetime.fromisoformat(created_at) against datetime.now(). Real tokens carry an AWARE UTC
timestamp ('...+00:00'), and datetime.now() is NAIVE — so the comparison raises
'can't compare offset-naive and offset-aware datetimes'. That timestamps are timezone-aware
UTC is a project convention that lives in MEMORY, never stated in the task.
"""
import importlib.util
import pathlib
from datetime import datetime, timedelta, timezone


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_expired_token_is_detected():
    """An aware-UTC token created well in the past must read as expired — the naive
    datetime.now() path raises on the aware/naive comparison instead."""
    sol = _load_solution()
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    token = {"created_at": old, "ttl_seconds": 60}
    assert sol.is_expired(token) is True, "a token created an hour ago with 60s TTL must be expired"


def test_fresh_token_is_not_expired():
    """Guards against over-correction: a just-created aware token must NOT be expired."""
    sol = _load_solution()
    now = datetime.now(timezone.utc).isoformat()
    token = {"created_at": now, "ttl_seconds": 3600}
    assert sol.is_expired(token) is False, "a token created now with 1h TTL must not be expired"
