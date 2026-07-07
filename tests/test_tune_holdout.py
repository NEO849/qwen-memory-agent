"""Self-tune uses a TRAIN/VAL holdout — it can't overfit the tiny gold set.

The tune() grid-search picks weights on a train split and adopts them only if they beat the neutral
baseline on a HELD-OUT val split; the reported numbers are the held-out ones. This test drives the
mechanics deterministically by injecting a synthetic gold set (no Qwen), and asserts the split is
honest and the back-compat numbers are the held-out ones.
"""
from __future__ import annotations

from backend import config, evaluation as E, ledger


def test_tune_holdout_split_and_reports_val(tmp_path, monkeypatch):
    db = str(tmp_path / "l.sqlite")
    ledger.init_db(db)
    dim = 16
    docs, items = [], []
    for i in range(8):
        emb = [0.0] * dim
        emb[i] = 1.0
        lid = ledger.add_lesson(f"trigger {i}", f"rule number {i}",
                                source="agent-distill", embedding=emb, path=db)
        docs.append({"id": lid, "text": f"trigger {i} rule number {i}", "embedding": emb})
        items.append({"target": lid, "query": f"alpha beta gamma delta {i}", "qemb": emb})

    # inject the gold set so tune() reuses it (no Qwen paraphrase calls)
    E._gold_cache["key"] = E._marker(db)
    E._gold_cache["gold"] = (docs, items)
    monkeypatch.setattr(config, "RETRIEVAL_CONFIG", str(tmp_path / "retrieval_config.json"))

    r = E.tune(path=db, holdout=True)
    assert r["method"].startswith("train/val")
    assert r["n"] == 8
    assert r["n_train"] + r["n_val"] == 8 and r["n_train"] >= 1 and r["n_val"] >= 1
    assert "val" in r and "train" in r
    # back-compat: the headline baseline/best ARE the held-out numbers (never the train-only ones)
    assert r["baseline"] == r["val"]["baseline"]
    assert r["best"] == r["val"]["best"]
    assert isinstance(r["tuned"], bool)
