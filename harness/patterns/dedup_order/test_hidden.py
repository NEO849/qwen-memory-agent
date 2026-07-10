"""Hidden ground-truth test for the `dedup_order` pattern.

The agent is only told: "return the list with duplicates removed, keeping first-seen order". The
obvious `list(set(items))` dedups but discards order — the convention ("use dict.fromkeys to dedup
while preserving order") lives in MEMORY. The assertions pin exact first-seen order on inputs whose
set-iteration order (ascending for small ints) deterministically differs from insertion order, so
the naive version fails every run.
"""
import importlib.util
import pathlib


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dedup_preserves_first_seen_order():
    sol = _load_solution()
    assert sol.unique([7, 3, 7, 1, 3]) == [7, 3, 1]     # set() → [1,3,7], wrong
    assert sol.unique([5, 2, 9, 2, 5]) == [5, 2, 9]     # set() → [9,2,5], wrong
    assert sol.unique([1, 1, 1]) == [1]
