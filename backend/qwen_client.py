"""Dünner, gehärteter Wrapper um Qwen (Alibaba Model Studio / DashScope) im OpenAI-kompatiblen Modus.

Idee-unabhängig: das brauchen wir in JEDER Variante. `python -m backend.qwen_client`
macht einen Verbindungstest, sobald der API-Key gesetzt ist.

Härtung (Final-Sprint, additiv — Happy-Path bleibt byte-identisch zur Baseline):
- Typed retry mit exponential backoff + jitter auf transiente Fehler (429/5xx/Timeout/Connection).
- Circuit-Breaker: nach N Fehlern in Folge kurz „offen" → schnelles, klares Degradieren
  (Aufrufer mit Fallback fangen `QwenUnavailable`) statt einen toten Gateway zu hämmern.
- Optionaler Disk-Cache (nur für die Benchmark-Harness, via `qwen_cache()`), damit ein
  Crash mitten im bezahlten Lauf NIE erneut abgerechnet wird. Der Live-Chat cached NICHT.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import random
import threading
import time

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from . import config, telemetry

log = logging.getLogger("regressguard.qwen")

# --- Resilience-Parameter (Env-überschreibbar, sane Defaults) --------------------------------
_RETRIES = int(os.environ.get("QWEN_RETRIES", "3"))            # Versuche zusätzlich zum ersten Call
_BACKOFF_BASE = float(os.environ.get("QWEN_BACKOFF_BASE", "0.5"))   # Sekunden, verdoppelt je Versuch
_BACKOFF_CAP = float(os.environ.get("QWEN_BACKOFF_CAP", "8.0"))     # Deckel je Wartezeit
_CB_THRESHOLD = int(os.environ.get("QWEN_CB_THRESHOLD", "5"))       # Fehler in Folge bis „offen"
_CB_COOLDOWN = float(os.environ.get("QWEN_CB_COOLDOWN", "20.0"))    # Sekunden „offen" bevor Halb-offen

# Transiente Fehler, bei denen ein Retry sinnvoll ist (alles andere fliegt sofort).
_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)


class QwenUnavailable(RuntimeError):
    """Circuit ist offen ODER alle Retries erschöpft — Aufrufer soll graceful degradieren
    (z. B. RECALL fällt auf RRF-only zurück), statt hart zu scheitern."""


class _Breaker:
    """Minimaler Thread-sicherer Circuit-Breaker (closed → open → half-open)."""

    def __init__(self, threshold: int, cooldown: float) -> None:
        self._threshold, self._cooldown = threshold, cooldown
        self._fails = 0
        self._open_until = 0.0
        self._lock = threading.Lock()

    def before(self) -> None:
        with self._lock:
            if self._open_until and time.monotonic() < self._open_until:
                raise QwenUnavailable(
                    f"Qwen circuit open (cooldown {self._open_until - time.monotonic():.0f}s)")

    def ok(self) -> None:
        with self._lock:
            self._fails = 0
            self._open_until = 0.0

    def fail(self) -> None:
        with self._lock:
            self._fails += 1
            if self._fails >= self._threshold:
                self._open_until = time.monotonic() + self._cooldown
                log.warning("Qwen circuit OPEN nach %d Fehlern — %.0fs cooldown",
                            self._fails, self._cooldown)


_breaker = _Breaker(_CB_THRESHOLD, _CB_COOLDOWN)


def _resilient(fn, *, desc: str):
    """Führt `fn()` mit Retry/Backoff/Jitter aus und pflegt den Circuit-Breaker.
    Erfolg → identisches Ergebnis wie ohne Wrapper. Erschöpft → QwenUnavailable."""
    _breaker.before()
    attempt = 0
    while True:
        try:
            out = fn()
            _breaker.ok()
            return out
        except _RETRYABLE as e:
            attempt += 1
            _breaker.fail()
            if attempt > _RETRIES:
                raise QwenUnavailable(f"{desc}: {type(e).__name__} nach {attempt} Versuchen") from e
            delay = min(_BACKOFF_CAP, _BACKOFF_BASE * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.25)  # Jitter gegen Thundering-Herd
            log.info("Qwen %s transient (%s) — retry %d/%d in %.2fs",
                     desc, type(e).__name__, attempt, _RETRIES, delay)
            time.sleep(delay)


def _client() -> OpenAI:
    config.assert_configured()
    # Bounded so a stalled/overloaded gateway (the classic 524) surfaces an error in seconds
    # instead of hanging a request — and its UI button. max_retries=0: WIR steuern Retries
    # (oben, mit Backoff/Jitter/Breaker) statt der SDK-Default-Logik.
    return OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.QWEN_BASE_URL,
                  timeout=20.0, max_retries=0)


# --- Optionaler Disk-Cache (NUR Benchmark) ---------------------------------------------------
_cache_dir: str | None = None


@contextlib.contextmanager
def qwen_cache(path: str):
    """Innerhalb dieses Blocks werden chat/chat_json/embed-Ergebnisse deterministisch auf Platte
    gecached (Key = sha256 über model+messages+kwargs). NUR für die Benchmark-Harness: ein
    Crash mitten im bezahlten Lauf wiederholt keinen Call. Der Live-Server ruft das NIE auf."""
    global _cache_dir
    os.makedirs(path, exist_ok=True)
    prev, _cache_dir = _cache_dir, path
    try:
        yield
    finally:
        _cache_dir = prev


def _cache_key(kind: str, model: str, payload) -> str:
    blob = json.dumps({"k": kind, "m": model, "p": payload}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _cache_get(key: str):
    if not _cache_dir:
        return None
    fp = os.path.join(_cache_dir, key + ".json")
    if os.path.exists(fp):
        with open(fp) as f:
            return json.load(f)
    return None


def _cache_put(key: str, value) -> None:
    if not _cache_dir:
        return
    fp = os.path.join(_cache_dir, key + ".json")
    with open(fp, "w") as f:
        json.dump(value, f)


# --- Öffentliche API (Rückgabewerte unverändert; `role` nur für Telemetrie, nie an die API) ---
def chat(messages: list[dict], model: str | None = None, *, role: str = "chat", **kwargs) -> str:
    """Eine Chat-Completion an Qwen. `messages` = OpenAI-Format [{role, content}, ...]."""
    mdl = model or config.QWEN_MODEL
    key = _cache_key("chat", mdl, {"msgs": messages, "kw": kwargs})
    hit = _cache_get(key)
    if hit is not None:
        telemetry.record(role, "chat", 0.0, cached=True)
        return hit
    t0 = time.perf_counter()
    try:
        resp = _resilient(
            lambda: _client().chat.completions.create(model=mdl, messages=messages, **kwargs),
            desc="chat")
    except QwenUnavailable:
        telemetry.record(role, "chat", (time.perf_counter() - t0) * 1000, ok=False)
        raise
    telemetry.record(role, "chat", (time.perf_counter() - t0) * 1000, usage=getattr(resp, "usage", None))
    out = resp.choices[0].message.content or ""
    _cache_put(key, out)
    return out


def chat_stream(messages: list[dict], model: str | None = None, *, role: str = "chat", **kwargs):
    """Stream a chat completion token-by-token (Qwen streaming). Yields content deltas (str).
    Single attempt (a partial stream can't be safely retried); if the connection fails BEFORE any
    token, raises QwenUnavailable so the caller can fall back to a non-streamed answer. Telemetry
    (latency + token usage from the final chunk) is recorded when the stream ends."""
    mdl = model or config.QWEN_MODEL
    t0 = time.perf_counter()
    usage = {"u": None}
    produced = False
    _breaker.before()
    try:
        stream = _client().chat.completions.create(
            model=mdl, messages=messages, stream=True,
            stream_options={"include_usage": True}, **kwargs)
    except _RETRYABLE as e:
        _breaker.fail()
        telemetry.record(role, "chat_stream", (time.perf_counter() - t0) * 1000, ok=False)
        raise QwenUnavailable(f"chat_stream: {type(e).__name__}") from e
    try:
        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage["u"] = chunk.usage
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    produced = True
                    yield delta
        _breaker.ok()
    finally:
        telemetry.record(role, "chat_stream", (time.perf_counter() - t0) * 1000,
                         usage=usage["u"], ok=produced)


def chat_with_tools(messages: list[dict], tools: list[dict], model: str | None = None,
                    tool_choice: str = "auto", *, role: str = "chat", **kwargs):
    """One chat completion with Qwen function/tool-calling (OpenAI-compatible). Returns the raw
    assistant message — inspect `.tool_calls` to see if the model chose to call a tool, and
    `.content` for a direct answer. The caller runs the tool and feeds the result back for a
    follow-up completion. This is how the agent autonomously decides to consult its memory."""
    mdl = model or config.QWEN_MODEL
    t0 = time.perf_counter()
    try:
        resp = _resilient(
            lambda: _client().chat.completions.create(
                model=mdl, messages=messages, tools=tools, tool_choice=tool_choice, **kwargs),
            desc="chat_with_tools")
    except QwenUnavailable:
        telemetry.record(role, "tools", (time.perf_counter() - t0) * 1000, ok=False)
        raise
    telemetry.record(role, "tools", (time.perf_counter() - t0) * 1000, usage=getattr(resp, "usage", None))
    return resp.choices[0].message


def chat_json(messages: list[dict], model: str | None = None, *, role: str = "chat", **kwargs) -> dict:
    """Chat-Completion, die garantiert JSON zurückgibt (Qwen role 1: lesson distillation).

    Nutzt response_format=json_object. Robust: fällt der Provider auf Text zurück, wird
    das erste balancierte JSON-Objekt aus der Antwort geparst statt hart zu werfen.
    """
    mdl = model or config.QWEN_MODEL
    key = _cache_key("chat_json", mdl, {"msgs": messages, "kw": kwargs})
    hit = _cache_get(key)
    if hit is not None:
        telemetry.record(role, "chat_json", 0.0, cached=True)
        return hit
    t0 = time.perf_counter()
    try:
        resp = _resilient(
            lambda: _client().chat.completions.create(
                model=mdl, messages=messages, response_format={"type": "json_object"}, **kwargs),
            desc="chat_json")
    except QwenUnavailable:
        telemetry.record(role, "chat_json", (time.perf_counter() - t0) * 1000, ok=False)
        raise
    telemetry.record(role, "chat_json", (time.perf_counter() - t0) * 1000, usage=getattr(resp, "usage", None))
    raw = resp.choices[0].message.content or "{}"
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            out = json.loads(raw[start:end + 1])
        else:
            raise
    _cache_put(key, out)
    return out


def embed(texts: list[str], model: str | None = None, *, role: str = "recall") -> list[list[float]]:
    """Embedde Texte über Qwen (role 2: retrieval). Gibt eine Liste 1024-dim Vektoren zurück,
    Reihenfolge wie die Eingabe. Leere Eingabe → []."""
    if not texts:
        return []
    mdl = model or config.QWEN_EMBED_MODEL
    key = _cache_key("embed", mdl, texts)
    hit = _cache_get(key)
    if hit is not None:
        telemetry.record(role, "embed", 0.0, cached=True)
        return hit
    t0 = time.perf_counter()
    try:
        resp = _resilient(lambda: _client().embeddings.create(model=mdl, input=texts), desc="embed")
    except QwenUnavailable:
        telemetry.record(role, "embed", (time.perf_counter() - t0) * 1000, ok=False)
        raise
    telemetry.record(role, "embed", (time.perf_counter() - t0) * 1000, usage=getattr(resp, "usage", None))
    items = sorted(resp.data, key=lambda d: d.index)  # Reihenfolge defensiv erzwingen
    return [item.embedding for item in items]


# --- qwen3-rerank (Qwen role: cross-encoder rerank) ------------------------------------------
# Native DashScope text-rerank endpoint (NOT the OpenAI-compat interface). We call it over httpx
# so no new SDK dependency is added. Body is FLAT (query/documents at top level) — verified.
def _rerank_url() -> str:
    return config.QWEN_BASE_URL.split("/compatible-mode")[0] + \
        "/api/v1/services/rerank/text-rerank/text-rerank"


def _resilient_http(build, *, desc: str) -> dict:
    """httpx variant of _resilient: retry on timeout/transport/429/5xx, breaker, else raise.
    A 4xx (bad request) is NOT retried — it surfaces immediately."""
    _breaker.before()
    attempt = 0
    while True:
        try:
            resp = build()
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            if resp.status_code >= 400:
                _breaker.ok()
                raise RuntimeError(f"{desc} {resp.status_code}: {resp.text[:200]}")
            _breaker.ok()
            return resp.json()
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as e:
            attempt += 1
            _breaker.fail()
            if attempt > _RETRIES:
                raise QwenUnavailable(f"{desc}: {type(e).__name__} nach {attempt} Versuchen") from e
            delay = min(_BACKOFF_CAP, _BACKOFF_BASE * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.25)
            log.info("Qwen %s transient (%s) — retry %d/%d in %.2fs",
                     desc, type(e).__name__, attempt, _RETRIES, delay)
            time.sleep(delay)


def rerank(query: str, documents: list[str], *, top_n: int | None = None,
           model: str | None = None, role: str = "rerank") -> list[tuple[int, float]]:
    """Cross-encoder rerank of `documents` against `query` via qwen3-rerank. Returns
    [(original_index, relevance_score), ...] sorted by relevance (best first). Empty input or a
    down service -> [] so the caller keeps its prior (RRF) order (graceful degradation)."""
    if not documents:
        return []
    mdl = model or config.RG_RERANK_MODEL
    key = _cache_key("rerank", mdl, {"q": query, "docs": documents, "top_n": top_n})
    hit = _cache_get(key)
    if hit is not None:
        telemetry.record(role, "rerank", 0.0, cached=True)
        return [tuple(x) for x in hit]
    body = {"model": mdl, "query": query, "documents": documents,
            "parameters": {"top_n": top_n or len(documents), "return_documents": False}}
    headers = {"Authorization": f"Bearer {config.DASHSCOPE_API_KEY}", "Content-Type": "application/json"}
    t0 = time.perf_counter()
    try:
        out = _resilient_http(
            lambda: httpx.post(_rerank_url(), headers=headers, json=body, timeout=20.0),
            desc="rerank")
    except (QwenUnavailable, RuntimeError) as e:
        telemetry.record(role, "rerank", (time.perf_counter() - t0) * 1000, ok=False)
        log.warning("rerank unavailable (%s) — falling back to RRF order", type(e).__name__)
        return []
    telemetry.record(role, "rerank", (time.perf_counter() - t0) * 1000)
    ranked = [(int(r["index"]), float(r["relevance_score"])) for r in out.get("results", [])]
    _cache_put(key, ranked)
    return ranked


if __name__ == "__main__":
    # Verbindungstest gegen Qwen — erst nach ID-Verify + API-Key + Credits sinnvoll.
    print(f"Endpoint: {config.QWEN_BASE_URL}")
    print(f"Modell:   {config.QWEN_MODEL}")
    answer = chat([{"role": "user", "content": "Antworte mit genau einem Wort: OK"}])
    print(f"Qwen sagt: {answer!r}")
