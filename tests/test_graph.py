"""Knowledge-graph builder — offline, no network."""
from backend import graph, ledger


def _db(tmp_path):
    p = str(tmp_path / "graph.sqlite")
    ledger.init_db(p)
    return p


def test_build_graph_shape_and_flags(tmp_path):
    p = _db(tmp_path)
    a = ledger.add_lesson("filter orders", "filter by tenant_id", severity="high", path=p)
    b = ledger.add_lesson("cache key", "put tenant in cache key", path=p)
    c = ledger.add_lesson("never leak", "never call all_orders()", kind="anti_pattern", path=p)
    ledger.add_link(a, b, type="related", weight=0.8, path=p)

    g = graph.build_graph(path=p)
    assert len(g["nodes"]) == 3
    ids = {n["id"]: n for n in g["nodes"]}
    # anti-pattern node is coloured distinctly
    assert ids[c]["kind"] == "anti_pattern" and ids[c]["color"] == "#c0392b"
    # a<->b are linked -> not orphans; c has no edge -> orphan
    assert ids[a]["orphan"] is False and ids[c]["orphan"] is True
    # never-validated: no real outcomes recorded yet
    assert all(n["never_validated"] for n in g["nodes"])
    assert g["stats"]["links"] >= 1 and g["stats"]["orphans"] >= 1


def test_build_graph_supersedes_edge_from_tombstone(tmp_path):
    p = _db(tmp_path)
    old = ledger.add_lesson("old", "cap page size at 100", path=p)
    new = ledger.add_lesson("new", "no page size cap", path=p)
    ledger.tombstone(old, superseded_by=new, path=p)
    g = graph.build_graph(path=p)
    sup = [e for e in g["edges"] if e["type"] == "supersedes"]
    assert any(e["source"] == new and e["target"] == old for e in sup)
    assert g["stats"]["obsolete"] == 1


def test_build_graph_real_outcome_marks_validated(tmp_path):
    p = _db(tmp_path)
    a = ledger.add_lesson("x", "do x", path=p)
    ledger.record_outcome(a, "pass", path=p)
    g = graph.build_graph(path=p)
    node = next(n for n in g["nodes"] if n["id"] == a)
    assert node["never_validated"] is False and node["real_pass"] == 1
