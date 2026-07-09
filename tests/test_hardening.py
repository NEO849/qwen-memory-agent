"""Welle 0 — Robustheit der Live-API (kein Flag, byte-identisches Verhalten).

Deckt ab:
  * ASGI-Body-Byte-Grenze (`_MaxBodySizeMiddleware`) — rejects oversize auch OHNE
    Content-Length (chunked-Bypass) und liefert kleine Bodies byte-identisch weiter (replay).
  * Rate-Limit-Bucket-Eviction (`_sweep_buckets`) — idle IPs werden entfernt (bounded memory).
  * Lifespan-Boot — die App startet über den lifespan-Handler und antwortet auf /health.
Voll gemockt / in-process, keine bezahlten Qwen-Calls.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from backend.main import _MaxBodySizeMiddleware


# --- ASGI middleware in Isolation: Integrität + Byte-Grenze -------------------

async def _echo_app(scope, receive, send):
    """Trivialer Inner-ASGI: liest den ganzen Body und antwortet mit dessen Länge."""
    body = b""
    while True:
        m = await receive()
        if m["type"] == "http.request":
            body += m.get("body", b"")
            if not m.get("more_body"):
                break
        elif m["type"] == "http.disconnect":
            break
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": str(len(body)).encode()})


async def _drive(max_body, chunks):
    """Treibt _MaxBodySizeMiddleware mit einer Chunk-Folge OHNE Content-Length (chunked)."""
    scope = {"type": "http", "method": "POST", "path": "/x", "headers": []}
    msgs = [{"type": "http.request", "body": c, "more_body": i < len(chunks) - 1}
            for i, c in enumerate(chunks)]
    it = iter(msgs)

    async def receive():
        try:
            return next(it)
        except StopIteration:
            return {"type": "http.disconnect"}

    sent = []

    async def send(m):
        sent.append(m)

    mw = _MaxBodySizeMiddleware(_echo_app, max_body=max_body)
    await mw(scope, receive, send)
    return sent


def _status(sent):
    return next(m["status"] for m in sent if m["type"] == "http.response.start")


def _body(sent):
    return b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")


def test_small_body_passes_through_byte_identical():
    sent = asyncio.run(_drive(64 * 1024, [b"a" * 100, b"b" * 50]))   # 150 bytes, no CL header
    assert _status(sent) == 200
    assert _body(sent) == b"150"           # inner app saw exactly 150 bytes → replay is intact


def test_oversize_chunked_body_rejected_without_content_length():
    # 70 KB in chunks, no Content-Length at all — the header check can't see this.
    sent = asyncio.run(_drive(64 * 1024, [b"x" * (10 * 1024)] * 7))
    assert _status(sent) == 413


def test_limit_boundary_exact_ok_one_over_rejected():
    assert _status(asyncio.run(_drive(1000, [b"z" * 1000]))) == 200
    assert _status(asyncio.run(_drive(1000, [b"z" * 1001]))) == 413


# --- Rate-Limit-Bucket-Eviction ----------------------------------------------

def test_sweep_evicts_idle_ip_keeps_active(monkeypatch):
    from collections import deque
    monkeypatch.setattr(main, "_last_sweep", 0.0)
    now = 10_000.0
    main._hits.clear()
    main._hits["idle"] = deque([now - 500])       # window (60s) long elapsed → evict
    main._hits["active"] = deque([now - 5])        # inside window → keep
    main._sweep_buckets(now)
    assert "idle" not in main._hits
    assert "active" in main._hits


def test_sweep_is_throttled(monkeypatch):
    from collections import deque
    monkeypatch.setattr(main, "_last_sweep", 9_999.0)   # just swept
    main._hits.clear()
    main._hits["idle"] = deque([0.0])              # ancient, but sweep is throttled
    main._sweep_buckets(10_000.0)                  # < _SWEEP_EVERY since last → no-op
    assert "idle" in main._hits


# --- Lifespan-Boot ------------------------------------------------------------

def test_app_boots_via_lifespan_and_health_ok():
    with TestClient(main.app) as client:           # runs the lifespan (init_db)
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_oversize_post_returns_413_end_to_end():
    with TestClient(main.app) as client:
        r = client.post("/ingest", content=b"x" * (70 * 1024))   # > 64 KB with CL header
        assert r.status_code == 413
