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

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from . import config

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


# --- Öffentliche API (Signaturen unverändert) ------------------------------------------------
def chat(messages: list[dict], model: str | None = None, **kwargs) -> str:
    """Eine Chat-Completion an Qwen. `messages` = OpenAI-Format [{role, content}, ...]."""
    mdl = model or config.QWEN_MODEL
    key = _cache_key("chat", mdl, {"msgs": messages, "kw": kwargs})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    def _do():
        resp = _client().chat.completions.create(model=mdl, messages=messages, **kwargs)
        return resp.choices[0].message.content or ""
    out = _resilient(_do, desc="chat")
    _cache_put(key, out)
    return out


def chat_with_tools(messages: list[dict], tools: list[dict], model: str | None = None,
                    tool_choice: str = "auto", **kwargs):
    """One chat completion with Qwen function/tool-calling (OpenAI-compatible). Returns the raw
    assistant message — inspect `.tool_calls` to see if the model chose to call a tool, and
    `.content` for a direct answer. The caller runs the tool and feeds the result back for a
    follow-up completion. This is how the agent autonomously decides to consult its memory."""
    mdl = model or config.QWEN_MODEL
    def _do():
        resp = _client().chat.completions.create(
            model=mdl, messages=messages, tools=tools, tool_choice=tool_choice, **kwargs)
        return resp.choices[0].message
    return _resilient(_do, desc="chat_with_tools")


def chat_json(messages: list[dict], model: str | None = None, **kwargs) -> dict:
    """Chat-Completion, die garantiert JSON zurückgibt (Qwen role 1: lesson distillation).

    Nutzt response_format=json_object. Robust: fällt der Provider auf Text zurück, wird
    das erste balancierte JSON-Objekt aus der Antwort geparst statt hart zu werfen.
    """
    mdl = model or config.QWEN_MODEL
    key = _cache_key("chat_json", mdl, {"msgs": messages, "kw": kwargs})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    def _do():
        resp = _client().chat.completions.create(
            model=mdl, messages=messages, response_format={"type": "json_object"}, **kwargs)
        return resp.choices[0].message.content or "{}"
    raw = _resilient(_do, desc="chat_json")
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


def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Embedde Texte über Qwen (role 2: retrieval). Gibt eine Liste 1024-dim Vektoren zurück,
    Reihenfolge wie die Eingabe. Leere Eingabe → []."""
    if not texts:
        return []
    mdl = model or config.QWEN_EMBED_MODEL
    key = _cache_key("embed", mdl, texts)
    hit = _cache_get(key)
    if hit is not None:
        return hit
    def _do():
        resp = _client().embeddings.create(model=mdl, input=texts)
        items = sorted(resp.data, key=lambda d: d.index)  # Reihenfolge defensiv erzwingen
        return [item.embedding for item in items]
    out = _resilient(_do, desc="embed")
    _cache_put(key, out)
    return out


if __name__ == "__main__":
    # Verbindungstest gegen Qwen — erst nach ID-Verify + API-Key + Credits sinnvoll.
    print(f"Endpoint: {config.QWEN_BASE_URL}")
    print(f"Modell:   {config.QWEN_MODEL}")
    answer = chat([{"role": "user", "content": "Antworte mit genau einem Wort: OK"}])
    print(f"Qwen sagt: {answer!r}")
