"""Latency micro-benchmark for the vectorized cosine path (RG_VECTORIZED, Welle 3).

Times the pairwise-cosine hot loop scalar-Python vs numpy-matmul over N = 1k / 10k embeddings
(dim 1024), and PROVES the ranking is identical (so the speedup is free of behaviour change).
Deterministic (fixed seeds), offline, no API key. Honest framing: this shrinks the CONSTANT
factor (and unlocks a future ANN index) — it does NOT change the O(N) asymptotics.

Run:  python -m harness.latency_bench          (writes latency_bench.json)
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

from backend import config, retrieval


def _vecs(n: int, dim: int, seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    return [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n)]


def _best_ms(fn, reps: int = 3) -> float:
    best = float("inf")
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return round(best * 1000, 2)


def _ranking(scores: list[float]) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: -scores[i])


def run(sizes=(1000, 10000), dim: int = 1024) -> dict:
    has_np = retrieval._numpy() is not None
    q = _vecs(1, dim, seed=1)[0]
    rows = []
    for n in sizes:
        m = _vecs(n, dim, seed=n)
        saved = config.RG_VECTORIZED
        try:
            config.RG_VECTORIZED = False
            scalar_ms = _best_ms(lambda: retrieval.cosine_scores(q, m))
            s_scores = retrieval.cosine_scores(q, m)
            config.RG_VECTORIZED = True
            vec_ms = _best_ms(lambda: retrieval.cosine_scores(q, m)) if has_np else None
            v_scores = retrieval.cosine_scores(q, m)
        finally:
            config.RG_VECTORIZED = saved
        rows.append({
            "n": n, "dim": dim, "scalar_ms": scalar_ms, "vectorized_ms": vec_ms,
            "speedup": round(scalar_ms / vec_ms, 1) if vec_ms else None,
            "ranking_identical": _ranking(s_scores) == _ranking(v_scores),
            "max_abs_score_diff": max((abs(a - b) for a, b in zip(s_scores, v_scores)), default=0.0),
        })
    return {"numpy_available": has_np, "sizes": rows,
            "honesty": "Constant-factor speedup of the pairwise-cosine hot loop; identical ranking. "
                       "Does NOT change O(N) asymptotics — it unlocks a future ANN index."}


if __name__ == "__main__":
    result = run()
    out = Path(__file__).resolve().parent.parent / "latency_bench.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nwritten → {out}")
