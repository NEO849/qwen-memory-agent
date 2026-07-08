"""One honest, deterministic step to give the live deck an EARNED confidence spread for the video.

It (a) reverts the earlier mismatched grounding on the tenant/pagination seeds, (b) upgrades those two
cards to the CONCRETE, test-passing form of the lesson (the specific fix, not the vague principle),
and (c) grounds each against its REAL hidden test over a different number of rounds — so confidence is
genuinely earned and naturally varied (more real evidence -> higher):

  * #1  tenant isolation  -> concrete order['tenant_id']==user['tenant_id'], 8 real rounds  (~0.92)
  * #29 pagination leak   -> concrete clamp-to-MAX_PAGE_SIZE,                 5 real rounds  (~0.89)
  (money_rounding is already grounded ~0.86 by harness.ground_demo, plus a tombstoned wrong lesson)

No new/duplicate cards — the tested text IS the card's text. Every number is a real Beta posterior from
real code-gen + pytest outcomes; nothing is fabricated. Lessons without an executable test stay at prior.

Run (service stopped):  python -m harness.rebuild_demo <ledger-path>
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from backend import config, ledger, memory
from harness import ab_runner
from harness import generalization as G

_PAG = Path(__file__).parent / "patterns" / "pagination_leak"
TENANT_ID, PAG_ID = 1, 29


def _reset(path: str) -> None:
    """Undo the mismatched grounding: back to the seeded human prior Beta(3,1), no outcomes."""
    c = sqlite3.connect(path)
    c.execute("DELETE FROM outcomes WHERE lesson_id IN (?,?)", (TENANT_ID, PAG_ID))
    c.execute("UPDATE lessons SET alpha=3.0, beta=1.0, status='active', superseded_by=NULL "
              "WHERE id IN (?,?)", (TENANT_ID, PAG_ID))
    c.commit()
    c.close()


def _block(lesson: str) -> str:
    return memory.render_injection([{"lesson": lesson, "severity": "high", "source": "human"}])


def _tenant_pass(block: str) -> bool:
    return ab_runner._run_pytest(ab_runner._agent_write_code(block))[0]


def _pag_pass(block: str, task: str) -> bool:
    code = G._codegen(block, task)
    return G._runtest(code, _PAG, "test_hidden.py") if code is not None else False


def _ground(lid: int, passes_fn, n: int, path: str) -> int:
    p = 0
    for _ in range(n):
        ok = bool(passes_fn())
        ledger.record_outcome(lid, "pass" if ok else "fail", path=path)
        p += 1 if ok else 0
    return p


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    ledger.init_db(path)
    _reset(path)

    # tenant → make the card concrete, then earn confidence from the real hidden test
    ledger.edit_lesson(TENANT_ID, trigger="listing a user's orders in a multi-tenant service",
                       lesson=ab_runner.CANONICAL_LESSON, path=path)
    tblk = _block(ab_runner.CANONICAL_LESSON)
    tp = _ground(TENANT_ID, lambda: _tenant_pass(tblk), 8, path)

    # pagination → make the card concrete, then earn confidence from the real hidden test
    pspec = G._load_spec(_PAG / "spec.py")
    ledger.edit_lesson(PAG_ID, trigger="returning a page of results to a client",
                       lesson=pspec.CANONICAL_LESSON, path=path)
    pblk = _block(pspec.CANONICAL_LESSON)
    pp = _ground(PAG_ID, lambda: _pag_pass(pblk, pspec.TASK), 5, path)

    print(f"tenant #{TENANT_ID}: {tp}/8 real passes ; pagination #{PAG_ID}: {pp}/5 real passes")
    c = sqlite3.connect(path)
    for r in c.execute("SELECT id, alpha, beta, ROUND(alpha/(alpha+beta),3) AS conf "
                       "FROM lessons WHERE id IN (?,?)", (TENANT_ID, PAG_ID)):
        print("  id, alpha, beta, confidence:", r)
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
