"""Phase 1B — LongMemEval knowledge-update harness logic (fully mocked, no paid calls)."""
from harness import longmemeval_eval as lme
from backend import memory


def _q(qid, gold, newest, oldest):
    return {
        "question_id": qid, "question_type": "knowledge-update",
        "question": "What is my best 5K time?", "answer": gold, "question_date": "2023-06-01",
        "haystack_dates": ["2023-05-01", "2023-04-01"],   # deliberately out of order
        "haystack_sessions": [
            [{"role": "user", "content": newest, "has_answer": True}],
            [{"role": "user", "content": oldest, "has_answer": False}],
        ],
    }


def test_timeline_is_chronological_oldest_first():
    tl = lme._timeline(_q("x", "25:50", "new fact", "old fact"))
    assert [d for d, _ in tl] == ["2023-04-01", "2023-05-01"]   # oldest → newest (recency at the end)
    assert "old fact" in tl[0][1] and "new fact" in tl[1][1]


def test_exact_match_numeric_and_substring():
    assert lme._exact("25:50", "your best time is 25:50")        # substring
    assert lme._exact("25:50", "it was 25 minutes 50 seconds")   # digits in order
    assert not lme._exact("25:50", "i don't know")


def test_exact_handles_non_string_gold():
    # LongMemEval gold answers can be ints (years, counts) — must not crash on .lower()
    assert lme._exact(2021, "that happened in 2021")
    assert lme._exact(5, "you have 5 unread messages")
    assert not lme._exact(2021, "i don't remember")


def test_run_memory_arm_beats_floor(monkeypatch):
    monkeypatch.setattr(memory, "_embed_one", lambda _t: None)   # offline BM25-only ingest/recall

    def fake_chat(msgs, **kw):
        return "Your best 5K time is 25:50." if "RETRIEVED MEMORY" in msgs[-1]["content"] else "I don't know."

    monkeypatch.setattr(lme.qwen_client, "chat", fake_chat)
    monkeypatch.setattr(lme, "_load",
                        lambda: [_q("a", "25:50", "best 5K time is now 25:50", "best 5K time is 26:10"),
                                 _q("b", "25:50", "best 5K time is now 25:50", "best 5K time is 26:10")])
    r = lme.run(n=2, k=10)
    assert r["n"] == 2
    assert r["no_memory"]["correct"] == 0          # floor: no context → can't know
    assert r["regress_guard"]["correct"] == 2      # memory surfaces the fact → correct
    assert r["lift_vs_no_memory"] == 1.0
    assert "NOT a validation of the outcome-grounded confidence gate" in r["honesty"]
