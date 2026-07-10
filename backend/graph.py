"""Knowledge-graph view of the lesson memory — the data behind the 3D globe.

Nodes = lessons (size by Beta evidence α+β, colour by confidence green→red; grey = obsolete/
'forgotten', dark red = anti-pattern 'do-not'). Edges = the A-MEM 'related' links + 'supersedes'
(belief revision) + 'synthesizes' (meta-lessons). No LLM, cheap — a snapshot read over the ledger.
"""
from __future__ import annotations

from . import ledger


def _hue(conf: float) -> str:
    """Confidence → hue, matching the deck's meter (0 = red, 1 = green)."""
    h = round(max(0.0, min(1.0, conf)) * 120)
    return f"hsl({h} 60% 66%)"


def build_graph(*, path: str | None = None, include_obsolete: bool = True,
                as_of: str | None = None) -> dict:
    if as_of is not None:
        # bi-temporal snapshot: everything VALID at `as_of` (a lesson tombstoned today was live then).
        active = ledger.list_lessons(as_of=as_of, path=path)
        obsolete = []
    else:
        active = ledger.list_lessons(status="active", path=path)
        obsolete = ledger.list_lessons(status="obsolete", path=path) if include_obsolete else []
    counts = ledger.outcome_counts(path=path)
    links = ledger.list_links(path=path)
    lessons = active + obsolete
    ids = {l["id"] for l in lessons}

    deg: dict[int, int] = {}
    edges: list[dict] = []

    def _edge(a: int, b: int, type_: str, w: float) -> None:
        if a in ids and b in ids:
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
            edges.append({"source": a, "target": b, "type": type_, "weight": w})

    for lk in links:
        _edge(lk["from_id"], lk["to_id"], lk["type"], lk["weight"])
    # supersedes from the tombstone pointer (winner -> retired lesson)
    for l in obsolete:
        sb = l.get("superseded_by")
        if sb in ids:
            _edge(sb, l["id"], "supersedes", 1.0)

    nodes: list[dict] = []
    for l in lessons:
        c = counts.get(l["id"], {})
        rp, rf = c.get("pass", 0), c.get("fail", 0)
        is_obs = as_of is None and l["status"] == "obsolete"
        is_anti = l.get("kind") == "anti_pattern"
        orphan = deg.get(l["id"], 0) == 0 and not is_obs
        color = "#5a6577" if is_obs else ("#c0392b" if is_anti else _hue(l["confidence"]))
        nodes.append({
            "id": l["id"],
            "label": (l["trigger"] or l["lesson"] or f"#{l['id']}")[:44],
            "severity": l["severity"], "kind": l.get("kind", "guard"),
            "confidence": round(l["confidence"], 2),
            "real_pass": rp, "real_fail": rf,
            "recall_count": l.get("recall_count", 0) or 0,
            "orphan": orphan, "obsolete": is_obs, "never_validated": (rp + rf == 0),
            "val": 3.0 + float(l["alpha"]) + float(l["beta"]),
            "color": color, "desc": (l["lesson"] or "")[:180],
        })

    return {
        "nodes": nodes, "edges": edges,
        "stats": {
            "lessons": len(active), "obsolete": len(obsolete),
            "links": len(edges), "orphans": sum(1 for n in nodes if n["orphan"]),
            "never_validated": sum(1 for n in nodes if n["never_validated"] and not n["obsolete"]),
        },
    }
