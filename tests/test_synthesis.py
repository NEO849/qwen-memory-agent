"""Pattern crystallization / ExpeL synthesis — offline (Qwen mocked)."""
from backend import ledger, memory, synthesis


def _db(tmp_path):
    p = str(tmp_path / "synth.sqlite")
    ledger.init_db(p)
    return p


def test_propose_only_for_scope_clusters(tmp_path, monkeypatch):
    monkeypatch.setattr(synthesis.qwen_client, "chat_json",
                        lambda *a, **k: {"trigger": "authz checks", "lesson": "centralize authorization"})
    p = _db(tmp_path)
    for i in range(3):
        ledger.add_lesson(f"t{i}", f"rule {i}", scope="api/auth", source="human", path=p)
    ledger.add_lesson("lone", "y", scope="db", source="human", path=p)   # only 1 in this scope
    out = synthesis.propose_synthesis(path=p, min_group=3)
    assert len(out["proposals"]) == 1
    pr = out["proposals"][0]
    assert pr["scope"] == "api/auth" and len(pr["children"]) == 3 and pr["lesson"]


def test_no_proposal_below_min_group(tmp_path, monkeypatch):
    monkeypatch.setattr(synthesis.qwen_client, "chat_json", lambda *a, **k: {"lesson": "x"})
    p = _db(tmp_path)
    ledger.add_lesson("a", "r", scope="api", source="human", path=p)
    ledger.add_lesson("b", "r", scope="api", source="human", path=p)   # only 2
    assert synthesis.propose_synthesis(path=p, min_group=3)["proposals"] == []


def test_accept_starts_at_prior_not_children_and_links(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "_embed_one", lambda _t: None)
    p = _db(tmp_path)
    c1 = ledger.add_lesson("a", "r1", scope="api", source="human", path=p)   # human prior 0.75
    c2 = ledger.add_lesson("b", "r2", scope="api", source="human", path=p)
    proposal = {"trigger": "pattern", "lesson": "the general rule", "scope": "api",
                "severity": "high", "children": [c1, c2]}
    meta = synthesis.accept(proposal, path=p)
    # HONESTY: the meta-lesson starts at the 0.5 prior, NOT the children's 0.75 — confidence must
    # be earned from real tests, never faked to the cluster's.
    assert meta["author"] == "synthesis"
    assert meta["confidence"] == 0.5
    syn = [l for l in ledger.list_links(path=p) if l["type"] == "synthesizes"]
    assert len(syn) == 2 and all(l["from_id"] == meta["id"] for l in syn)
