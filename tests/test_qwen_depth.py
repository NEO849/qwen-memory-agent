"""Welle 1 — Qwen-Tiefe: Structured-Output, Multi-Model-Routing, Reasoning-Capture.

Alle Stufen flag-gegatet, default OFF. Jede Gruppe hat eine explizite „Flag-OFF == Baseline"-
Assertion. Voll gemockt (kein Client, keine bezahlten Calls)."""
import types

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from backend import config, extractor, qwen_client as qc, reviser, telemetry


# --- Fakes -------------------------------------------------------------------

class _Msg:
    def __init__(self, content, reasoning=None):
        self.content = content
        self.reasoning_content = reasoning
        self.tool_calls = None


class _Resp:
    def __init__(self, content, usage=None):
        self.choices = [types.SimpleNamespace(message=_Msg(content))]
        self.usage = usage


def _stream(reasoning_parts, content_parts):
    for r in reasoning_parts:
        yield types.SimpleNamespace(usage=None, choices=[types.SimpleNamespace(
            delta=types.SimpleNamespace(reasoning_content=r, content=None))])
    for c in content_parts:
        yield types.SimpleNamespace(usage=None, choices=[types.SimpleNamespace(
            delta=types.SimpleNamespace(reasoning_content=None, content=c))])
    yield types.SimpleNamespace(
        usage=types.SimpleNamespace(prompt_tokens=5, completion_tokens=7), choices=[])


def _install(monkeypatch, create):
    comp = types.SimpleNamespace(create=create)
    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=comp),
                                   embeddings=types.SimpleNamespace(create=create))
    monkeypatch.setattr(qc, "_client", lambda: client)


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(qc, "_breaker", qc._Breaker(qc._CB_THRESHOLD, qc._CB_COOLDOWN))
    monkeypatch.setattr(qc.time, "sleep", lambda *_: None)
    telemetry.reset()


# --- Structured output (RG_STRUCTURED_OUTPUT) --------------------------------

def test_structured_output_off_uses_json_object_baseline(monkeypatch):
    monkeypatch.setattr(config, "RG_STRUCTURED_OUTPUT", False)
    seen = []
    _install(monkeypatch, lambda **kw: (seen.append(kw), _Resp('{"a": 1}'))[1])
    out = qc.chat_json([{"role": "user", "content": "x"}], schema=extractor.LESSON_SCHEMA, role="distill")
    assert out == {"a": 1}
    assert seen[0]["response_format"] == {"type": "json_object"}   # OFF == today's behaviour


def test_structured_output_on_uses_json_schema(monkeypatch):
    monkeypatch.setattr(config, "RG_STRUCTURED_OUTPUT", True)
    seen = []
    _install(monkeypatch, lambda **kw: (seen.append(kw), _Resp('{"a": 1}'))[1])
    qc.chat_json([{"role": "user", "content": "x"}], schema=extractor.LESSON_SCHEMA, role="distill")
    rf = seen[0]["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["schema"] == extractor.LESSON_SCHEMA
    assert rf["json_schema"]["strict"] is True


def test_structured_output_rejection_falls_back_to_json_object(monkeypatch):
    monkeypatch.setattr(config, "RG_STRUCTURED_OUTPUT", True)
    seen = []

    def create(**kw):
        seen.append(kw["response_format"]["type"])
        if kw["response_format"]["type"] == "json_schema":
            raise ValueError("model rejects json_schema")   # non-transient → fallback
        return _Resp('{"ok": 1}')

    _install(monkeypatch, create)
    out = qc.chat_json([{"role": "user", "content": "x"}], schema=extractor.LESSON_SCHEMA, role="distill")
    assert out == {"ok": 1}
    assert seen == ["json_schema", "json_object"]              # tried strict, degraded gracefully


# --- Multi-model routing (RG_MODEL_ROUTING) ----------------------------------

def test_model_for_off_is_baseline():
    from backend import config as c
    orig = c.RG_MODEL_ROUTING
    try:
        c.RG_MODEL_ROUTING = False
        assert c.model_for("judge") == c.model_for("distill") == c.model_for("x") == c.QWEN_MODEL
    finally:
        c.RG_MODEL_ROUTING = orig


def test_model_for_on_routes_per_role(monkeypatch):
    monkeypatch.setattr(config, "RG_MODEL_ROUTING", True)
    assert config.model_for("judge") == "qwen-max"
    assert config.model_for("paraphrase") == "qwen-turbo"
    assert config.model_for("distill") == "qwen-plus"
    assert config.model_for("anything-else") == config.RG_MODEL_DEFAULT


def test_revise_routes_judge_model(monkeypatch):
    monkeypatch.setattr(config, "RG_MODEL_ROUTING", True)
    captured = {}
    monkeypatch.setattr(reviser.qwen_client, "chat_json",
                        lambda msgs, **kw: captured.update(kw) or {"obsolete": False, "reason": ""})
    reviser.judge_obsolete({"trigger": "t", "lesson": "l", "scope": ""}, "some change",
                           model=config.model_for("judge"))
    assert captured["model"] == "qwen-max"


def test_telemetry_surfaces_model_per_role(monkeypatch):
    _install(monkeypatch, lambda **kw: _Resp("OK"))
    qc.chat([{"role": "user", "content": "hi"}], model="qwen-max", role="revise")
    assert telemetry.snapshot()["roles"]["revise"]["model"] == "qwen-max"


# --- Reasoning capture (RG_REASONING) ----------------------------------------

def test_reasoning_off_no_stream_no_capture(monkeypatch):
    monkeypatch.setattr(config, "RG_REASONING", False)
    seen = []
    _install(monkeypatch, lambda **kw: (seen.append(kw), _Resp('{"obsolete": false, "reason": "ok"}'))[1])
    out = qc.chat_json([{"role": "user", "content": "x"}], role="revise", capture_reasoning=True)
    assert out["reason"] == "ok"
    assert seen[0].get("stream") is not True            # OFF == no streaming request
    assert telemetry.reasoning_snapshot() == []


def test_reasoning_on_captures_trace(monkeypatch):
    monkeypatch.setattr(config, "RG_REASONING", True)

    def create(**kw):
        assert kw.get("stream") is True
        assert kw.get("extra_body") == {"enable_thinking": True}
        return _stream(["I weigh tenant isolation"], ['{"obsolete": false, "reason": "still valid"}'])

    _install(monkeypatch, create)
    out = qc.chat_json([{"role": "user", "content": "x"}], role="revise", capture_reasoning=True)
    assert out["reason"] == "still valid"
    traces = telemetry.reasoning_snapshot()
    assert len(traces) == 1 and "tenant isolation" in traces[0]["reasoning"]
    assert traces[0]["role"] == "revise"


def test_reasoning_stream_failure_falls_back(monkeypatch):
    monkeypatch.setattr(config, "RG_REASONING", True)

    def create(**kw):
        if kw.get("stream"):
            raise ValueError("thinking not supported by this model")   # non-transient → fallback
        return _Resp('{"obsolete": true, "reason": "obsolete"}')

    _install(monkeypatch, create)
    out = qc.chat_json([{"role": "user", "content": "x"}], role="revise", capture_reasoning=True)
    assert out["obsolete"] is True                    # degraded to plain path, still works
    assert telemetry.reasoning_snapshot() == []


def test_reasoning_endpoint(monkeypatch):
    telemetry.record_reasoning("distill", "because get_orders must filter by tenant_id")
    with TestClient(main.app) as client:
        r = client.get("/reasoning")
        assert r.status_code == 200
        body = r.json()
        assert body["traces"][0]["role"] == "distill"
        assert "tenant_id" in body["traces"][0]["reasoning"]


# --- Wiring: extractor passes schema + reasoning + routing -------------------

def test_extractor_wires_schema_and_reasoning(monkeypatch):
    captured = {}
    monkeypatch.setattr(extractor.qwen_client, "chat_json",
                        lambda msgs, **kw: captured.update(kw) or
                        {"trigger": "t", "lesson": "l", "scope": "s", "severity": "high"})
    extractor.extract_lesson("red test", "the diff")
    assert captured["schema"] == extractor.LESSON_SCHEMA
    assert captured["capture_reasoning"] is True
    assert captured["role"] == "distill"
