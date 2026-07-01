"""Ledger unit tests — offline, no network. Each test uses an isolated temp DB."""
import os
import tempfile

import pytest

from backend import ledger


@pytest.fixture()
def db():
    path = os.path.join(tempfile.mkdtemp(), "t.sqlite")
    ledger.init_db(path)
    return path


def test_add_and_get(db):
    lid = ledger.add_lesson("trigger x", "always do y", scope="mod.py", severity="high", path=db)
    l = ledger.get_lesson(lid, path=db)
    assert l["lesson"] == "always do y"
    assert l["severity"] == "high"
    assert l["status"] == "active"
    assert l["confidence"] == 0.5  # Beta(1,1)


def test_human_prior_boost(db):
    lid = ledger.add_lesson("t", "human rule", source="human", path=db)
    l = ledger.get_lesson(lid, path=db)
    assert l["alpha"] == 3.0 and l["beta"] == 1.0
    assert abs(l["confidence"] - 0.75) < 1e-9


def test_outcome_increments_are_atomic_and_honest(db):
    lid = ledger.add_lesson("t", "rule", path=db)
    ledger.record_outcome(lid, "pass", path=db)
    assert abs(ledger.get_lesson(lid, path=db)["confidence"] - (2 / 3)) < 1e-9
    ledger.record_outcome(lid, "fail", path=db)
    assert ledger.get_lesson(lid, path=db)["confidence"] == 0.5  # Beta(2,2)
    assert len(ledger.outcomes_for(lid, path=db)) == 2


def test_demote_and_tombstone(db):
    lid = ledger.add_lesson("t", "rule", path=db)
    ledger.demote(lid, amount=2.0, path=db)
    assert ledger.get_lesson(lid, path=db)["confidence"] < 0.5
    ledger.tombstone(lid, path=db)
    assert ledger.get_lesson(lid, path=db)["status"] == "obsolete"


def test_pin_and_edit_bumps_rev(db):
    lid = ledger.add_lesson("t", "rule", path=db)
    ledger.set_pin(lid, True, path=db)
    assert ledger.get_lesson(lid, path=db)["pinned"] is True
    ledger.edit_lesson(lid, lesson="corrected rule", path=db)
    l = ledger.get_lesson(lid, path=db)
    assert l["lesson"] == "corrected rule"
    assert l["rev"] == 2


def test_snapshot_orders_pinned_first(db):
    a = ledger.add_lesson("a", "first", path=db)
    b = ledger.add_lesson("b", "second", path=db)
    ledger.set_pin(b, True, path=db)
    rows = ledger.list_lessons(status="active", path=db)
    assert rows[0]["id"] == b  # pinned floats to front


def test_embedding_roundtrip(db):
    vec = [0.1, -0.2, 0.3, 0.4]
    lid = ledger.add_lesson("t", "rule", embedding=vec, path=db)
    got = ledger.get_lesson(lid, with_embedding=True, path=db)["embedding"]
    assert got is not None and len(got) == 4
    assert all(abs(a - b) < 1e-6 for a, b in zip(vec, got))
