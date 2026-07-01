"""Confidence math + injection policy — offline."""
from backend import confidence as c


def test_posterior_mean():
    assert c.posterior_mean(1, 1) == 0.5
    assert abs(c.posterior_mean(2, 1) - 2 / 3) < 1e-9
    assert c.posterior_mean(0, 0) == 0.0  # degenerate guard


def test_variance_shrinks_with_evidence():
    assert c.posterior_variance(2, 2) > c.posterior_variance(20, 20)


def test_evidence_count_excludes_priors():
    assert c.evidence_count(1, 1) == 0
    assert c.evidence_count(4, 2) == 4  # 3 passes + 1 fail over the (1,1) prior


def test_should_inject_policy():
    active = {"status": "active", "pinned": False, "confidence": 0.6}
    assert c.should_inject(active, threshold=0.5) is True
    assert c.should_inject(active, threshold=0.7) is False
    # pinned bypasses the confidence gate
    assert c.should_inject({"status": "active", "pinned": True, "confidence": 0.0},
                           threshold=0.9) is True
    # obsolete is never injected, even if pinned
    assert c.should_inject({"status": "obsolete", "pinned": True, "confidence": 1.0}) is False


def test_beta_pdf_handles_degenerate():
    # must not raise / divide by zero at the edges
    assert c.beta_pdf(1, 1, 0.0) > 0
    assert c.beta_pdf(0, 0, 0.5) > 0
    # a sharp Beta(20,2) peaks near its mean, not at 0.1
    assert c.beta_pdf(20, 2, 0.9) > c.beta_pdf(20, 2, 0.1)
