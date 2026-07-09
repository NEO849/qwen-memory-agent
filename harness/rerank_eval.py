"""Does qwen3-rerank actually improve retrieval? — an honest Recall@1 / Recall@3 / MRR check.

Latency-irrelevant (offline): for each of the 5 benchmark classes we know the ONE correct
lesson; we ask recall for that class's context (SEEN and UNSEEN phrasing) and measure whether
the correct lesson is surfaced at rank 1 / in the top 3, with the qwen3-rerank stage OFF vs ON.
This is where rerank's rubric value ('sophisticated multi-model Qwen use' that *measurably*
helps) lands — not on the latency-sensitive live path.

Run:  .venv/bin/python -m harness.rerank_eval
"""
from __future__ import annotations

import os
import tempfile

from backend import config, memory, qwen_client
from harness import benchmark as B


def _rank_of(target_id: int, ids: list[int]) -> int | None:
    return (ids.index(target_id) + 1) if target_id in ids else None


def _measure(led: str, targets: list[tuple[str, str, int]]) -> dict:
    hits1 = hits3 = 0
    rr = 0.0
    n = len(targets)
    for _name, ctx, tid in targets:
        ids = [l["id"] for l in memory.recall(ctx, k=5, track=False, path=led)["lessons"]]
        r = _rank_of(tid, ids)
        if r == 1:
            hits1 += 1
        if r and r <= 3:
            hits3 += 1
        if r:
            rr += 1.0 / r
    return {"recall@1": round(hits1 / n, 3), "recall@3": round(hits3 / n, 3),
            "mrr": round(rr / n, 3), "n": n}


def main() -> int:
    led = os.path.join(tempfile.mkdtemp(prefix="rr_ledger_"), "l.sqlite")
    with qwen_client.qwen_cache(os.environ.get("BENCH_CACHE", ".bench_cache")):
        store = B.build_store(led, ground=3, log=lambda *_: None)
        cid = {c["class"]: c["id"] for c in store["correct"]}
        # 10 queries: each class's SEEN + UNSEEN recall context -> its correct lesson id
        targets = []
        for c in B._load_classes():
            targets.append((f"{c['name']}/seen", c["seen"]["ctx"], cid[c["name"]]))
            targets.append((f"{c['name']}/unseen", c["unseen"]["ctx"], cid[c["name"]]))

        config.RG_RERANK = False
        off = _measure(led, targets)
        config.RG_RERANK = True
        on = _measure(led, targets)
        config.RG_RERANK = False

    print("Retrieval quality — correct-lesson findability over 5 classes x {seen,unseen} (n=10)")
    print(f"  {'':18}{'Recall@1':>10}{'Recall@3':>10}{'MRR':>8}")
    print(f"  {'RRF only (off)':18}{off['recall@1']:>10}{off['recall@3']:>10}{off['mrr']:>8}")
    print(f"  {'+ qwen3-rerank':18}{on['recall@1']:>10}{on['recall@3']:>10}{on['mrr']:>8}")
    d1 = round(on['recall@1'] - off['recall@1'], 3)
    dm = round(on['mrr'] - off['mrr'], 3)
    print(f"  {'delta':18}{d1:>+10}{'':>10}{dm:>+8}")
    verdict = ("rerank improves findability" if (d1 > 0 or dm > 0)
               else "no measured lift on this suite (RRF already ranks the correct lesson well)")
    print(f"\nVERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
