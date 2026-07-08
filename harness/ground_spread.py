"""Ground several EXISTING seeded lessons against their REAL hidden tests, so the live deck shows an
authentic SPREAD of earned confidence instead of a wall of the 0.75 human prior.

Honest by construction: every number is the posterior mean of Beta(alpha, beta) after REAL code-gen +
pytest outcomes. More real evidence -> higher confidence, so grounding a lesson over more rounds
legitimately moves it further from the prior. Lessons without an executable test stay at their prior
(we never fabricate a number).

It grounds the lesson RECALLED for each pattern (found via memory.recall, so it upgrades the existing
seeded card — no duplicate is added):
  * tenant isolation  (ab_runner's real hidden test)      — 8 rounds
  * pagination leak    (patterns/pagination_leak hidden)   — 5 rounds
money_rounding is already grounded by harness.ground_demo (~0.86 + a tombstoned wrong lesson), giving
a spread like 0.86 / 0.89 / 0.92 + one forgotten.

Run:  python -m harness.ground_spread [ledger-path]
"""
from __future__ import annotations

import sys
from pathlib import Path

from backend import config, ledger, memory
from harness import ab_runner
from harness import generalization as G

_PAG = Path(__file__).parent / "patterns" / "pagination_leak"


def _block(lesson: str) -> str:
    return memory.render_injection([{"lesson": lesson, "severity": "high", "source": "human"}])


def _ground_generic(lid: int, lesson: str, task: str, test_dir: Path, test_file: str,
                    n: int, path: str | None) -> int:
    block, passes = _block(lesson), 0
    for _ in range(n):
        code = G._codegen(block, task)
        ok = G._runtest(code, test_dir, test_file) if code is not None else False
        ledger.record_outcome(lid, "pass" if ok else "fail", path=path)
        passes += 1 if ok else 0
    return passes


def _ground_tenant(lid: int, lesson: str, n: int, path: str | None) -> int:
    block, passes = _block(lesson), 0
    for _ in range(n):
        ok = ab_runner._run_pytest(ab_runner._agent_write_code(block))[0]
        ledger.record_outcome(lid, "pass" if ok else "fail", path=path)
        passes += 1 if ok else 0
    return passes


def ground_spread(path: str | None = None) -> list[tuple]:
    out = []
    # pagination — recall the seeded lesson, ground it against its real hidden test
    try:
        pspec = G._load_spec(_PAG / "spec.py")
        hits = memory.recall(pspec.RECALL_CONTEXT, path=path)["lessons"]
        if hits:
            lid, txt = hits[0]["id"], hits[0]["lesson"]
            p = _ground_generic(lid, txt, pspec.TASK, _PAG, "test_hidden.py", 5, path)
            out.append(("pagination", lid, p, 5))
    except Exception as e:                       # one pattern failing must not abort the rest
        out.append(("pagination", None, f"ERR {e}", 0))
    # tenant — recall the seeded lesson, ground it against ab_runner's real hidden test
    try:
        hits = memory.recall(ab_runner.RECALL_CONTEXT, path=path)["lessons"]
        if hits:
            lid, txt = hits[0]["id"], hits[0]["lesson"]
            p = _ground_tenant(lid, txt, 8, path)
            out.append(("tenant", lid, p, 8))
    except Exception as e:
        out.append(("tenant", None, f"ERR {e}", 0))
    return out


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    ledger.init_db(path)
    for name, lid, p, n in ground_spread(path):
        print(f"grounded {name}: lesson #{lid} — {p}/{n} real passes")
