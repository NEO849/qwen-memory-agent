"""Hidden test for the UNSEEN `utc_datetime` variant — `seconds_until(deadline)`.

Same convention as the SEEN task (use datetime.now(timezone.utc), never naive datetime.now()),
a different function. An aware-UTC deadline compared against a naive now raises
'can't compare offset-naive and offset-aware datetimes'.
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


def test_future_deadline_is_positive():
    sol = _load_solution()
    deadline = (datetime.now(timezone.utc) + timedelta(seconds=3600)).isoformat()
    got = sol.seconds_until(deadline)
    assert 3400 < got <= 3600, f"expected ~3600s until an aware-UTC deadline 1h out, got {got!r}"


def test_past_deadline_is_negative():
    sol = _load_solution()
    deadline = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    got = sol.seconds_until(deadline)
    assert got < 0, f"a deadline 10 min in the past must be negative, got {got!r}"
