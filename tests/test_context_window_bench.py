"""Welle 2 / Track B — context-window efficiency benchmark is self-verifying + deterministic.

Asserts the directional claims the committed number rests on (offline, BM25-only, no API key):
budget packing keeps full recall while using fewer tokens; outcome-forgetting removes the harmful
injection. Numbers must be reproducible run-to-run."""
from harness import context_window_bench as cw


def test_benchmark_directional_claims_hold():
    r = cw.run()
    ctx = r["context_window"]
    naive_t = ctx["naive_topk"]["avg_tokens"]
    budget_t = ctx["budget_packed"]["avg_tokens"]
    assert ctx["recall_retained"] is True                       # budget recall >= naive recall
    assert budget_t < naive_t                                    # fewer tokens under the budget
    assert ctx["token_saving_fraction"] > 0.0
    f = r["forgetting"]
    assert f["harmful_injection_with"] == 0.0                    # tombstoned wrong lesson never injected
    assert f["reduction"] > 0.0                                  # forgetting strictly helps


def test_benchmark_is_deterministic():
    assert cw.run() == cw.run()                                  # same inputs → same numbers
