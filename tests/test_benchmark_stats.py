"""Stats used by the 3-arm benchmark — Wilson CI + exact McNemar. Pure, no Qwen calls."""
from harness.benchmark import mcnemar, wilson_ci, _binom_two_sided_p


def test_wilson_edges_and_monotonic():
    assert wilson_ci(0, 0) == [0.0, 0.0]
    lo, hi = wilson_ci(5, 5)                       # all pass, n=5
    assert 0.5 < lo <= 1.0 and hi == 1.0
    lo0, hi0 = wilson_ci(0, 5)                      # none pass
    assert lo0 == 0.0 and 0.0 < hi0 < 0.5
    # tighter CI with more data at the same rate
    wide = wilson_ci(3, 5)
    narrow = wilson_ci(30, 50)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_mcnemar_one_way_and_concordant():
    # 5 pairs where arm1 passes & arm2 fails -> all discordant one way
    one_way = mcnemar([(True, False)] * 5)
    assert one_way["discordant_1not2"] == 5 and one_way["discordant_2not1"] == 0
    assert one_way["p_value"] == 0.0625            # 2*(1/2)^5, the floor at n=5
    # fully concordant -> no discordant pairs -> p=1.0
    conc = mcnemar([(True, True), (False, False)])
    assert conc["p_value"] == 1.0


def test_binom_two_sided_symmetry():
    assert _binom_two_sided_p(0, 0) == 1.0
    assert _binom_two_sided_p(5, 0) == _binom_two_sided_p(0, 5) == 0.0625
    assert _binom_two_sided_p(1, 1) == 1.0
