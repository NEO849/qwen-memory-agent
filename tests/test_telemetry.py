"""Observability — per-role accumulator + correlation scope. Pure, no Qwen calls."""
from backend import telemetry


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5


def test_record_and_snapshot():
    telemetry.reset()
    telemetry.record("distill", "chat_json", 120.0, usage=_Usage())
    telemetry.record("distill", "chat_json", 80.0, usage=_Usage())
    telemetry.record("recall", "embed", 0.0, cached=True)
    snap = telemetry.snapshot()
    d = snap["roles"]["distill"]
    assert d["calls"] == 2 and d["prompt_tokens"] == 20 and d["completion_tokens"] == 10
    assert d["p50_ms"] > 0 and d["p95_ms"] > 0 and d["avg_ms"] == 100.0
    assert snap["roles"]["recall"]["cached"] == 1
    assert snap["totals"]["calls"] == 3 and snap["totals"]["prompt_tokens"] == 20
    assert isinstance(snap["uptime_s"], float)


def test_error_counts_and_recent():
    telemetry.reset()
    telemetry.record("chat", "chat", 50.0, ok=False)
    snap = telemetry.snapshot()
    assert snap["roles"]["chat"]["errors"] == 1
    assert snap["recent"][0]["ok"] is False and snap["recent"][0]["role"] == "chat"


def test_correlation_scope():
    with telemetry.request_scope("abc123") as cid:
        assert cid == "abc123" and telemetry.correlation() == "abc123"
    assert telemetry.correlation() == ""  # reset after scope
