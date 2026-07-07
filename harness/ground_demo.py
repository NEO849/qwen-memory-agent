"""Make the core loop VISIBLE on the live instance.

The whole thesis — confidence is EARNED from real pytest outcomes, and a lesson refuted by real
tests is forgotten — is fully built and tested, but on a fresh demo ledger every lesson is still a
prior (grounded_outcomes = 0). This grounds a couple of lessons against a REAL hidden test so the
deployed memory demonstrates its own loop:

  * a CORRECT lesson (money = integer cents) → real passes → earned high confidence, node validated
  * a WRONG lesson  (money = float dollars)  → real fails  → confidence drops → tombstoned (belief
    revision, a grey "forgotten" node with real_fail > 0)

It uses the money_rounding pattern (a task independent of the get_orders demo), so the live
red→teach→green money-shot and the /duel A/B are untouched.

Run:  python -m harness.ground_demo [ledger-path]
"""
from __future__ import annotations

import sys
from pathlib import Path

from backend import config, ledger, memory
from harness import generalization as G

_PDIR = Path(__file__).parent / "patterns" / "money_rounding"
_TASK = G._load_spec(_PDIR / "spec.py").TASK

CORRECT = ("computing a cart or invoice total",
           "Money is integer cents, never float dollars. In cart_total, sum "
           "item['price_cents'] * item['quantity'] as integers, then divide by 100 once at the end.")
WRONG = ("computing a cart or invoice total",
         "For a cart total, add each line as float dollars (item['price_cents'] / 100 * "
         "item['quantity']) into a running float total and return it.")


def _ground(trigger: str, rule: str, n: int, path: str | None) -> tuple[int, int]:
    """Add a lesson, then run n real code-gen+pytest rounds injecting it and record the REAL outcomes."""
    l = memory.add_note(f"{trigger}: {rule}", scope="payments", severity="high",
                        author="seed", check_conflicts=False, path=path)
    lid = l["id"]
    ledger.edit_lesson(lid, trigger=trigger, lesson=rule, path=path)
    block = memory.render_injection([{"lesson": rule, "severity": "high",
                                      "source": "human", "scope": "payments"}])
    passes = 0
    for _ in range(n):
        code = G._codegen(block, _TASK)
        ok = G._runtest(code, _PDIR, "test_hidden.py") if code is not None else False
        ledger.record_outcome(lid, "pass" if ok else "fail", path=path)
        passes += 1 if ok else 0
    return lid, passes


def ground(path: str | None = None) -> dict:
    cid, cp = _ground(CORRECT[0], CORRECT[1], 3, path)
    wid, wp = _ground(WRONG[0], WRONG[1], 3, path)
    tombstoned = False
    if wp == 0:                                        # refuted by every real test → forget it
        ledger.tombstone(wid, superseded_by=cid, path=path)
        tombstoned = True
    return {"correct_id": cid, "correct_pass": cp, "wrong_id": wid, "wrong_pass": wp,
            "wrong_tombstoned": tombstoned}


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    ledger.init_db(p)
    r = ground(p)
    print(f"grounded — correct #{r['correct_id']} {r['correct_pass']}/3 pass; "
          f"wrong #{r['wrong_id']} {r['wrong_pass']}/3 pass -> "
          f"{'tombstoned (forgotten)' if r['wrong_tombstoned'] else 'kept'}")
