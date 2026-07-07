"""Associative memory — Hebbian synapse growth + spreading-activation recall.

Brain-like wiring that NEVER touches confidence: co-recalled lessons wire together (synapse weight
grows with use, capped), and recall can spread along the strongest synapses to surface related
lessons that pure retrieval missed. Deterministic over the ledger/links — no Qwen.
"""
from __future__ import annotations

from backend import ledger, memory


def _mk(db: str, trigger: str) -> int:
    return ledger.add_lesson(trigger, f"rule for {trigger}", source="agent-distill", path=db)


def test_hebbian_link_grows_and_caps(tmp_path):
    db = str(tmp_path / "l.sqlite"); ledger.init_db(db)
    a, b = _mk(db, "a"), _mk(db, "b")

    ledger.reinforce_link(a, b, delta=0.1, path=db)                 # first co-recall creates it
    rel = [x for x in ledger.list_links(path=db) if x["type"] == "related"]
    assert len(rel) == 1 and abs(rel[0]["weight"] - 0.1) < 1e-9

    for _ in range(3):                                              # repeated co-recall strengthens
        ledger.reinforce_link(b, a, delta=0.1, path=db)            # order-independent (undirected)
    w = [x for x in ledger.list_links(path=db) if x["type"] == "related"][0]["weight"]
    assert abs(w - 0.4) < 1e-9

    for _ in range(20):                                            # saturates at the cap
        ledger.reinforce_link(a, b, delta=0.1, cap=1.0, path=db)
    w = [x for x in ledger.list_links(path=db) if x["type"] == "related"][0]["weight"]
    assert w == 1.0


def test_spreading_activation_surfaces_strongest_neighbour(tmp_path):
    db = str(tmp_path / "l.sqlite"); ledger.init_db(db)
    seed, strong, weak, far = (_mk(db, "seed"), _mk(db, "strong"),
                               _mk(db, "weak"), _mk(db, "far"))
    ledger.add_link(seed, strong, type="related", weight=0.9, path=db)
    ledger.add_link(seed, weak, type="related", weight=0.2, path=db)
    # 'far' is unlinked to seed
    by_id = {l["id"]: l for l in ledger.list_lessons(status="active", path=db)}

    top = memory._associative_neighbours([seed], by_id, {seed}, k=1, threshold=0.0, path=db)
    assert len(top) == 1 and top[0]["id"] == strong          # strongest synapse wins
    assert top[0]["_via"] == "association"

    both = memory._associative_neighbours([seed], by_id, {seed}, k=5, threshold=0.0, path=db)
    ids = {o["id"] for o in both}
    assert strong in ids and weak in ids and far not in ids   # only true neighbours surface
