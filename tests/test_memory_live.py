"""Live end-to-end facade test — hits the real Qwen API. Run with:  pytest -m live

Proves the full learn->recall path: distill a lesson from a red test+diff, embed & store it,
then recall it from a semantically-related coding context and confirm it surfaces.
"""
import os
import tempfile

import pytest

from backend import ledger, memory

pytestmark = pytest.mark.live


@pytest.fixture()
def db():
    path = os.path.join(tempfile.mkdtemp(), "live.sqlite")
    ledger.init_db(path)
    return path


def test_ingest_then_recall_surfaces_lesson(db):
    test_output = ("FAILED test_tenant_isolation - AssertionError: tenant B saw tenant A's orders\n"
                   "get_orders() returned rows across tenants")
    diff = ("-    return db.query('SELECT * FROM orders')\n"
            "+    return db.query('SELECT * FROM orders WHERE tenant_id = ?', user.tenant_id)")
    lesson = memory.ingest(test_output, diff, path=db)
    assert lesson["id"] > 0
    assert "tenant" in (lesson["lesson"] + lesson["trigger"]).lower()

    # a *different* wording of the same coding situation should still recall it
    out = memory.recall("I'm writing a function that reads orders for the current user", path=db)
    ids = [l["id"] for l in out["lessons"]]
    assert lesson["id"] in ids
    assert out["snapshot"]["count"] == 1


def test_human_note_pinned_overrides(db):
    l = memory.add_note("by the way, never log full credit card numbers",
                        pinned=True, path=db)
    assert l["source"] == "human"
    assert l["pinned"] is True
    # pinned lesson is injected even for an unrelated context (human override)
    out = memory.recall("some totally unrelated parsing task", path=db)
    assert l["id"] in [x["id"] for x in out["lessons"]]
