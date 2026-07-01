"""In-process SSE fan-out for live ledger updates.

Single-uvicorn design: every write bumps a process-global monotonic `etag` and publishes
a tiny {"type":"ledger_changed","etag":N} event (the counter only, never the payload).
The deck reacts by re-fetching the canonical GET /ledger. This keeps the client to one
idempotent render() and needs no external broker.

HARD CONSTRAINT: run with `uvicorn --workers 1` — the fan-out lives in one process, so a
second worker would not see the first's writes.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

_etag: int = 0
_subscribers: set[asyncio.Queue] = set()
_MAX_SUBSCRIBERS = 50   # cap idle SSE connections (mild memory-DoS guard)


def current_etag() -> int:
    return _etag


def _fanout(msg: dict) -> None:
    for q in list(_subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


def bump(kind: str = "ledger_changed", **extra) -> int:
    """Advance the etag and notify all subscribers. Call after every ledger write."""
    global _etag
    _etag += 1
    _fanout({"type": kind, "etag": _etag, **extra})
    return _etag


def publish(msg: dict) -> None:
    """Push a non-ledger event (e.g. agent step) to subscribers WITHOUT bumping the etag,
    so the deck doesn't needlessly re-fetch for agent-only updates."""
    _fanout(msg)


async def stream() -> AsyncIterator[str]:
    """Yield SSE-formatted events for one client. Sends the current etag immediately so a
    late subscriber syncs, then streams changes; a heartbeat keeps proxies from closing."""
    if len(_subscribers) >= _MAX_SUBSCRIBERS:
        yield _sse({"type": "busy", "etag": _etag})
        return
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    try:
        yield _sse({"type": "hello", "etag": _etag})
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=15.0)
                yield _sse(msg)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        _subscribers.discard(q)


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"
