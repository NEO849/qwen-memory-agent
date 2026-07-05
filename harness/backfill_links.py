"""One-shot: seed 'related' edges between lessons from embedding cosine, so the knowledge
graph has structure on day one. Going forward, teaching a lesson grows the graph automatically
(reviser.check_contradiction persists the semantic neighbourhood it computes).

Usage:  python -m harness.backfill_links [--threshold 0.55] [--top-k 4] [--path data/ledger.sqlite]
"""
from __future__ import annotations

import argparse

from backend import config, ledger, retrieval


def backfill(*, path: str | None = None, threshold: float = 0.55, top_k: int = 4) -> int:
    """Add a 'related' edge from each embedded lesson to its top-k nearest neighbours above
    the cosine threshold. add_link is idempotent + canonicalizes undirected pairs, so symmetric
    duplicates collapse. Returns the total link count afterwards."""
    lessons = [l for l in ledger.list_lessons(status="active", with_embedding=True, path=path)
               if l.get("embedding")]
    for a in lessons:
        sims = sorted(
            ((retrieval._cosine(a["embedding"], b["embedding"]), b["id"])
             for b in lessons if b["id"] != a["id"]),
            reverse=True)
        for sim, bid in sims[:top_k]:
            if sim < threshold:
                break
            ledger.add_link(a["id"], bid, type="related", weight=round(sim, 3), path=path)
    return len(ledger.list_links(path=path))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--top-k", type=int, default=4)
    ap.add_argument("--path", default=None)
    args = ap.parse_args()
    p = args.path or config.LEDGER_PATH
    ledger.init_db(p)
    total = backfill(path=p, threshold=args.threshold, top_k=args.top_k)
    print(f"backfill done — {total} 'related' links in {p} (threshold {args.threshold}, top-k {args.top_k})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
