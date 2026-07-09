"""Härtung des Qwen-Clients — Retry/Backoff, Circuit-Breaker, Disk-Cache.

Vollständig gemockt (kein `live`-Marker, keine bezahlten Calls): wir prüfen die
Wrapper-Logik, nicht die SDK-Exception-Konstruktoren.
"""
import types

import pytest

from backend import qwen_client as qc


class _Transient(Exception):
    """Steht im Test für einen transienten Qwen-Fehler (429/5xx/Timeout)."""


class _FakeResp:
    def __init__(self, content):
        msg = types.SimpleNamespace(content=content, tool_calls=None)
        self.choices = [types.SimpleNamespace(message=msg)]


def _fake_client(create_fn):
    """Baut ein Objekt mit .chat.completions.create und .embeddings.create = create_fn."""
    comp = types.SimpleNamespace(create=create_fn)
    return types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=comp),
        embeddings=types.SimpleNamespace(create=create_fn),
    )


@pytest.fixture(autouse=True)
def _fresh_breaker(monkeypatch):
    # Frischer Breaker + retryable = unser Test-Fehler + kein echtes Sleep.
    monkeypatch.setattr(qc, "_breaker", qc._Breaker(qc._CB_THRESHOLD, qc._CB_COOLDOWN))
    monkeypatch.setattr(qc, "_RETRYABLE", (_Transient,))
    monkeypatch.setattr(qc.time, "sleep", lambda *_: None)


def test_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}
    def create(**_):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Transient("kurzzeitig 503")
        return _FakeResp("OK")
    monkeypatch.setattr(qc, "_client", lambda: _fake_client(create))
    assert qc.chat([{"role": "user", "content": "hi"}]) == "OK"
    assert calls["n"] == 3  # 2 Fehlversuche + 1 Erfolg


def test_exhausts_to_unavailable(monkeypatch):
    def create(**_):
        raise _Transient("dauerhaft down")
    monkeypatch.setattr(qc, "_client", lambda: _fake_client(create))
    with pytest.raises(qc.QwenUnavailable):
        qc.chat([{"role": "user", "content": "hi"}])


def test_circuit_opens_and_blocks(monkeypatch):
    br = qc._Breaker(threshold=2, cooldown=999)
    br.fail(); br.fail()
    with pytest.raises(qc.QwenUnavailable):
        br.before()          # offen → sofort blocken, kein Call
    br.ok()
    br.before()              # nach Erfolg wieder geschlossen


def test_disk_cache_avoids_second_call(monkeypatch, tmp_path):
    calls = {"n": 0}
    def create(**_):
        calls["n"] += 1
        return _FakeResp("cached-answer")
    monkeypatch.setattr(qc, "_client", lambda: _fake_client(create))
    with qc.qwen_cache(str(tmp_path)):
        a = qc.chat([{"role": "user", "content": "same"}])
        b = qc.chat([{"role": "user", "content": "same"}])
    assert a == b == "cached-answer"
    assert calls["n"] == 1   # zweiter Aufruf kam aus dem Cache, kein Re-Billing
