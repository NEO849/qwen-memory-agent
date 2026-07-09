"""Poison-Demotion-Kurve — die Kern-These NUMERISCH statt binär.

Everyone can SAY "our memory forgets what's wrong". This measures it: a plausible-but-WRONG
lesson loses confidence trial by trial as real pytest runs refute it (Beta posterior mean),
crosses the injection gate (0.62 — below it the lesson is no longer injected), and is finally
tombstoned (forgotten). A CORRECT lesson, driven by the same machinery, climbs. Every single
confidence step is produced by a REAL pytest run of the `money_rounding` pattern:

    ceiling_solution (integer cents)  -> hidden test GREEN -> pass -> alpha += 1 -> confidence up
    floor_solution   (float dollars)  -> hidden test RED   -> fail -> beta  += 1 -> confidence down

Honest by construction: no Qwen, no fabricated jumps, isolated throwaway ledger (no prod write),
deterministic + reproducible. This is the same record_outcome path the live system uses.

Run:  python -m harness.poison_curve --trials 6
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from backend import ledger
from harness import generalization as G

_PDIR = Path(__file__).parent / "patterns" / "money_rounding"
CORRECT_CODE = (_PDIR / "ceiling_solution.py").read_text(encoding="utf-8")
WRONG_CODE = (_PDIR / "floor_solution.py").read_text(encoding="utf-8")

GATE = 0.62   # a-priori injection threshold (RG_MIN_CONFIDENCE in the honest 3-arm benchmark)


def _real_pass(code: str) -> bool:
    """One real pytest run of the hidden money test against `code`. Deterministic."""
    return G._runtest(code, _PDIR, "test_hidden.py")


def _lane(name: str, code: str, rule: str, *, trials: int, path: str) -> dict:
    lid = ledger.add_lesson(rule[:120], rule, scope="payments", severity="high",
                            source="human", path=path)
    l = ledger.get_lesson(lid, path=path)
    curve = [{"trial": 0, "confidence": round(l["confidence"], 4),
              "alpha": l["alpha"], "beta": l["beta"], "event": "human prior Beta(3,1)"}]
    passes = 0
    gate_cross = None
    for t in range(1, trials + 1):
        ok = _real_pass(code)                                   # REAL pytest, every trial
        l = ledger.record_outcome(lid, "pass" if ok else "fail", path=path)
        passes += int(ok)
        conf = l["confidence"]
        event = None
        if gate_cross is None and conf < GATE:
            gate_cross = t
            event = f"crossed below inject-gate {GATE} → no longer injected"
        curve.append({"trial": t, "real_test": "pass" if ok else "fail",
                      "confidence": round(conf, 4), "alpha": l["alpha"],
                      "beta": l["beta"], "event": event})
    tombstoned = False
    if passes == 0:                                             # refuted by every real test → forget
        ledger.tombstone(lid, path=path)
        tombstoned = True
        curve[-1]["event"] = "tombstoned (forgotten — 0/{} real passes)".format(trials)
    return {"lesson_id": lid, "passes": passes, "trials": trials,
            "gate_cross_trial": gate_cross, "tombstoned": tombstoned,
            "final_confidence": round(ledger.get_lesson(lid, path=path)["confidence"], 4),
            "curve": curve}


def run(*, trials: int = 6, path: str) -> dict:
    ledger.init_db(path)
    # Anchor: confirm the pattern really behaves as claimed before trusting the curve.
    anchor = {"ceiling_passes": _real_pass(CORRECT_CODE),
              "floor_passes": _real_pass(WRONG_CODE)}
    assert anchor["ceiling_passes"] and not anchor["floor_passes"], \
        f"pattern anchor broke: {anchor} (expected ceiling GREEN, floor RED)"
    return {
        "demo": ("poison-demotion-curve — mechanism demo (ONE deterministic pattern, the same "
                 "real pytest repeated each trial; a Beta-accounting curve, NOT a population "
                 "benchmark and NOT independent samples)"),
        "gate": GATE,
        "anchor": anchor,
        "correct": _lane("correct", CORRECT_CODE,
                         "Money is integer cents: sum price_cents*quantity as ints, /100 once.",
                         trials=trials, path=path),
        "poisoned": _lane("poisoned", WRONG_CODE,
                          "For a cart total, add each line as float dollars into a running total.",
                          trials=trials, path=path),
        "honesty": ("Every confidence step is driven by a REAL pytest run of the money_rounding "
                    "pattern (ceiling=integer cents=GREEN, floor=float dollars=RED). Same "
                    "record_outcome path + same wp==0 tombstone rule as the live system. Offline, "
                    "no Qwen/LLM, isolated ledger, no prod write, deterministic + reproducible. "
                    "NOTE: a single real failure only DE-INJECTS a lesson (drops it below the "
                    "gate); tombstoning (permanent forget) is the terminal case after sustained "
                    "refutation (0 passes). The trials repeat ONE deterministic test — this is a "
                    "mechanism demo, not independent sampling."),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=6)
    args = ap.parse_args()
    tmp = str(Path(tempfile.mkdtemp(prefix="poison_")) / "ledger.sqlite")
    result = run(trials=args.trials, path=tmp)
    out = Path(__file__).resolve().parent.parent / "poison_curve.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nwritten → {out}")
