"""Lightweight, in-process observability for the Qwen call path.

Records, per Qwen ROLE (distill / recall / revise / self-check / synthesize / chat), the call
count, error count, latency (p50/p95) and token cost — plus a correlation id that ties the
DISTILL -> RECALL -> REVISE -> SELF-CHECK chain of one request together. Zero external deps,
thread-safe, bounded memory. The happy path pays only a timing + dict update.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
import threading
import time
import uuid
from collections import deque

log = logging.getLogger("regressguard.telemetry")
PROCESS_START = time.time()

# Correlation id for the current logical request (set by FastAPI middleware / a benchmark run).
_correlation: contextvars.ContextVar[str] = contextvars.ContextVar("rg_corr", default="")

_lock = threading.Lock()
_roles: dict[str, dict] = {}
_recent: deque = deque(maxlen=50)
_reasoning: deque = deque(maxlen=20)   # bounded ring of captured model reasoning traces


def _role_bucket(role: str) -> dict:
    b = _roles.get(role)
    if b is None:
        b = {"calls": 0, "errors": 0, "cached": 0, "ms": deque(maxlen=200),
             "prompt_tokens": 0, "completion_tokens": 0, "model": None}
        _roles[role] = b
    return b


def new_correlation() -> str:
    cid = uuid.uuid4().hex[:8]
    _correlation.set(cid)
    return cid


def set_correlation(cid: str) -> None:
    _correlation.set(cid)


def correlation() -> str:
    return _correlation.get()


def record(role: str, kind: str, ms: float, *, usage=None, ok: bool = True,
           cached: bool = False, model: str | None = None) -> None:
    """Record one Qwen call. `usage` is the OpenAI-compatible usage object (or None).
    `model` (when given) is stored per role so /telemetry shows which model served each role —
    the visible proof of multi-model routing."""
    pt = getattr(usage, "prompt_tokens", 0) or 0
    ct = getattr(usage, "completion_tokens", 0) or 0
    with _lock:
        b = _role_bucket(role)
        b["calls"] += 1
        if cached:
            b["cached"] += 1
        if not ok:
            b["errors"] += 1
        if ms:
            b["ms"].append(ms)
        if model:
            b["model"] = model
        b["prompt_tokens"] += pt
        b["completion_tokens"] += ct
        _recent.appendleft({"role": role, "kind": kind, "ms": round(ms, 1), "ok": ok,
                            "cached": cached, "prompt_tokens": pt, "completion_tokens": ct,
                            "corr": _correlation.get()})
    # one structured, correlation-tagged line per call — the DISTILL->RECALL->REVISE->SELF-CHECK
    # chain of a request shares a corr id, so a log grep reconstructs the whole flow.
    log.info("qwen role=%s kind=%s ms=%.0f tok=%d/%d ok=%s cached=%s corr=%s",
             role, kind, ms, pt, ct, ok, cached, _correlation.get() or "-")


def _pct(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    i = min(len(s) - 1, int(q * len(s)))
    return round(s[i], 1)


def snapshot() -> dict:
    """A JSON-serializable view for /telemetry — per-role latency + token cost + recent calls."""
    with _lock:
        roles = {}
        tot_calls = tot_err = tot_pt = tot_ct = 0
        for role, b in _roles.items():
            ms = list(b["ms"])
            roles[role] = {
                "calls": b["calls"], "errors": b["errors"], "cached": b["cached"],
                "p50_ms": _pct(ms, 0.50), "p95_ms": _pct(ms, 0.95),
                "avg_ms": round(sum(ms) / len(ms), 1) if ms else 0.0,
                "prompt_tokens": b["prompt_tokens"], "completion_tokens": b["completion_tokens"],
                "model": b.get("model"),
            }
            tot_calls += b["calls"]; tot_err += b["errors"]
            tot_pt += b["prompt_tokens"]; tot_ct += b["completion_tokens"]
        return {
            "uptime_s": round(time.time() - PROCESS_START, 1),
            "totals": {"calls": tot_calls, "errors": tot_err,
                       "prompt_tokens": tot_pt, "completion_tokens": tot_ct},
            "roles": roles,
            "recent": list(_recent)[:20],
        }


def record_reasoning(role: str, text: str) -> None:
    """Stash a model reasoning/thinking trace (bounded ring), correlation-tagged. Purely
    observability — surfaced at /reasoning; never influences a lesson's earned confidence."""
    if not text:
        return
    with _lock:
        _reasoning.appendleft({"role": role, "corr": _correlation.get() or "-",
                               "reasoning": text[:4000], "ts": round(time.time(), 1)})


def reasoning_snapshot() -> list:
    with _lock:
        return list(_reasoning)


def reset() -> None:
    with _lock:
        _roles.clear()
        _recent.clear()
        _reasoning.clear()


@contextlib.contextmanager
def request_scope(cid: str | None = None):
    """Bind a correlation id for one logical request (middleware / benchmark run)."""
    token = _correlation.set(cid or uuid.uuid4().hex[:8])
    try:
        yield _correlation.get()
    finally:
        _correlation.reset(token)
