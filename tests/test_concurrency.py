"""Concurrency — outcome writes are atomic, no lost updates under parallel load.

`ledger.record_outcome` does an in-SQL `alpha = alpha + 1` inside BEGIN IMMEDIATE on a WAL
database with a 5s busy timeout. So N processes each recording M passes on the SAME lesson must
yield EXACTLY alpha = 1 + N*M — never fewer (a lost read-modify-write) — which proves the Beta
counter is a real, race-free systems property rather than a docstring claim.
"""
from __future__ import annotations

import multiprocessing as mp

from backend import ledger


def _hammer(args) -> None:
    path, lesson_id, m, result = args
    for _ in range(m):
        ledger.record_outcome(lesson_id, result, path=path)


def test_no_lost_updates_under_parallel_outcomes(tmp_path):
    db = str(tmp_path / "ledger.sqlite")
    ledger.init_db(db)
    lid = ledger.add_lesson("concurrency", "record races must not lose an update",
                            source="agent-distill", path=db)  # fresh Beta(1,1)

    N, M = 8, 25  # 200 concurrent increments on one row
    ctx = mp.get_context("fork")
    with ctx.Pool(N) as pool:
        pool.map(_hammer, [(db, lid, M, "pass")] * N)

    final = ledger.get_lesson(lid, path=db)
    assert final["alpha"] == 1.0 + N * M, "a concurrent pass was lost"
    assert final["beta"] == 1.0
    assert len(ledger.outcomes_for(lid, path=db)) == N * M
