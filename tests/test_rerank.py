"""qwen3-rerank client — parsing, caching, and graceful degradation. Mocked (no paid calls)."""
import types

import pytest

from backend import qwen_client as qc


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(qc, "_breaker", qc._Breaker(qc._CB_THRESHOLD, qc._CB_COOLDOWN))
    monkeypatch.setattr(qc.time, "sleep", lambda *_: None)


def _resp(status, payload):
    return types.SimpleNamespace(status_code=status, json=lambda: payload,
                                 text="", request=None)


def test_rerank_parses_and_caches(monkeypatch, tmp_path):
    calls = {"n": 0}
    def post(*a, **k):
        calls["n"] += 1
        return _resp(200, {"results": [{"index": 2, "relevance_score": 0.9},
                                       {"index": 0, "relevance_score": 0.4}]})
    monkeypatch.setattr(qc.httpx, "post", post)
    with qc.qwen_cache(str(tmp_path)):
        r1 = qc.rerank("q", ["a", "b", "c"], top_n=2)
        r2 = qc.rerank("q", ["a", "b", "c"], top_n=2)
    assert r1 == [(2, 0.9), (0, 0.4)]
    assert r2 == r1 and calls["n"] == 1          # second call served from cache


def test_rerank_graceful_on_transport_error(monkeypatch):
    def post(*a, **k):
        raise qc.httpx.ConnectError("reranker down")
    monkeypatch.setattr(qc.httpx, "post", post)
    assert qc.rerank("q", ["a", "b"]) == []        # graceful -> empty -> caller keeps RRF order


def test_rerank_graceful_on_4xx(monkeypatch):
    def post(*a, **k):
        return _resp(400, {"code": "InvalidParameter"})
    monkeypatch.setattr(qc.httpx, "post", post)
    assert qc.rerank("q", ["a"]) == []             # bad request -> no retry storm, empty result


def test_rerank_empty_input():
    assert qc.rerank("q", []) == []
