"""/receipts — a lesson's confidence traces back to the real pytest outcomes that earned it."""
import os
import tempfile

import pytest

from backend import ledger, main, config


@pytest.fixture()
def temp_ledger(monkeypatch):
    p = os.path.join(tempfile.mkdtemp(prefix="rcpt_"), "l.sqlite")
    ledger.init_db(p)
    monkeypatch.setattr(config, "LEDGER_PATH", p)
    return p


def test_receipts_trace_confidence(temp_ledger):
    lid = ledger.add_lesson("t", "always clamp page_size", scope="", severity="med",
                            embedding=None, source="agent-distill", path=temp_ledger)
    for _ in range(3):
        ledger.record_outcome(lid, "pass", path=temp_ledger, injected=True)
    ledger.record_outcome(lid, "fail", path=temp_ledger, injected=True)

    r = main.receipts(lid)
    assert r["lesson_id"] == lid
    assert r["grounded"] == {"pass": 3, "fail": 1, "total": 4}
    # Beta(1,1) prior + 3 pass + 1 fail -> Beta(4,2) -> mean 4/6
    assert r["beta"] == {"alpha": 4.0, "beta": 2.0}
    assert r["confidence"] == round(4 / 6, 4)   # posterior mean, rounded to 4 places
    assert len(r["receipts"]) == 4
    assert [o["result"] for o in r["receipts"]] == ["pass", "pass", "pass", "fail"]
    assert all("ts" in o for o in r["receipts"])   # every receipt is timestamped


def test_receipts_404(temp_ledger):
    with pytest.raises(Exception):
        main.receipts(999999)
