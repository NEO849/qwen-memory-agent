"""The memory measures and improves ITSELF (adapted from the author's MIT markmem eval/tune).

evaluate(): for a sample of lessons, Qwen writes a KEYWORD-FREE paraphrase question (so pure
  BM25 can't cheat on word overlap — only real meaning finds the card). We then measure Recall@1/3
  and MRR, with the vector arm ON vs OFF, proving the semantic leg earns its place.
tune(): grid-search the RRF fusion weights against the measured Recall@1 gold set and persist the
  best config — but only if it beats the neutral baseline. Closes the meta-loop: a memory that
  tunes how it retrieves, measured against its own hit-rate.
metrics(): a compact 'memory health' snapshot (retrieval + grounding + calibration).

Honest by construction: numbers come from real retrieval runs; tune adopts nothing that doesn't beat
baseline. This is what turns Regress-Guard from 'a memory' into a self-measuring, self-tuning memory.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from . import config, ledger, qwen_client, retrieval

_PARA_SYS = (
    "You test a coding-lesson memory. Given a lesson, write ONE natural developer question whose "
    "correct answer needs exactly this lesson — but describe the SITUATION in different words and do "
    "NOT reuse the lesson's distinctive keywords/identifiers (e.g. avoid field names like 'tenant_id', "
    "'idempotency'). Force real meaning, not word overlap. Return ONLY the question, one sentence."
)

# gold set is expensive (N Qwen paraphrase calls) — cache it so "Measure" then "Self-tune" on the
# SAME unchanged ledger reuses it. Keyed by (path, ledger-signature) so a different ledger or any
# edit since the last build forces a rebuild instead of scoring against stale gold.
_gold_cache: dict = {}   # {"key": (path, marker), "gold": (docs, items)}


def _marker(path: str | None) -> tuple:
    rows = ledger.list_lessons(status="active", path=path)
    return (path, len(rows), max((r["updated_at"] for r in rows), default=None))


def _paraphrase(lesson: dict) -> str:
    user = f"LESSON: {lesson['lesson']}\n(trigger: {lesson.get('trigger', '')})\nWrite the question now."
    try:
        return qwen_client.chat(
            [{"role": "system", "content": _PARA_SYS}, {"role": "user", "content": user}],
            temperature=0.4).strip().strip('"')
    except Exception:
        return lesson.get("trigger") or lesson["lesson"]


def _build_gold(path: str | None, sample: int) -> tuple[list, list]:
    """Return (docs, items). docs = all active lessons as retrieval docs; items = paraphrase probes."""
    lessons = ledger.list_lessons(status="active", with_embedding=True, path=path)
    docs = [{"id": l["id"], "text": f"{l.get('trigger','')} {l['lesson']}", "embedding": l.get("embedding")}
            for l in lessons]
    if len(lessons) < 2:
        return docs, []
    rng = random.Random(7)
    chosen = lessons if len(lessons) <= sample else rng.sample(lessons, sample)
    items = []
    for l in chosen:
        q = _paraphrase(l)
        try:
            qemb = qwen_client.embed([q])[0]
        except Exception:
            qemb = None
        items.append({"target": l["id"], "query": q, "qemb": qemb})
    _gold_cache["key"] = _marker(path)
    _gold_cache["gold"] = (docs, items)
    return docs, items


def _recall(items: list, docs: list, weights: dict, use_vector: bool) -> dict:
    h1 = h3 = 0; mrr = 0.0; n = len(items)
    if not n:
        return {"recall_at_1": 0.0, "recall_at_3": 0.0, "mrr": 0.0, "n": 0}
    for it in items:
        fused = retrieval.fuse(it["query"], docs, query_embedding=(it["qemb"] if use_vector else None),
                               weights=weights, k=len(docs))
        ranked = [r[0] for r in fused]
        if it["target"] in ranked:
            rank = ranked.index(it["target"]) + 1
            if rank == 1: h1 += 1
            if rank <= 3: h3 += 1
            mrr += 1.0 / rank
    return {"recall_at_1": round(h1 / n, 3), "recall_at_3": round(h3 / n, 3),
            "mrr": round(mrr / n, 3), "n": n}


def _current_weights() -> dict:
    try:
        w = json.loads(Path(config.RETRIEVAL_CONFIG).read_text(encoding="utf-8"))
        return {"bm25": float(w.get("bm25", 1.0)), "vector": float(w.get("vector", 1.0))}
    except Exception:
        return {"bm25": 1.0, "vector": 1.0}


def evaluate(path: str | None = None, sample: int = 8) -> dict:
    """Measure retrieval quality on keyword-free paraphrase queries; A/B the vector arm."""
    docs, items = _build_gold(path, sample)
    w = _current_weights()
    return {"n": len(items), "weights": w,
            "vector_on": _recall(items, docs, w, use_vector=True),
            "vector_off": _recall(items, docs, w, use_vector=False)}


def tune(path: str | None = None, sample: int = 8) -> dict:
    """Grid-search RRF weights against Recall@1 (MRR tiebreak); persist only if it beats baseline."""
    # reuse the gold set only if it was built for THIS ledger in its current state
    if _gold_cache.get("key") == _marker(path) and _gold_cache.get("gold"):
        docs, items = _gold_cache["gold"]
    else:
        docs, items = _build_gold(path, sample)
    if not items:
        return {"tuned": False, "reason": "not enough lessons", "n": 0}
    baseline_w = {"bm25": 1.0, "vector": 1.0}
    base = _recall(items, docs, baseline_w, True)
    best_w, best = baseline_w, base
    for bm in (0.5, 1.0, 1.5, 2.0):
        for vec in (0.5, 1.0, 1.5, 2.0, 3.0):
            w = {"bm25": bm, "vector": vec}
            r = _recall(items, docs, w, True)
            if (r["recall_at_1"], r["mrr"]) > (best["recall_at_1"], best["mrr"]):
                best_w, best = w, r
    improved = (best["recall_at_1"], best["mrr"]) > (base["recall_at_1"], base["mrr"])
    if improved:
        Path(config.RETRIEVAL_CONFIG).parent.mkdir(parents=True, exist_ok=True)
        Path(config.RETRIEVAL_CONFIG).write_text(json.dumps(best_w), encoding="utf-8")
    return {"tuned": improved, "baseline": base, "best": best, "weights": best_w, "n": len(items)}


def metrics(path: str | None = None) -> dict:
    """Compact memory-health snapshot: grounding + calibration (no LLM, cheap)."""
    active = ledger.list_lessons(status="active", path=path)
    obsolete = ledger.list_lessons(status="obsolete", path=path)
    outcomes = 0; conf_sum = 0.0; gap_sum = 0.0; gap_n = 0
    for l in active:
        passes = max(0.0, l["alpha"] - 1.0); fails = max(0.0, l["beta"] - 1.0)
        outcomes += int(passes + fails); conf_sum += l["confidence"]
        if passes + fails > 0:                       # calibration: predicted vs empirical pass-rate
            gap_sum += abs(l["confidence"] - passes / (passes + fails)); gap_n += 1
    n = len(active)
    return {
        "lessons_active": n, "lessons_obsolete": len(obsolete),
        "grounded_outcomes": outcomes,
        "avg_confidence": round(conf_sum / n, 3) if n else 0.0,
        "calibration_gap": round(gap_sum / gap_n, 3) if gap_n else 0.0,
        "weights": _current_weights(),
    }
