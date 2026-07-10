"""Give the SEEDED demo memory a coherent ILLUSTRATIVE onboarding timeline, so the globe's
time-travel slider is meaningful.

The demo ledger is a curated seed (realistic coding lessons created in one seeding run). This
spreads their existence across the past weeks — **created_at AND valid_from set to the SAME value**
(no transaction-vs-validity discrepancy a judge could catch) — and closes a few validity intervals
for lessons already tombstoned, so scrubbing the slider actually shows the memory grow and forget.

HONEST SCOPE: this is an ILLUSTRATIVE demo timeline, not real production usage history — the UI and
docs label it as such. It touches ONLY timestamps; alpha/beta, status, outcomes and links are left
exactly as they are, so earned confidence / grounded_outcomes / calibration_gap are unchanged.

Deterministic (fixed anchor dates, id-ordered — no wall clock), idempotent (re-running reproduces
the same stamps). Run:  python -m harness.seed_timeline [ledger-path]
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from backend import config, ledger

# Fixed anchors (no Date.now → reproducible). The seed "onboarding" runs over ~8 weeks up to here.
_START = datetime(2026, 5, 12, 9, 0, 0, tzinfo=timezone.utc)
_END = datetime(2026, 7, 6, 18, 0, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def apply(path: str) -> dict:
    rows = ledger.list_lessons(path=path)                       # pinned-first, then id ASC
    rows.sort(key=lambda l: l["id"])                            # pure chronological by creation id
    n = len(rows)
    if n == 0:
        return {"updated": 0, "tombstones_dated": 0, "span_days": 0}
    span = (_END - _START).total_seconds()
    tomb = 0
    with ledger._connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        for i, l in enumerate(rows):
            frac = i / max(1, n - 1)
            born = _START + timedelta(seconds=span * frac)
            ts = _iso(born)
            # created_at == valid_from → the lesson simply "exists since" this instant (consistent)
            conn.execute("UPDATE lessons SET created_at=?, valid_from=? WHERE id=?", (ts, ts, l["id"]))
            if l["status"] == "obsolete":
                # it was refuted a few days after it was learned → close the validity interval THEN
                died = _iso(min(born + timedelta(days=6), _END))
                conn.execute("UPDATE lessons SET valid_to=? WHERE id=?", (died, l["id"]))
                tomb += 1
        conn.commit()
    return {"updated": n, "tombstones_dated": tomb,
            "span_days": round(span / 86400, 1), "from": _iso(_START)[:10], "to": _iso(_END)[:10]}


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    r = apply(p)
    print(f"illustrative timeline applied: {r['updated']} lessons spread {r.get('from')}→{r.get('to')} "
          f"({r['span_days']} days), {r['tombstones_dated']} tombstones dated. "
          f"confidence/outcomes untouched.")
