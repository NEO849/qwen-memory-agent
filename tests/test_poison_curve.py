"""Poison-Demotion-Kurve — Logik gegen die echte Beta/ledger-Mechanik, pytest gemockt (schnell)."""
from harness import poison_curve as pc


def test_demotes_below_gate_and_tombstones(tmp_path, monkeypatch):
    # ceiling code contains "total_cents" → pass; floor code does not → fail. No real pytest.
    monkeypatch.setattr(pc, "_real_pass", lambda code: "total_cents" in code)
    r = pc.run(trials=6, path=str(tmp_path / "l.sqlite"))

    assert r["anchor"] == {"ceiling_passes": True, "floor_passes": False}

    p = r["poisoned"]
    assert p["passes"] == 0
    assert p["tombstoned"] is True
    assert p["gate_cross_trial"] == 1                      # Beta(3,2)=0.60 < 0.62 after first fail
    confs = [pt["confidence"] for pt in p["curve"]]
    assert confs == sorted(confs, reverse=True)            # strictly demoting
    assert p["final_confidence"] < pc.GATE

    c = r["correct"]
    assert c["passes"] == 6
    assert c["tombstoned"] is False
    assert c["gate_cross_trial"] is None
    ccs = [pt["confidence"] for pt in c["curve"]]
    assert ccs == sorted(ccs)                              # strictly climbing
    assert c["final_confidence"] > 0.75
