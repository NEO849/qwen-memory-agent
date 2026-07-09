"""Bounded multi-step tool loop in _chat_prepare — flag OFF = one round, ON = multi-round.
Fully mocked (memory + qwen), no paid calls."""
import types

import pytest

from backend import main


def _call(cid, name, args):
    return types.SimpleNamespace(id=cid, function=types.SimpleNamespace(name=name, arguments=args))


def _msg(content=None, tool_calls=None):
    return types.SimpleNamespace(content=content, tool_calls=tool_calls)


@pytest.fixture(autouse=True)
def _mock_memory(monkeypatch):
    monkeypatch.setattr(main.memory, "recall",
                        lambda q, k, path=None: {"lessons": [{"id": 1, "lesson": "L1"}, {"id": 7, "lesson": "L7"}]})
    monkeypatch.setattr(main.memory, "render_injection",
                        lambda lessons: "BLOCK(" + ",".join(str(l["id"]) for l in lessons) + ")")
    monkeypatch.setattr(main.memory, "directive_count", lambda s: 0)
    monkeypatch.setattr(main.memory, "inhibitions", lambda lessons: [])
    monkeypatch.setattr(main.memory, "related", lambda lid, k=3, path=None: [{"id": 9, "lesson": "L9"}])


def _script(monkeypatch, msgs):
    seq = iter(msgs)
    calls = {"n": 0}
    def fake(messages, tools, **kw):
        calls["n"] += 1
        return next(seq)
    monkeypatch.setattr(main.qwen_client, "chat_with_tools", fake)
    return calls


def test_flag_off_single_round(monkeypatch):
    monkeypatch.setattr(main.config, "RG_TOOL_LOOP", False)
    calls = _script(monkeypatch, [_msg(tool_calls=[_call("1", "recall_memory", '{"query":"pagination"}')])])
    messages, direct, meta, used_tool, tq = main._chat_prepare("how to paginate", 5)
    assert calls["n"] == 1                       # exactly one round when flag off
    assert direct is None and messages is not None and used_tool is True
    assert tq == "pagination" and meta["recalled"] == [1, 7]
    # flag OFF: tool result is the plain block (no "Recalled lesson ids" prefix)
    tool_msg = [m for m in messages if m.get("role") == "tool"][0]
    assert tool_msg["content"] == "BLOCK(1,7)"


def test_flag_on_multi_round_uses_both_tools(monkeypatch):
    monkeypatch.setattr(main.config, "RG_TOOL_LOOP", True)
    monkeypatch.setattr(main.config, "RG_TOOL_LOOP_MAX", 3)
    seen = {"related_id": None}
    monkeypatch.setattr(main.memory, "related",
                        lambda lid, k=3, path=None: (seen.__setitem__("related_id", lid) or [{"id": 9, "lesson": "L9"}]))
    calls = _script(monkeypatch, [
        _msg(tool_calls=[_call("1", "recall_memory", '{"query":"pagination"}')]),
        _msg(tool_calls=[_call("2", "get_related_lessons", '{"lesson_id":1}')]),
        _msg(content="final answer"),
    ])
    messages, direct, meta, used_tool, tq = main._chat_prepare("how to paginate", 5)
    assert calls["n"] == 3                        # recall -> related -> answer (bounded multi-step)
    assert direct == "final answer" and used_tool is True
    assert meta["recalled"] == [1, 7]            # round 1 recall happened
    assert seen["related_id"] == 1               # round 2 dispatched get_related_lessons(1)


def test_flag_on_caps_rounds(monkeypatch):
    """If Qwen keeps calling tools, the loop stops at RG_TOOL_LOOP_MAX and hands off a final answer."""
    monkeypatch.setattr(main.config, "RG_TOOL_LOOP", True)
    monkeypatch.setattr(main.config, "RG_TOOL_LOOP_MAX", 2)
    calls = _script(monkeypatch, [
        _msg(tool_calls=[_call("1", "recall_memory", '{"query":"a"}')]),
        _msg(tool_calls=[_call("2", "recall_memory", '{"query":"b"}')]),
        _msg(tool_calls=[_call("3", "recall_memory", '{"query":"c"}')]),  # never reached
    ])
    messages, direct, meta, used_tool, tq = main._chat_prepare("q", 5)
    assert calls["n"] == 2 and messages is not None and direct is None  # capped, caller finishes


def test_direct_answer_no_tool(monkeypatch):
    monkeypatch.setattr(main.config, "RG_TOOL_LOOP", False)
    _script(monkeypatch, [_msg(content="hi there")])
    messages, direct, meta, used_tool, tq = main._chat_prepare("hello", 5)
    assert direct == "hi there" and messages is None and used_tool is False
