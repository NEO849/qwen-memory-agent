"""Gate-threshold sweep — is the 0.62 injection gate cherry-picked? (offline, no Qwen, deterministic)

A skeptic's fair question: "you chose 0.62 because it makes your numbers look good." This answers it.
For each bug class we ground a CORRECT lesson (ceiling_solution → real pytest passes → high Beta
confidence) and a POISONED one (floor_solution → real pytest fails → low confidence), exactly like
the poison curve. Then we sweep the injection gate 0.30–0.90 and report, at each threshold, how many
CORRECT lessons get injected (want: all) vs POISONED lessons injected (want: none, i.e. harmful).

If a WIDE band of thresholds cleanly separates good from bad, then 0.62 sits on a robust plateau —
the result is insensitive to the exact gate, so it is NOT cherry-picked. Same real record_outcome
math the live gate uses. Run:  python -m harness.gate_sweep
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend import confidence
from harness.poison_curve import MULTICLASS, _PDIR, _real_pass

GATES = [0.30, 0.40, 0.50, 0.62, 0.70, 0.80, 0.90]


def _ground_conf(code: str, pdir: Path, trials: int) -> float:
    """Beta(1,1) prior + real pytest outcomes → posterior mean (the live gate's own math)."""
    passes = sum(1 for _ in range(trials) if _real_pass(code, pdir))
    return confidence.posterior_mean(1 + passes, 1 + (trials - passes))


def run(*, trials: int = 6) -> dict:
    root = _PDIR.parent
    correct, poison = [], []
    for name in MULTICLASS:
        d = root / name
        correct.append(_ground_conf((d / "ceiling_solution.py").read_text(encoding="utf-8"), d, trials))
        poison.append(_ground_conf((d / "floor_solution.py").read_text(encoding="utf-8"), d, trials))
    n = len(MULTICLASS)
    sweep = []
    for g in GATES:
        ic = sum(1 for c in correct if c >= g)
        ip = sum(1 for c in poison if c >= g)
        sweep.append({"gate": g, "correct_injected": ic, "poison_injected": ip,
                      "clean": ic == n and ip == 0})
    clean = [s["gate"] for s in sweep if s["clean"]]
    return {
        "demo": "gate-threshold sweep — robustness of the 0.62 injection gate (offline, real pytest)",
        "trials": trials, "n_classes": n,
        "correct_confidences": [round(c, 3) for c in correct],
        "poison_confidences": [round(c, 3) for c in poison],
        "sweep": sweep,
        "clean_band": [min(clean), max(clean)] if clean else None,
        "gate_0_62_clean": any(s["gate"] == 0.62 and s["clean"] for s in sweep),
        "honesty": ("Correct lessons ground to high confidence, poisoned to low, on real pytest "
                    "(Beta(1,1)+outcomes = the live gate's math). A wide clean band means the exact "
                    "gate barely matters — 0.62 is a robust choice, not cherry-picked. Deterministic, "
                    "no Qwen, isolated ledgers. Small N per lesson (illustrative)."),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=6)
    args = ap.parse_args()
    r = run(trials=args.trials)
    out = Path(__file__).resolve().parent.parent / "gate_sweep.json"
    out.write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))
    print(f"\nwritten → {out}")
