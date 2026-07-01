"""High-level memory service — the seam the API, the MCP tool and the A/B harness all use.

Ties the three Qwen roles + the ledger together:
  ingest(test_output, diff)  -> DISTILL (Qwen) -> embed -> store          (learn from a fix)
  recall(context, k)         -> embed -> snapshot -> BM25+vector RRF fuse  (inject before acting)
  record_outcome(...)        -> atomic Beta update                        (learn from the test)
  add_note(text, ...)        -> human 'by the way' lesson (verbatim or Qwen-distilled)

Every function takes an optional `path` so the harness can run against a throwaway DB —
the isolation boundary that keeps the interactive layer from ever touching the causal proof.
"""
from __future__ import annotations

from . import extractor, ledger, qwen_client, retrieval
from .confidence import should_inject


def _embed_one(text: str) -> list[float] | None:
    """Embed a single string, fail-open (None) so a transient embed error still lets
    the lesson be stored and retrieved lexically via BM25."""
    try:
        vecs = qwen_client.embed([text])
        return vecs[0] if vecs else None
    except Exception:
        return None


def _lesson_text(lesson: dict) -> str:
    return f"{lesson.get('trigger', '')} {lesson.get('lesson', '')}".strip()


def ingest(test_output: str, diff: str, *, path: str | None = None) -> dict:
    """Learn a lesson from a red test + fix diff (Qwen role 1), embed it, store it."""
    distilled = extractor.extract_lesson(test_output, diff)
    emb = _embed_one(f"{distilled['trigger']} {distilled['lesson']}")
    lid = ledger.add_lesson(
        distilled["trigger"], distilled["lesson"], scope=distilled["scope"],
        severity=distilled["severity"], embedding=emb, source="agent-distill", path=path,
    )
    return ledger.get_lesson(lid, path=path)


def add_note(text: str, *, distill: bool = False, scope: str = "", severity: str = "med",
             author: str | None = None, pinned: bool = False, path: str | None = None) -> dict:
    """Human 'by the way' note -> lesson. Default verbatim (no Qwen in the critical path);
    distill=True asks Qwen to shape it into a {trigger, lesson, scope, severity}."""
    note_raw = text.strip()
    if distill:
        shaped = extractor.extract_lesson(
            test_output="(human note, no failing test)", diff=note_raw)
        trigger, lesson = shaped["trigger"], shaped["lesson"]
        scope, severity = scope or shaped["scope"], shaped["severity"]
        source = "human-distill"
    else:
        # verbatim: first line becomes the trigger, the whole note is the rule
        trigger = note_raw.splitlines()[0][:120] if note_raw else "human note"
        lesson = note_raw
        source = "human"
    emb = _embed_one(f"{trigger} {lesson}")
    lid = ledger.add_lesson(trigger, lesson, scope=scope, severity=severity, embedding=emb,
                            source=source, author=author, note_raw=note_raw, pinned=pinned,
                            path=path)
    return ledger.get_lesson(lid, path=path)


def recall(context: str, *, k: int = 5, threshold: float = 0.0,
           path: str | None = None) -> dict:
    """Retrieve the lessons to inject for a given coding context.

    Returns {"lessons": [...], "snapshot": {...}}. The snapshot marker (count + max
    updated_at) is the happens-before evidence: a note committed before this snapshot is
    included; one committed after is guaranteed to appear on the next recall.
    """
    snapshot = ledger.list_lessons(status="active", with_embedding=True, path=path)
    snap_marker = {
        "count": len(snapshot),
        "max_updated_at": max((l["updated_at"] for l in snapshot), default=None),
    }
    if not snapshot:
        return {"lessons": [], "snapshot": snap_marker}

    q_emb = _embed_one(context)
    docs = [{"id": l["id"], "text": _lesson_text(l), "embedding": l.get("embedding")}
            for l in snapshot]
    fused = retrieval.fuse(context, docs, query_embedding=q_emb, k=max(k * 2, k))
    by_id = {l["id"]: l for l in snapshot}

    # strip the heavy embedding from returned lessons
    def clean(l: dict) -> dict:
        return {kk: vv for kk, vv in l.items() if kk != "embedding"}

    ordered: list[dict] = []
    seen: set[int] = set()
    # pinned first (human override) — included even if retrieval didn't surface them
    for l in snapshot:
        if l["pinned"] and should_inject(l, threshold=threshold):
            ordered.append(clean(l)); seen.add(l["id"])
    for doc_id, score, ex in fused:
        l = by_id.get(doc_id)
        if l and l["id"] not in seen and should_inject(l, threshold=threshold):
            item = clean(l); item["_score"] = round(score, 6); item["_explain"] = ex
            ordered.append(item); seen.add(l["id"])
        if len(ordered) >= k:
            break
    return {"lessons": ordered[:k], "snapshot": snap_marker}


def record_outcome(lesson_id: int, result: str, *, run_id: str | None = None,
                   injected: bool = True, path: str | None = None) -> dict:
    """Feed a real test outcome back into the lesson's confidence (Qwen-independent)."""
    return ledger.record_outcome(lesson_id, result, run_id=run_id, injected=injected, path=path)


def render_injection(lessons: list[dict]) -> str:
    """Format recalled lessons as a compact block for an agent's system prompt."""
    if not lessons:
        return ""
    lines = ["# Lessons from memory (avoid repeating past mistakes):"]
    for l in lessons:
        lines.append(f"- [{l['severity']}] {l['lesson']} (scope: {l['scope'] or 'general'})")
    return "\n".join(lines)
