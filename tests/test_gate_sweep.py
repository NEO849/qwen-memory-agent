"""Gate-threshold sweep — logic wired, pytest mocked (ceiling passes, floor fails)."""
from harness import gate_sweep as gs


def test_wide_clean_band_and_0_62_robust(monkeypatch):
    # ceiling_solution docstrings contain "CEILING"; floor ones do not → deterministic separation
    monkeypatch.setattr(gs, "_real_pass", lambda code, pdir: "CEILING" in code)
    r = gs.run(trials=6)

    assert r["correct_confidences"] == [0.875] * 8          # 6/6 pass → Beta(7,1), across 8 classes
    assert r["poison_confidences"] == [0.125] * 8           # 0/6 fail → Beta(1,7), across 8 classes
    assert r["gate_0_62_clean"] is True
    # the clean band must be WIDE (insensitive to the exact gate) — that is the whole point
    assert r["clean_band"][0] <= 0.4 and r["clean_band"][1] >= 0.7
    # at a clean gate: all 8 correct injected, 0 poison
    clean = [s for s in r["sweep"] if s["gate"] == 0.62][0]
    assert clean["correct_injected"] == 8 and clean["poison_injected"] == 0
