"""Welle 3 — async judge fan-out (RG_ASYNC_REVISE) + batched gold embeddings (RG_BATCH_EMBED).

Both flag-gated; ON must produce the SAME result as the sequential baseline, only faster / fewer
calls. Fully mocked, no paid calls."""
from backend import config, evaluation, ledger, reviser


def _seed_revise(db):
    ledger.init_db(db)
    for t in ["keep this rule", "obsolete now rule", "keep that rule", "obsolete too rule"]:
        ledger.add_lesson(t, f"rule for {t}", source="agent-distill", path=db)


def _fake_judge(lesson, change, model=None):
    return {"obsolete": "obsolete" in lesson["trigger"], "reason": "verdict"}


def test_async_revise_matches_sequential(tmp_path, monkeypatch):
    monkeypatch.setattr(reviser, "judge_obsolete", _fake_judge)
    db_seq = str(tmp_path / "seq.sqlite"); _seed_revise(db_seq)
    db_asy = str(tmp_path / "asy.sqlite"); _seed_revise(db_asy)

    monkeypatch.setattr(config, "RG_ASYNC_REVISE", False)
    seq = reviser.revise("a refactor", path=db_seq)
    monkeypatch.setattr(config, "RG_ASYNC_REVISE", True)
    asy = reviser.revise("a refactor", path=db_asy)

    key = lambda rs: [(r["lesson"], r["obsolete"], r["action"]) for r in rs]
    assert key(seq) == key(asy)                          # same verdicts, same order
    tomb_seq = {l["id"] for l in ledger.list_lessons(status="obsolete", path=db_seq)}
    tomb_asy = {l["id"] for l in ledger.list_lessons(status="obsolete", path=db_asy)}
    assert len(tomb_seq) == 2 and len(tomb_asy) == 2     # both tombstoned the two obsolete lessons


def test_batch_embed_uses_single_call(tmp_path, monkeypatch):
    db = str(tmp_path / "l.sqlite"); ledger.init_db(db)
    for t in ("alpha", "beta", "gamma"):
        ledger.add_lesson(t, f"rule for {t}", source="agent-distill", path=db)
    monkeypatch.setattr(evaluation, "_paraphrase", lambda l: f"question for {l['id']}")
    calls = {"n": 0, "sizes": []}

    def fake_embed(texts, **kw):
        calls["n"] += 1; calls["sizes"].append(len(texts))
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    monkeypatch.setattr(evaluation.qwen_client, "embed", fake_embed)

    monkeypatch.setattr(config, "RG_BATCH_EMBED", True)
    _docs, items = evaluation._build_gold(db, sample=10)
    assert calls["n"] == 1 and calls["sizes"] == [len(items)]     # ONE batched call for the whole set

    calls["n"] = 0; calls["sizes"] = []
    monkeypatch.setattr(config, "RG_BATCH_EMBED", False)
    _docs, items = evaluation._build_gold(db, sample=10)
    assert calls["n"] == len(items) and all(s == 1 for s in calls["sizes"])   # baseline: one per item
