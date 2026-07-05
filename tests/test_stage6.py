"""Dedup (salience, not confidence) + decay (read-time) + retrievability — offline."""
from datetime import datetime, timezone

from backend import confidence, evaluation, ledger, memory


def _db(tmp_path):
    p = str(tmp_path / "s6.sqlite")
    ledger.init_db(p)
    return p


# --- dedup: reinforcement bumps salience, NEVER confidence (stays test-grounded) ---

def test_reinforce_merge_bumps_salience_not_confidence(tmp_path):
    p = _db(tmp_path)
    a = ledger.add_lesson("t", "r", source="human", path=p)   # human prior Beta(3,1)
    before = ledger.get_lesson(a, path=p)
    m = ledger.reinforce_merge(a, path=p)
    assert m["merge_count"] == 1
    assert m["alpha"] == before["alpha"] and m["beta"] == before["beta"]
    assert m["confidence"] == before["confidence"]


def test_dedup_merges_only_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "_embed_one", lambda _t: [1.0, 0.0, 0.0])   # identical vectors
    p = _db(tmp_path)
    # default OFF -> two separate lessons
    memory.add_note("always filter by tenant_id", scope="api", check_conflicts=False, path=p)
    memory.add_note("always filter by tenant_id", scope="api", check_conflicts=False, path=p)
    assert len(ledger.list_lessons(status="active", path=p)) == 2
    # ON -> the third near-duplicate is merged, not inserted
    monkeypatch.setattr(memory.config, "RG_DEDUP", True)
    out = memory.add_note("always filter by tenant_id", scope="api", check_conflicts=False, path=p)
    assert out.get("_deduped") is True and out["merge_count"] == 1
    assert len(ledger.list_lessons(status="active", path=p)) == 2   # still 2, reinforced not added


def test_dedup_respects_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "_embed_one", lambda _t: [1.0, 0.0, 0.0])
    monkeypatch.setattr(memory.config, "RG_DEDUP", True)
    p = _db(tmp_path)
    memory.add_note("rule", scope="api", check_conflicts=False, path=p)
    out = memory.add_note("rule", scope="db", check_conflicts=False, path=p)   # different scope
    assert not out.get("_deduped")
    assert len(ledger.list_lessons(status="active", path=p)) == 2


# --- decay: read-time, default off = unchanged, on = stale sinks toward 0.5 ---

def test_decay_default_off_is_unchanged():
    stale = {"confidence": 0.9, "status": "active", "updated_at": "2000-01-01T00:00:00+00:00"}
    assert confidence.should_inject(stale, threshold=0.7) is True          # no decay -> 0.9 >= 0.7
    assert confidence.should_inject(stale, threshold=0.7, decay=True) is False  # decayed -> below 0.7


def test_decayed_confidence_sinks_toward_prior():
    old = {"confidence": 0.9, "updated_at": "2000-01-01T00:00:00+00:00"}
    fresh = {"confidence": 0.9, "updated_at": datetime.now(timezone.utc).isoformat()}
    assert confidence.decayed_confidence(old, half_life_days=30) < 0.9
    assert confidence.decayed_confidence(old) < confidence.decayed_confidence(fresh)
    assert abs(confidence.decayed_confidence(fresh) - 0.9) < 0.01   # fresh barely moves


# --- retrievability self-quiz ---

def test_health_pct_present_and_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "_embed_one", lambda _t: None)
    p = _db(tmp_path)
    ledger.add_lesson("tenant isolation filter", "filter orders by tenant_id", path=p)
    ledger.add_lesson("pagination page size", "cap page size at 100", path=p)
    m = evaluation.metrics(path=p)
    assert 0.0 <= m["health_pct"] <= 1.0
    assert isinstance(m["stale"], list)
    assert m["health_pct"] == 1.0   # distinct triggers -> each finds itself
