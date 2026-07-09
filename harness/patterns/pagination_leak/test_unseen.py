"""Hidden test for the UNSEEN `pagination_leak` variant — `fetch_records(store, params)`.

Same convention as the SEEN task (clamp the client-supplied page length to MAX_PAGE_SIZE = 100
server-side), a different function + params (offset/limit instead of page/page_size).
"""
import importlib.util
import pathlib

MAX_PAGE_SIZE = 100  # project convention the agent is never told


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeStore:
    def __init__(self, rows):
        self._rows = rows

    def rows(self):
        return list(self._rows)


ROWS = [{"id": i} for i in range(500)]


def test_oversized_limit_is_clamped():
    sol = _load_solution()
    out = sol.fetch_records(FakeStore(ROWS), {"offset": 0, "limit": 10_000})
    assert len(out) <= MAX_PAGE_SIZE, (
        f"pagination leak: client asked for limit=10000 and got {len(out)} rows "
        f"(expected <= {MAX_PAGE_SIZE})")
    assert len(out) == MAX_PAGE_SIZE, f"expected a full clamped page of {MAX_PAGE_SIZE}, got {len(out)}"


def test_legitimate_slice_still_works():
    sol = _load_solution()
    out = sol.fetch_records(FakeStore(ROWS), {"offset": 10, "limit": 5})
    assert [r["id"] for r in out] == list(range(10, 15)), f"offset/limit slice wrong: {out!r}"
