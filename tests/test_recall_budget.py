"""Welle 2 — token-budgetierte, kontextfenster-bewusste Recall-Packung (RG_RECALL_BUDGET).

OFF (default) = exaktes top-k-Verhalten. ON = greedy Wert-Dichte-Packung unter hartem Token-Budget.
`_pack_budget` ist rein/deterministisch; recall wird offline (BM25-only) integriert getestet."""
from backend import config, ledger, memory


def _item(i, conf, score, text, pinned=False):
    return {"id": i, "confidence": conf, "_score": score, "trigger": "",
            "lesson": text, "pinned": pinned}


# --- _pack_budget (pure) -----------------------------------------------------

def test_pack_budget_respects_budget_and_density_order():
    items = [_item(1, 0.9, 0.9, "a" * 400),   # cost 100, density 0.0081
             _item(2, 0.9, 0.9, "b" * 40),    # cost 10,  density 0.081  (best)
             _item(3, 0.1, 0.1, "c" * 40)]    # cost 10,  density 0.001
    sel, stats = memory._pack_budget(items, token_budget=20)
    assert [s["id"] for s in sel] == [2, 3]          # highest-density fit first; item1 too big
    assert stats == {"token_budget": 20, "tokens_used": 20,
                     "packed": 2, "considered": 3, "dropped": 1}


def test_pack_budget_pinned_included_first():
    items = [_item(1, 0.9, 0.9, "x" * 40, pinned=True), _item(2, 0.9, 0.9, "y" * 40)]
    sel, stats = memory._pack_budget(items, token_budget=5)   # each costs 10 > budget
    ids = [s["id"] for s in sel]
    assert ids[0] == 1 and 2 not in ids               # pinned override always in, rest dropped
    assert stats["packed"] == 1


def test_pack_budget_failopen_keeps_single_when_nothing_fits():
    sel, stats = memory._pack_budget([_item(1, 0.5, 0.5, "z" * 400)], token_budget=5)
    assert [s["id"] for s in sel] == [1]              # never empty while a candidate exists
    assert stats["packed"] == 1


# --- recall integration (offline, BM25-only) ---------------------------------

def _seed(db, n):
    ledger.init_db(db)
    for i in range(n):
        ledger.add_lesson(f"pagination offset topic {i}",
                          "always cap the page size and validate the offset parameter " * 3,
                          source="agent-distill", path=db)


def test_recall_off_is_topk_no_budget_key(tmp_path, monkeypatch):
    db = str(tmp_path / "l.sqlite"); _seed(db, 8)
    monkeypatch.setattr(memory, "_embed_one", lambda t: None)   # offline
    res = memory.recall("pagination offset", k=3, path=db, track=False)
    assert "budget" not in res                        # OFF == baseline
    assert len(res["lessons"]) <= 3


def test_recall_budget_mode_packs_under_budget(tmp_path, monkeypatch):
    db = str(tmp_path / "l.sqlite"); _seed(db, 8)
    monkeypatch.setattr(memory, "_embed_one", lambda t: None)
    monkeypatch.setattr(config, "RG_RECALL_BUDGET", True)
    monkeypatch.setattr(config, "RG_RECALL_TOKEN_BUDGET", 80)
    res = memory.recall("pagination offset", path=db, track=False)
    assert "budget" in res
    b = res["budget"]
    assert b["tokens_used"] <= 80 or b["packed"] == 1   # respects budget (or fail-open single)
    assert b["packed"] <= b["considered"]
    assert len(res["lessons"]) == b["packed"]           # spread OFF → lessons == packed set
