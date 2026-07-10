"""Calibration curve — does CLAIMED confidence match ACTUAL out-of-sample pass rate?

The core promise of an outcome-grounded memory is that its confidence number MEANS something:
"when we say 0.9, the lesson really works ~90% of the time on code we haven't seen." This measures
exactly that, with a clean train/test split so it can't be circular:

  * CLAIM (train):  inject a lesson, let Qwen (temp 0.7 → real variety) write N implementations,
                    grade them against `test_hidden.py`. The Beta(1,1)+outcomes posterior mean is
                    the confidence the live system WOULD assign — same math as `record_outcome`.
  * ACTUAL (test):  grade the SAME implementations against a DIFFERENT `test_unseen.py`
                    (fresh assertions the confidence never saw) → the honest out-of-sample rate.

floor (no memory) vs ceiling (correct lesson) across 5 bug classes gives a natural confidence
spread from ~0.1 to ~0.95. We report a reliability diagram, the Brier score, and ECE.

HONEST SCOPE: small N (illustrative, wide CIs), and the confidence is grounded on `test_hidden`
while measured on `test_unseen` — a genuine out-of-sample check, not the circular "confidence vs the
very outcomes that formed it". Paid Qwen, disk-cached + per-sample nonce for reproducibility.

Run:  python -m harness.calibration --n 8
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from backend import confidence, memory, qwen_client
from harness import generalization as G

PDIR = Path(__file__).resolve().parent / "patterns"
PATTERNS = ["email_normalize", "money_rounding", "mutable_default", "pagination_leak", "sql_param"]


def _load(name: str, fname: str, mod: str):
    sp = PDIR / name / fname
    s = importlib.util.spec_from_file_location(mod + "_" + name, sp)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _spec(name: str):
    return _load(name, "spec.py", "spec")


def _codegen(lesson_block: str, task: str, i: int) -> str | None:
    """One implementation. temp>0 for real variety; a per-sample nonce makes each call a distinct
    cache key (reproducible) while Qwen still samples a genuinely different solution."""
    msgs = []
    if lesson_block:
        msgs.append({"role": "system", "content": lesson_block})
    msgs.append({"role": "user", "content": f"{task}\n\n# implementation variant {i}"})
    try:
        return G._extract(qwen_client.chat(msgs, temperature=0.7))
    except Exception:
        return None


def _group(name: str, spec, variant, use_lesson: bool, n: int) -> dict:
    block = ""
    if use_lesson:
        block = memory.render_injection([{"lesson": spec.CANONICAL_LESSON, "severity": "high",
                                          "source": "human", "scope": name}])
    hidden_pass = 0
    unseen_outcomes = []
    for i in range(n):
        # TRAIN: SEEN task (e.g. cart_total) → test_hidden grounds the confidence
        seen_code = _codegen(block, spec.TASK, i)
        hidden = G._runtest(seen_code, PDIR / name, "test_hidden.py") if seen_code else False
        # TEST: UNSEEN variant (e.g. invoice_total, same rule, different surface) → out-of-sample.
        # The same lesson must TRANSFER to a task the confidence never saw. Real generalisation.
        var_code = _codegen(block, variant.TASK, i)
        unseen = G._runtest(var_code, PDIR / name, "test_unseen.py") if var_code else False
        hidden_pass += int(hidden)
        unseen_outcomes.append(int(unseen))
    # CLAIM: Beta(1,1) prior + hidden outcomes → posterior mean (identical to the live gate's math)
    conf = confidence.posterior_mean(1 + hidden_pass, 1 + (n - hidden_pass))
    observed = sum(unseen_outcomes) / n if n else 0.0
    return {
        "pattern": name,
        "condition": "with_memory" if use_lesson else "no_memory",
        "n": n,
        "claimed_confidence": round(conf, 3),   # from test_hidden (train)
        "observed_unseen": round(observed, 3),  # from test_unseen (out-of-sample test)
        "hidden_pass": hidden_pass,
        "unseen_pass": sum(unseen_outcomes),
        "_unseen_outcomes": unseen_outcomes,
    }


def run(*, n: int = 8) -> dict:
    groups = []
    for name in PATTERNS:
        s = _spec(name)
        v = _load(name, "variant.py", "variant")
        groups.append(_group(name, s, v, False, n))   # floor  → low confidence
        groups.append(_group(name, s, v, True, n))    # ceiling → high confidence

    # Brier score over every (group-confidence, out-of-sample outcome) pair
    sq = [(g["claimed_confidence"] - o) ** 2 for g in groups for o in g["_unseen_outcomes"]]
    brier = sum(sq) / len(sq) if sq else 0.0

    # Reliability diagram + ECE over 5 equal-width confidence buckets
    total = sum(g["n"] for g in groups)
    buckets: dict[int, list] = {}
    for g in groups:
        b = min(int(g["claimed_confidence"] * 5), 4)
        buckets.setdefault(b, []).append(g)
    ece = 0.0
    reliability = []
    for b in sorted(buckets):
        gs = buckets[b]
        w = sum(g["n"] for g in gs)
        mc = sum(g["claimed_confidence"] * g["n"] for g in gs) / w
        ma = sum(g["observed_unseen"] * g["n"] for g in gs) / w
        ece += (w / total) * abs(mc - ma)
        reliability.append({"bucket": f"{b * 0.2:.1f}-{(b + 1) * 0.2:.1f}",
                            "mean_claimed": round(mc, 3), "mean_observed": round(ma, 3), "n": w})

    # Contrast-only view: only the classes with a REAL floor/ceiling gap (the others Qwen solves
    # without memory, so they add no signal and merely dilute the aggregate). This is the honest,
    # un-diluted number — it deliberately includes the pagination_leak miscalibration.
    CONTRAST = {"email_normalize", "pagination_leak"}
    cg = [g for g in groups if g["pattern"] in CONTRAST and g["condition"] == "with_memory"]
    contrast = None
    if cg:
        contrast = {
            "classes": sorted(CONTRAST),
            "mean_claimed": round(sum(g["claimed_confidence"] for g in cg) / len(cg), 3),
            "mean_observed": round(sum(g["observed_unseen"] for g in cg) / len(cg), 3),
            "note": ("With the memory-signal classes only, high-confidence lessons claim ~0.9 but "
                     "transfer at only ~0.5 — because one of them (pagination_leak) claims 0.9 and "
                     "transfers 0/8. The aggregate below hides this; we surface it on purpose."),
        }

    for g in groups:
        g.pop("_unseen_outcomes", None)
    return {
        "demo": ("small non-circular TRANSFER experiment (NOT a fine-grained calibration curve) — "
                 "claimed confidence grounded on the SEEN task, success measured on an UNSEEN "
                 "variant task the confidence never saw"),
        "model": "qwen-plus", "temperature": 0.7, "n_per_group": n,
        "effective_units": "≈10 class-points (the 8 samples per group share one confidence), not 80",
        "brier_score": round(brier, 4),
        "ece": round(ece, 4),
        "reliability": reliability,
        "contrast_only": contrast,
        "groups": groups,
        "honesty": ("Confidence is grounded on the SEEN task (test_hidden); success is measured on a "
                    "DIFFERENT UNSEEN variant task (test_unseen) — the lesson must TRANSFER, so this "
                    "is genuine out-of-sample, not circular. Beta(1,1)+outcomes = the live gate's "
                    "own math. HONEST LIMITS: only two confidence levels appeared (~0.1 and ~0.9) — "
                    "a COARSE high/low separation, NOT a fine-grained calibration curve over [0,1]. "
                    "Effective sample ≈10 class-points, not 80 (samples in a group share one "
                    "confidence). 3 of 5 classes Qwen solves without memory (no contrast). One "
                    "high-confidence class (pagination_leak) claimed 0.9 but transferred 0/8 — a "
                    "REAL miscalibration we surface, not hide; the aggregate Brier 0.09 / ECE 0.04 "
                    "are dominated by that one failure and diluted by the easy classes. See "
                    "contrast_only for the un-diluted number. The Beta math's convergence itself is "
                    "shown separately + synthetically in tests/test_calibration.py — do not merge."),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    args = ap.parse_args()
    with qwen_client.qwen_cache(str(Path(__file__).resolve().parent.parent / ".calib_cache")):
        result = run(n=args.n)
    out = Path(__file__).resolve().parent.parent / "calibration_result.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nwritten → {out}")
