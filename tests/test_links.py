"""A-MEM links + usage salience — offline, no network."""
from backend import ledger


def _db(tmp_path):
    p = str(tmp_path / "links.sqlite")
    ledger.init_db(p)
    return p


def test_add_link_related_is_canonical_and_deduped(tmp_path):
    p = _db(tmp_path)
    a = ledger.add_lesson("t1", "r1", path=p)
    b = ledger.add_lesson("t2", "r2", path=p)
    ledger.add_link(b, a, type="related", weight=0.7, path=p)
    ledger.add_link(a, b, type="related", weight=0.9, path=p)   # same undirected pair
    rel = [l for l in ledger.list_links(path=p) if l["type"] == "related"]
    assert len(rel) == 1
    assert (rel[0]["from_id"], rel[0]["to_id"]) == (min(a, b), max(a, b))


def test_add_link_supersedes_keeps_direction(tmp_path):
    p = _db(tmp_path)
    a = ledger.add_lesson("t1", "r1", path=p)
    b = ledger.add_lesson("t2", "r2", path=p)
    ledger.add_link(b, a, type="supersedes", weight=1.0, path=p)
    s = [l for l in ledger.list_links(path=p) if l["type"] == "supersedes"]
    assert (s[0]["from_id"], s[0]["to_id"]) == (b, a)


def test_add_link_self_is_noop(tmp_path):
    p = _db(tmp_path)
    a = ledger.add_lesson("t1", "r1", path=p)
    ledger.add_link(a, a, type="related", path=p)
    assert ledger.list_links(path=p) == []


def test_bump_recall_increments_without_touching_updated_at(tmp_path):
    p = _db(tmp_path)
    a = ledger.add_lesson("t1", "r1", path=p)
    before = ledger.get_lesson(a, path=p)
    ledger.bump_recall([a, a and 999999], path=p)   # unknown id is harmless
    after = ledger.get_lesson(a, path=p)
    assert after["recall_count"] == 1
    assert after["last_recalled_at"] is not None
    assert after["updated_at"] == before["updated_at"]   # usage must NOT reorder the deck
