"""Qwen role 3 — REVISE: belief revision / obsolescence detection.

Memory that only ever ADDS eventually injects advice that a later refactor made wrong.
The reviser closes that gap: given a described change to the codebase, Qwen judges whether
each active lesson is now obsolete/contradicted, and if so the lesson is tombstoned
(status=obsolete, soft, auditable) instead of being injected forever.

This is the self-correcting axis — "a memory that forgets what's wrong" — which pure
add-only memories (and the big chat assistants' memory) do not do.
"""
from __future__ import annotations

from . import ledger, qwen_client

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
