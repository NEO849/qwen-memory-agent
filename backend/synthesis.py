"""Pattern crystallization (ExpeL — Zhao et al., AAAI 2024): when several lessons cluster around
the same area, synthesize ONE higher-level meta-lesson that captures the shared principle.

PROPOSE-only (never auto-insert). Honesty: an accepted meta-lesson starts at the normal 0.5 prior
and must EARN confidence from real tests like any other — we do NOT fake its confidence to the
children's. It is tagged author='synthesis' and linked to its children with 'synthesizes' edges
(which the knowledge globe renders as a fan).
"""
from __future__ import annotations

from collections import defaultdict

from . import ledger, qwen_client

_SYS = (
    "You maintain a memory of coding lessons. Several lessons cluster around the same area of the "
    "codebase. Write ONE higher-level meta-lesson that captures the shared principle — more general "
    "than any single child, but still concrete and actionable. Do not just concatenate them. "
    "Return ONLY JSON: {\"trigger\": \"short situation\", \"lesson\": \"the general rule\"}."
)


def _groups(active: list[dict], min_group: int) -> list[tuple[str, list[dict]]]:
    by_scope: dict[str, list[dict]] = defaultdict(list)
    for l in active:
        key = (l.get("scope") or "").strip().lower()
        if key:
            by_scope[key].append(l)
    return [(k, ls) for k, ls in by_scope.items() if len(ls) >= min_group]


def propose_synthesis(*, path: str | None = None, min_group: int = 3, model: str | None = None) -> dict:
    """Find scope-clusters of >= min_group active lessons and ask Qwen to synthesize a meta-lesson
    for each. Returns proposals only — nothing is inserted."""
    active = ledger.list_lessons(status="active", path=path)
    proposals: list[dict] = []
    for scope, group in _groups(active, min_group):
        body = "\n".join(f"- {l['lesson']}" for l in group[:12])
        user = f"LESSONS IN scope '{scope}':\n{body}\n\nWrite the meta-lesson JSON now."
        try:
            raw = qwen_client.chat_json(
                [{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
                model=model, temperature=0.2)
        except Exception:
            continue
        rule = str(raw.get("lesson", "")).strip()
        if not rule:
            continue
        proposals.append({
            "scope": scope,
            "children": [l["id"] for l in group],
            "trigger": (str(raw.get("trigger", "")).strip() or f"recurring pattern in {scope}")[:120],
            "lesson": rule,
            "severity": "high",
            "min_child_confidence": round(min(l["confidence"] for l in group), 2),
        })
    return {"proposals": proposals}


def accept(proposal: dict, *, path: str | None = None) -> dict:
    """Insert an accepted meta-lesson (starts at the normal prior — NOT the children's confidence)
    and link it to its children with 'synthesizes' edges."""
    from . import memory
    trig, rule = proposal["trigger"], proposal["lesson"]
    scope, sev = proposal.get("scope", ""), proposal.get("severity", "high")
    emb = memory._embed_one(f"{trig} {rule}")
    mid = ledger.add_lesson(trig, rule, scope=scope, severity=sev, embedding=emb,
                            source="agent-distill", author="synthesis", kind="guard", path=path)
    for cid in proposal.get("children", []):
        try:
            ledger.add_link(mid, int(cid), type="synthesizes", weight=1.0, path=path)
        except Exception:
            pass
    return ledger.get_lesson(mid, path=path)
