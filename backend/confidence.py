"""Outcome-grounded confidence — a Beta-Bayes model driven by real test pass/fail.

This is the differentiator: a lesson's confidence is NOT an LLM's opinion, it is the
posterior mean of a Beta(alpha, beta) distribution updated from actual pytest outcomes
(pass -> alpha+1, fail -> beta+1; the update itself lives in ledger.record_outcome as an
atomic in-SQL increment). Here we keep the pure, testable math + the injection policy.

A fresh lesson starts Beta(1, 1) -> mean 0.50 (maximal uncertainty). Every real green run
sharpens the distribution and pushes the mean up; a red run pushes it down. Honest numbers,
no faked jumps.
"""
from __future__ import annotations


def posterior_mean(alpha: float, beta: float) -> float:
    """E[Beta(alpha, beta)] = alpha / (alpha + beta)."""
    total = alpha + beta
    return alpha / total if total else 0.0


def posterior_variance(alpha: float, beta: float) -> float:
    """Var[Beta] — shrinks as evidence accumulates. Used for 'how sure are we' displays."""
    total = alpha + beta
    if total <= 0:
        return 0.0
    return (alpha * beta) / (total * total * (total + 1.0))


def evidence_count(alpha: float, beta: float) -> float:
    """Number of real observations behind a lesson (priors excluded)."""
    return max(0.0, (alpha - 1.0)) + max(0.0, (beta - 1.0))


def should_inject(lesson: dict, *, threshold: float = 0.0) -> bool:
    """Injection policy. Pinned lessons bypass the confidence gate (human override).
    Otherwise inject active lessons whose posterior mean clears the threshold.
    Obsolete (tombstoned) lessons are never injected."""
    if lesson.get("status") == "obsolete":
        return False
    if lesson.get("pinned"):
        return True
    return lesson.get("confidence", 0.0) >= threshold


def beta_pdf(alpha: float, beta: float, x: float) -> float:
    """Unnormalized-safe Beta PDF value at x in [0,1] — used to sanity-check the
    frontend sparkline. Clamps degenerate params so it never divides by zero."""
    import math

    a = max(alpha, 1e-6)
    b = max(beta, 1e-6)
    x = min(max(x, 1e-9), 1.0 - 1e-9)
    log_pdf = (
        (a - 1.0) * math.log(x)
        + (b - 1.0) * math.log(1.0 - x)
        + math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
    )
    return math.exp(log_pdf)


if __name__ == "__main__":
    for (a, b) in [(1, 1), (2, 1), (4, 1), (3, 5)]:
        print(f"Beta({a},{b})  mean={posterior_mean(a, b):.3f}  "
              f"var={posterior_variance(a, b):.4f}  evidence={evidence_count(a, b):.0f}")
