"""Every bug class in the offline suite must anchor deterministically: its floor_solution
(plausible-but-wrong) FAILS its hidden test and its ceiling_solution (correct) PASSES it. This is
what makes the offline multi-class poison-demotion and gate-sweep proofs real — no Qwen, no luck."""
from pathlib import Path

from harness.poison_curve import MULTICLASS, _real_pass

_PATTERNS = Path(__file__).resolve().parent.parent / "harness" / "patterns"


def test_all_multiclass_anchors_hold():
    for name in MULTICLASS:
        d = _PATTERNS / name
        ceiling = (d / "ceiling_solution.py").read_text(encoding="utf-8")
        floor = (d / "floor_solution.py").read_text(encoding="utf-8")
        assert _real_pass(ceiling, d), f"{name}: ceiling_solution should PASS its hidden test"
        assert not _real_pass(floor, d), f"{name}: floor_solution should FAIL its hidden test"


def test_new_bug_classes_present():
    # the three classes added to generalise the mechanism beyond the original five
    for name in ("strip_prefix", "bool_env", "dedup_order"):
        assert name in MULTICLASS, f"{name} missing from MULTICLASS"
