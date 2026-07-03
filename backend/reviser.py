"""Qwen role 3 — REVISE: belief revision / obsolescence detection.

Memory that only ever ADDS eventually injects advice that a later refactor made wrong.
The reviser closes that gap: given a described change to the codebase, Qwen judges whether
each active lesson is now obsolete/contradicted, and if so the lesson is tombstoned
(status=obsolete, soft, auditable) instead of being injected forever.

This is the self-correcting axis — "a memory that forgets what's wrong" — which pure
add-only memories (and the big chat assistants' memory) do not do.
"""
from __future__ import annotations

from . import ledger, qwen_client, retrieval

_SYSTEM = (
    "You maintain a memory of coding lessons. The codebase just changed. Decide whether an "
    "existing remembered lesson is now OBSOLETE — i.e. the change makes the lesson wrong, "
    "unnecessary, or contradicted (e.g. the concern is now handled elsewhere). Be conservative: "
    "only mark obsolete when the change clearly supersedes the lesson; a still-valid lesson must "
    "stay active. Return ONLY JSON: {\"obsolete\": bool, \"reason\": \"one short sentence\"}."
)


def judge_obsolete(lesson: dict, change: str, model: str | None = None) -> dict:
    user = (
        f"CHANGE TO THE CODEBASE:\n{change.strip()[:4000]}\n\n"
        f"EXISTING LESSON:\n- trigger: {lesson['trigger']}\n- rule: {lesson['lesson']}\n"
        f"- scope: {lesson['scope'] or 'general'}\n\n"
        "Is this lesson now obsolete? Return the JSON now."
    )
    raw = qwen_client.chat_json(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        model=model, temperature=0,
    )
    return {"obsolete": bool(raw.get("obsolete")), "reason": str(raw.get("reason", "")).strip()}


_CONTRA_SYS = (
    "You maintain a memory of coding lessons. A NEW lesson was just taught. Compare it with an "
    "EXISTING remembered lesson that covers a similar situation. Decide if they CONTRADICT — i.e. "
    "they give opposite/incompatible guidance for the same situation, so both cannot hold at once. "
    "Similar-but-compatible (one refines or adds to the other) is NOT a contradiction. If they do "
    "contradict, the newer teaching wins (belief revision) unless the existing one is clearly more "
    "correct. Return ONLY JSON: {\"contradicts\": bool, \"loser\": \"existing\"|\"new\"|\"none\", "
    "\"reason\": \"one short sentence\"}."
)

# semantic-neighbour gate: only lessons this close in embedding space are worth an LLM judge call
_SIM_THRESHOLD = 0.55
_MAX_CANDIDATES = 4


def _judge_contradiction(new_lesson: dict, existing: dict, model: str | None = None) -> dict:
    user = (
        f"NEW LESSON:\n- trigger: {new_lesson['trigger']}\n- rule: {new_lesson['lesson']}\n"
        f"- scope: {new_lesson.get('scope') or 'general'}\n\n"
        f"EXISTING LESSON:\n- trigger: {existing['trigger']}\n- rule: {existing['lesson']}\n"
        f"- scope: {existing.get('scope') or 'general'}\n\n"
        "Do they contradict? Return the JSON now."
    )
    raw = qwen_client.chat_json(
        [{"role": "system", "content": _CONTRA_SYS}, {"role": "user", "content": user}],
        model=model, temperature=0,
    )
    loser = str(raw.get("loser", "none")).strip().lower()
    if loser not in ("existing", "new", "none"):
        loser = "none"
    return {"contradicts": bool(raw.get("contradicts")), "loser": loser,
            "reason": str(raw.get("reason", "")).strip()}


def check_contradiction(new_lesson: dict, *, path: str | None = None) -> dict:
    """When a new lesson is taught, find active lessons it CONTRADICTS and revise beliefs.

    Two-stage (cheap→expensive): vector cosine shortlists semantic neighbours, then Qwen judges
    only those for a real contradiction. The loser is tombstoned (superseded_by), so the memory
    self-heals instead of holding two opposite rules. Returns {conflicts:[...], revised:[ids]}.
    """
    new_emb = new_lesson.get("embedding")
    active = ledger.list_lessons(status="active", with_embedding=True, path=path)
    # rank candidates by semantic similarity (skip the new lesson itself, and un-embedded rows)
    scored = []
    for l in active:
        if l["id"] == new_lesson.get("id") or not l.get("embedding") or not new_emb:
            continue
        sim = retrieval._cosine(new_emb, l["embedding"])
        if sim >= _SIM_THRESHOLD:
            scored.append((sim, l))
    scored.sort(key=lambda t: t[0], reverse=True)

    conflicts: list[dict] = []
    revised: list[int] = []
    for sim, existing in scored[:_MAX_CANDIDATES]:
        verdict = _judge_contradiction(new_lesson, existing)
        if not verdict["contradicts"] or verdict["loser"] == "none":
            continue
        if verdict["loser"] == "existing":
            ledger.tombstone(existing["id"], superseded_by=new_lesson.get("id"), path=path)
            revised.append(existing["id"])
            action = "tombstoned-existing"
        else:  # the new teaching lost — retire it, keep the established lesson
            if new_lesson.get("id") is not None:
                ledger.tombstone(new_lesson["id"], superseded_by=existing["id"], path=path)
                revised.append(new_lesson["id"])
            action = "tombstoned-new"
        conflicts.append({
            "existing_id": existing["id"], "existing": existing["lesson"],
            "new_id": new_lesson.get("id"), "similarity": round(sim, 3),
            "loser": verdict["loser"], "action": action, "reason": verdict["reason"],
        })
    return {"conflicts": conflicts, "revised": revised}


def revise(change: str, *, path: str | None = None) -> list[dict]:
    """Judge every active lesson against a described change; tombstone the obsolete ones.
    Returns one verdict per active lesson (with action taken)."""
    results = []
    for lesson in ledger.list_lessons(status="active", path=path):
        verdict = judge_obsolete(lesson, change)
        if verdict["obsolete"]:
            ledger.tombstone(lesson["id"], path=path)
        results.append({"lesson_id": lesson["id"], "lesson": lesson["lesson"],
                        "obsolete": verdict["obsolete"], "reason": verdict["reason"],
                        "action": "tombstoned" if verdict["obsolete"] else "kept"})
    return results
