"""Empirical calibration harness — logic + metric wiring, Qwen fully mocked (no paid calls).

Complements tests/test_calibration.py: that one proves the Beta MATH is calibrated (simulated
Bernoulli). This one wires the EMPIRICAL harness (real Qwen code, real hidden/unseen tests) whose
paid run produces calibration_result.json.
"""
from harness import calibration as C


def test_calibration_structure_and_metrics(monkeypatch):
    # with-memory → "GOOD" code that passes both tests; no-memory → "BAD" that fails both
    monkeypatch.setattr(C, "_codegen", lambda block, task, i: "GOOD" if block else "BAD")
    monkeypatch.setattr(C.G, "_runtest", lambda code, d, t: code == "GOOD")

    r = C.run(n=4)

    assert len(r["groups"]) == 10                       # 5 patterns × {floor, ceiling}
    wm = [g for g in r["groups"] if g["condition"] == "with_memory"]
    nm = [g for g in r["groups"] if g["condition"] == "no_memory"]
    assert len(wm) == 5 and len(nm) == 5

    # ceiling: high claimed confidence AND high out-of-sample rate; floor: the opposite
    assert all(g["observed_unseen"] == 1.0 for g in wm)
    assert all(g["observed_unseen"] == 0.0 for g in nm)
    assert all(g["claimed_confidence"] > 0.6 for g in wm)   # Beta(1,1)+4 passes ≈ 0.83
    assert all(g["claimed_confidence"] < 0.4 for g in nm)   # Beta(1,1)+4 fails  ≈ 0.17

    # metrics present + far better than an uninformative 0.25 coin-flip Brier
    assert 0.0 <= r["brier_score"] < 0.15
    assert 0.0 <= r["ece"] < 0.25
    assert r["reliability"] and all("mean_claimed" in b and "mean_observed" in b
                                    for b in r["reliability"])
