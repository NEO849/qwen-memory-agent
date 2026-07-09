"""Welle 3 — vectorized cosine (RG_VECTORIZED) is numerically faithful to the scalar baseline.

OFF == scalar `_cosine` exactly. ON (numpy) == scalar ranking, sub-1e-12 score noise. If numpy is
absent the ON path falls back to scalar (no new hard dependency)."""
import random

import pytest

from backend import config, retrieval


def _vecs(n, dim=64, seed=3):
    rng = random.Random(seed)
    return [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n)]


def test_off_is_exact_scalar(monkeypatch):
    monkeypatch.setattr(config, "RG_VECTORIZED", False)
    q, m = _vecs(1)[0], _vecs(12)
    assert retrieval.cosine_scores(q, m) == [retrieval._cosine(q, e) for e in m]


@pytest.mark.skipif(retrieval._numpy() is None, reason="numpy not installed")
def test_on_matches_scalar_ranking_and_values(monkeypatch):
    q, m = _vecs(1)[0], _vecs(50)
    monkeypatch.setattr(config, "RG_VECTORIZED", False)
    scalar = retrieval.cosine_scores(q, m)
    monkeypatch.setattr(config, "RG_VECTORIZED", True)
    vec = retrieval.cosine_scores(q, m)
    assert max(abs(a - b) for a, b in zip(scalar, vec)) < 1e-12
    order = lambda s: sorted(range(len(s)), key=lambda i: -s[i])
    assert order(scalar) == order(vec)                       # identical ranking → no behaviour change


@pytest.mark.skipif(retrieval._numpy() is None, reason="numpy not installed")
def test_vector_rank_parity(monkeypatch):
    q = _vecs(1)[0]
    docs = [{"id": i, "embedding": e} for i, e in enumerate(_vecs(30))]
    monkeypatch.setattr(config, "RG_VECTORIZED", False)
    off = [i for i, _ in retrieval.vector_rank(q, docs)]
    monkeypatch.setattr(config, "RG_VECTORIZED", True)
    on = [i for i, _ in retrieval.vector_rank(q, docs)]
    assert off == on


def test_empty_inputs_safe(monkeypatch):
    monkeypatch.setattr(config, "RG_VECTORIZED", True)
    assert retrieval.cosine_scores([], [[1.0]]) == [0.0]
    assert retrieval.cosine_scores([1.0], []) == []


def test_latency_bench_ranking_identical():
    from harness import latency_bench
    r = latency_bench.run(sizes=(200,), dim=64)          # tiny sizes → fast, still proves parity
    assert r["sizes"][0]["ranking_identical"] is True
    assert r["sizes"][0]["max_abs_score_diff"] < 1e-9
