"""Hybrid retrieval fusion — BM25 (lexical) + vector cosine (semantic), fused with RRF.

Retrieval fusion adapted from the author's own MIT-licensed markmem (memory_retrieve.py):
the BM25 core (k1=1.5, b=0.75, +1 IDF) and Reciprocal Rank Fusion (K=60, weighted) are
carried over faithfully; the markdown/graph/frontmatter/file-IO coupling is dropped and the
Ollama/bge-m3 vector leg is replaced by an externally-supplied embedding cosine (the caller
passes ready vectors — this module never calls any API).

Pure stdlib. Fail-open: empty docs -> []; no query terms -> vector-only (or [] if no vectors).

MIT License.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

from . import config

_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")


def tokenize(text: str) -> Counter:
    """Lowercase word/identifier tokens of length >= 2 (keeps snake_case ids like tenant_id)."""
    return Counter(_TOKEN_RE.findall((text or "").lower()))


# ---------------------------------------------------------------------- BM25 --
class BM25:
    """Classic BM25 (k1=1.5, b=0.75) over pre-tokenized Counters, keyed by doc id."""

    def __init__(self, corpus: dict[Any, Counter], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = corpus
        self.doc_len = {d: sum(c.values()) for d, c in corpus.items()}
        n = len(corpus) or 1
        self.avgdl = (sum(self.doc_len.values()) / n) if n else 0.0
        df: Counter = Counter()
        for c in corpus.values():
            df.update(c.keys())
        # BM25 IDF with +1 so common terms never contribute negatively.
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def score(self, query_terms: Counter, doc_id: Any) -> float:
        c = self.docs[doc_id]
        dl = self.doc_len[doc_id] or 1
        denom_len = self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
        s = 0.0
        for t in query_terms:
            f = c.get(t, 0)
            if f:
                s += self.idf.get(t, 0.0) * (f * (self.k1 + 1)) / (f + denom_len)
        return s

    def rank(self, query_terms: Counter) -> list[tuple[Any, float]]:
        out = [(d, self.score(query_terms, d)) for d in self.docs]
        out = [(d, s) for d, s in out if s > 0]
        out.sort(key=lambda x: x[1], reverse=True)
        return out


# -------------------------------------------------------------------- VECTOR --
def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if (na and nb) else 0.0


# --- Welle 3: optional vectorized cosine (RG_VECTORIZED) --------------------------------------
# numpy is imported DEFENSIVELY and only used when the flag is on — its absence (or the flag off)
# falls straight back to the scalar path, so the baseline needs no new dependency and stays
# byte-identical. This reduces the CONSTANT factor of the pairwise-cosine hot loops (and unlocks a
# future ANN index); it does NOT change the asymptotics.
_np = None
_np_tried = False


def _numpy():
    global _np, _np_tried
    if not _np_tried:
        _np_tried = True
        try:
            import numpy as _n
            _np = _n
        except Exception:
            _np = None
    return _np


def cosine_scores(query: list[float] | None, embeddings: list[list[float]]) -> list[float]:
    """Cosine of `query` against each vector in `embeddings`, SAME order. Vectorized numpy matmul
    when RG_VECTORIZED (and numpy present); otherwise the scalar `_cosine` path. On real embeddings
    the ranking is identical — the only differences are sub-1e-12 float noise that never crosses a
    threshold or reorders distinct scores."""
    if not query or not embeddings:
        return [0.0] * len(embeddings)
    if config.RG_VECTORIZED:
        np = _numpy()
        if np is not None:
            q = np.asarray(query, dtype=np.float64)
            m = np.asarray(embeddings, dtype=np.float64)
            denom = np.linalg.norm(m, axis=1) * np.linalg.norm(q)
            dots = m @ q
            with np.errstate(divide="ignore", invalid="ignore"):
                scores = np.where(denom > 0, dots / denom, 0.0)
            return scores.tolist()
    return [_cosine(query, e) for e in embeddings]


def vector_rank(query_embedding: list[float] | None,
                docs: list[dict]) -> list[tuple[Any, float]]:
    """Rank docs that carry an 'embedding' by cosine to the query embedding."""
    if not query_embedding:
        return []
    embedded = [d for d in docs if d.get("embedding")]
    scores = cosine_scores(query_embedding, [d["embedding"] for d in embedded])
    out = [(d["id"], s) for d, s in zip(embedded, scores)]
    out.sort(key=lambda x: x[1], reverse=True)
    return out


# ----------------------------------------------------------------------- RRF --
def rrf_fuse(rankings: list[list[tuple[Any, float]]], k: int = 60,
             weights: list[float] | None = None) -> dict[Any, float]:
    """Reciprocal Rank Fusion with optional per-signal weights. Rank-based, so it is
    robust to the different score scales of the lexical and semantic legs."""
    fused: dict[Any, float] = defaultdict(float)
    for idx, ranking in enumerate(rankings):
        w = weights[idx] if (weights and idx < len(weights)) else 1.0
        for rank, (doc_id, _score) in enumerate(ranking, start=1):
            fused[doc_id] += w * (1.0 / (k + rank))
    return fused


# ---------------------------------------------------------------------- CORE --
def fuse(query: str, docs: list[dict], query_embedding: list[float] | None = None,
         weights: dict | None = None, k: int = 10) -> list[tuple]:
    """Fuse BM25 + vector cosine over `docs` and return the top-k.

    docs: [{"id": Any, "text": str, "embedding": list[float] | None}, ...]
    returns: [(id, fused_score, {"bm25_rank": int|None, "vector_rank": int|None}), ...] desc.
    """
    if not docs:
        return []
    w = {"bm25": 1.0, "vector": 1.0, **(weights or {})}

    corpus = {d["id"]: tokenize(d.get("text", "")) for d in docs}
    q_terms = tokenize(query)
    bm_rank = BM25(corpus).rank(q_terms) if q_terms else []
    vec_rank = vector_rank(query_embedding, docs)

    labeled = [(bm_rank, w["bm25"]), (vec_rank, w["vector"])]
    labeled = [(r, wt) for r, wt in labeled if r]
    if not labeled:
        return []
    fused = rrf_fuse([r for r, _ in labeled], weights=[wt for _, wt in labeled])

    bm_pos = {d: i + 1 for i, (d, _) in enumerate(bm_rank)}
    vec_pos = {d: i + 1 for i, (d, _) in enumerate(vec_rank)}
    ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]
    return [(doc_id, score, {"bm25_rank": bm_pos.get(doc_id), "vector_rank": vec_pos.get(doc_id)})
            for doc_id, score in ranked]


if __name__ == "__main__":
    docs = [
        {"id": 1, "text": "always filter tenant scoped queries by tenant_id", "embedding": None},
        {"id": 2, "text": "parse dates with a timezone aware library", "embedding": None},
        {"id": 3, "text": "close file handles to avoid descriptor leaks", "embedding": None},
    ]
    res = fuse("query leaks rows across tenant_id boundary", docs, k=3)
    print("BM25-only fusion (expect doc 1 top):")
    for doc_id, score, ex in res:
        print(f"  id={doc_id} score={score:.5f} {ex}")
