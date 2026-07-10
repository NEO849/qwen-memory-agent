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


def _real_pass(code: str, pdir=_PDIR) -> bool:
    """One real pytest run of a pattern's hidden test against `code`. Deterministic."""
    return G._runtest(code, pdir, "test_hidden.py")


def _lane(name: str, code: str, rule: str, *, trials: int, path: str, pdir=_PDIR) -> dict:
    lid = ledger.add_lesson(rule[:120], rule, scope="payments", severity="high",
                            source="human", path=path)
    l = ledger.get_lesson(lid, path=path)
    curve = [{"trial": 0, "confidence": round(l["confidence"], 4),
              "alpha": l["alpha"], "beta": l["beta"], "event": "human prior Beta(3,1)"}]
    passes = 0
    gate_cross = None
    for t in range(1, trials + 1):
        ok = _real_pass(code, pdir)                             # REAL pytest, every trial
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


# The 5 bug classes whose floor_solution deterministically FAILS its hidden test and whose
# ceiling_solution PASSES it (verified in-repo) — so the demotion is real, class by class.
MULTICLASS = ["email_normalize", "money_rounding", "mutable_default", "pagination_leak", "sql_param"]


def run_multiclass(*, trials: int = 6, path: str) -> dict:
    """Robustness: the SAME demotion+tombstone mechanism across 5 distinct bug classes, not just
    money. Each class injects its plausible-but-wrong fix (floor_solution) and lets real pytest
    refute it. Deterministic, offline, isolated ledger."""
    ledger.init_db(path)
    root = _PDIR.parent
    results = []
    for name in MULTICLASS:
        d = root / name
        wrong = (d / "floor_solution.py").read_text(encoding="utf-8")
        correct = (d / "ceiling_solution.py").read_text(encoding="utf-8")
        assert _real_pass(correct, d) and not _real_pass(wrong, d), f"{name} anchor broke"
        lane = _lane(f"{name}:poisoned", wrong, f"plausible-but-wrong fix for {name}",
                     trials=trials, path=path, pdir=d)
        results.append({"class": name, "gate_cross_trial": lane["gate_cross_trial"],
                        "tombstoned": lane["tombstoned"],
                        "final_confidence": lane["final_confidence"]})
    return {
        "demo": "multi-class poison-demotion — same forgetting mechanism across 5 bug classes",
        "gate": GATE, "trials": trials, "classes": len(results),
        "crossed_gate_after_1_fail": sum(1 for r in results if r["gate_cross_trial"] == 1),
        "tombstoned": sum(1 for r in results if r["tombstoned"]),
        "results": results,
        "honesty": ("Each class's plausible-but-wrong fix (floor_solution) is refuted by real pytest "
                    "(deterministic — floor FAILS / ceiling PASSES its hidden test, verified in-repo). "
                    "Shows demotion+tombstone is not money_rounding-specific. Offline, no Qwen, "
                    "isolated ledger."),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--multiclass", action="store_true", help="run the 5-class robustness variant")
    args = ap.parse_args()
    tmp = str(Path(tempfile.mkdtemp(prefix="poison_")) / "ledger.sqlite")
    if args.multiclass:
        result = run_multiclass(trials=args.trials, path=tmp)
        out = Path(__file__).resolve().parent.parent / "poison_multiclass.json"
    else:
        result = run(trials=args.trials, path=tmp)
        out = Path(__file__).resolve().parent.parent / "poison_curve.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nwritten → {out}")
