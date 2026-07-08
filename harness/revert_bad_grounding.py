"""Undo a mismatched grounding run: reset lessons #1 (tenant) & #29 (pagination) to their original
human prior Beta(3,1)=0.75 and delete the (unfair) outcome rows.

Why: harness.ground_spread grounded the GENERAL seeded lessons against STRICT concrete hidden tests
they don't satisfy, so they logged real fails and their confidence dropped — a mismatched test, not a
refuted lesson. This is a pure, honest data restoration (no fabricated numbers): the lessons go back to
exactly their seeded state, as if never grounded.

Run:  python -m harness.revert_bad_grounding [ledger-path]
"""
from __future__ import annotations

import sqlite3
import sys

from backend import config

IDS = (1, 29)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    c = sqlite3.connect(path)
    c.execute(f"DELETE FROM outcomes WHERE lesson_id IN {IDS}")
    c.execute(f"UPDATE lessons SET alpha=3.0, beta=1.0, status='active', superseded_by=NULL "
              f"WHERE id IN {IDS}")
    c.commit()
    print("reverted → (id, alpha, beta, status):")
    for r in c.execute(f"SELECT id, alpha, beta, status FROM lessons WHERE id IN {IDS}"):
        print("  ", r)
    print("total outcomes remaining:", c.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
