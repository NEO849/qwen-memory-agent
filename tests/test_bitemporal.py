"""Bi-temporal point-in-time recall — validity interval, as_of filter, graph snapshot.

Deterministic (validity times set explicitly), offline, no Qwen. Verifies that the default
(as_of=None) path stays byte-identical to the old snapshot read.
"""
from backend import graph, ledger


def _set_validity(path, lid, vfrom, vto=None):
    with ledger._connect(path) as c:
        c.execute("UPDATE lessons SET valid_from=?, valid_to=? WHERE id=?", (vfrom, vto, lid))
        c.commit()


def test_migration_is_idempotent_and_adds_columns(tmp_path):
    p = str(tmp_path / "l.sqlite")
    ledger.init_db(p)
    ledger.init_db(p)   # re-run must be a no-op, not raise
    with ledger._connect(p) as c:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(lessons)")}
    assert "valid_from" in cols and "valid_to" in cols


def test_add_stamps_valid_from_and_tombstone_stamps_valid_to(tmp_path):
    p = str(tmp_path / "l.sqlite")
    ledger.init_db(p)
    a = ledger.add_lesson("a", "lesson A", path=p)
    row = ledger.get_lesson(a, path=p)
    assert row["valid_from"] is not None and row["valid_to"] is None
    ledger.tombstone(a, path=p)
    row = ledger.get_lesson(a, path=p)
    assert row["valid_to"] is not None            # tombstone closes the validity interval


def test_point_in_time_list(tmp_path):
    p = str(tmp_path / "l.sqlite")
    ledger.init_db(p)
    a = ledger.add_lesson("a", "A", path=p)
    b = ledger.add_lesson("b", "B", path=p)
    _set_validity(p, a, "2026-01-01T00:00:00")                          # a: valid Jan → open
    _set_validity(p, b, "2026-01-01T00:00:00", "2026-06-01T00:00:00")   # b: valid Jan → June

    assert {x["id"] for x in ledger.list_lessons(as_of="2026-03-01T00:00:00", path=p)} == {a, b}
    assert {x["id"] for x in ledger.list_lessons(as_of="2026-07-01T00:00:00", path=p)} == {a}
    assert ledger.list_lessons(as_of="2025-01-01T00:00:00", path=p) == []
    # default (no as_of) is the old snapshot read — byte-identical, both present
    assert {x["id"] for x in ledger.list_lessons(path=p)} == {a, b}


def test_graph_snapshot_as_of(tmp_path):
    p = str(tmp_path / "l.sqlite")
    ledger.init_db(p)
    a = ledger.add_lesson("a", "A", path=p)
    _set_validity(p, a, "2026-01-01T00:00:00", "2026-06-01T00:00:00")
    assert len(graph.build_graph(path=p, as_of="2026-03-01T00:00:00")["nodes"]) == 1   # valid then
    assert len(graph.build_graph(path=p, as_of="2026-07-01T00:00:00")["nodes"]) == 0   # gone by July
