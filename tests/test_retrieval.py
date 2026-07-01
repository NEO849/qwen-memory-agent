"""Retrieval fusion — offline (BM25 + dummy-vector cosine + RRF)."""
from backend import retrieval


DOCS = [
    {"id": 1, "text": "always filter tenant scoped queries by tenant_id", "embedding": None},
    {"id": 2, "text": "parse dates with a timezone aware library", "embedding": None},
    {"id": 3, "text": "close file handles to avoid descriptor leaks", "embedding": None},
]


def test_bm25_ranks_relevant_doc_first():
    res = retrieval.fuse("rows leak across tenant_id boundary", DOCS, k=3)
    assert res[0][0] == 1


def test_empty_docs_is_failopen():
    assert retrieval.fuse("anything", [], k=3) == []


def test_no_query_terms_no_vectors_returns_empty():
    # query has no usable tokens and no embedding -> nothing to rank
    assert retrieval.fuse("!!! ??? ...", DOCS, k=3) == []


def test_vector_arm_ranks_by_cosine():
    docs = [
        {"id": 1, "text": "alpha", "embedding": [1.0, 0.0]},
        {"id": 2, "text": "beta", "embedding": [0.0, 1.0]},
    ]
    # query embedding points at doc 1's direction; query text is non-matching noise
    res = retrieval.fuse("zzz", docs, query_embedding=[0.9, 0.1], k=2)
    assert res[0][0] == 1
    assert res[0][2]["vector_rank"] == 1


def test_rrf_fuse_weighting():
    r1 = [("a", 9.0), ("b", 1.0)]
    r2 = [("b", 9.0), ("a", 1.0)]
    # equal weights -> tie; heavier weight on r2 -> b wins
    fused_equal = retrieval.rrf_fuse([r1, r2])
    assert abs(fused_equal["a"] - fused_equal["b"]) < 1e-9
    fused_w = retrieval.rrf_fuse([r1, r2], weights=[1.0, 3.0])
    assert fused_w["b"] > fused_w["a"]
