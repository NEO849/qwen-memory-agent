"""Calibration — the Beta confidence is honestly calibrated, not decorative.

Two properties a bare similarity score (RAG cosine) structurally cannot have, because a cosine is
not a probability and makes no falsifiable claim:

  1. Convergence — as real outcomes accumulate, a lesson's confidence converges to its TRUE
     pass-rate. The posterior mean tracks reality.
  2. Calibration — across many lessons, displayed confidence matches the empirical pass-rate:
     the Expected Calibration Error (ECE) is small. Confidence here is a probability and we verify
     it behaves like one.

Pure math over `confidence.posterior_mean`, deterministic (seeded RNG) — no Qwen, no network.
This is the mathematical backbone of the "earned, not the model's opinion" thesis.
"""
from __future__ import annotations

import random

from backend import confidence


def _simulate(true_p: float, n: int, rng: random.Random) -> float:
    """Feed n Bernoulli(true_p) outcomes to a fresh Beta(1,1) lesson, return its confidence."""
    a, b = 1.0, 1.0
    for _ in range(n):
        if rng.random() < true_p:
            a += 1.0
        else:
            b += 1.0
    return confidence.posterior_mean(a, b)


def test_confidence_converges_to_true_pass_rate():
    rng = random.Random(7)
    for p in (0.15, 0.40, 0.60, 0.85, 0.97):
        est = _simulate(p, 3000, rng)
        assert abs(est - p) < 0.03, f"p={p} did not converge (est={est:.3f})"


def test_expected_calibration_error_is_small():
    rng = random.Random(42)
    N, obs, bins = 4000, 30, 10
    preds: list[float] = []
    actuals: list[float] = []
    for _ in range(N):
        true_p = rng.random()
        c = _simulate(true_p, obs, rng)                        # displayed confidence
        held_out = 1.0 if rng.random() < true_p else 0.0       # the next real outcome
        preds.append(c)
        actuals.append(held_out)

    ece = 0.0
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        idx = [j for j, c in enumerate(preds)
               if lo <= c < hi or (i == bins - 1 and c >= hi)]
        if not idx:
            continue
        conf = sum(preds[j] for j in idx) / len(idx)
        acc = sum(actuals[j] for j in idx) / len(idx)
        ece += abs(conf - acc) * len(idx) / N

    assert ece < 0.06, f"Beta confidence is miscalibrated (ECE={ece:.3f})"
