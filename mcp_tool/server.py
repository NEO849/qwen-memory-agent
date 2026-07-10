"""Regress-Guard MCP server — gives any coding agent (Claude Code, Qwen Code, …) a shared,
outcome-grounded memory. This is what makes Regress-Guard a real MemoryAgent integration, not
a demo: an agent calls `recall` before writing code and `record` after fixing a red test, so the
same class of bug does not come back in a later session.

Two tools:
  recall(context)           -> lessons to FOLLOW before writing code (avoid a past mistake)
  record(test_output, diff) -> LEARN a lesson after fixing a failing test

Backing store — zero local setup by default:
  * If REGRESS_GUARD_URL is set (default: the public Alibaba Cloud deployment), the tools talk to
    the DEPLOYED memory over HTTP — no local ledger, no Qwen key needed; the cloud does the
    distilling + hybrid retrieval. `recall` is open; because that cloud memory is SHARED, `record`
    (writes) needs an operator token (set REGRESS_GUARD_TOKEN) so it can't be poisoned by strangers.
  * Set REGRESS_GUARD_LOCAL=1 to use a local ledger + your own Qwen key instead — then it's your own
    memory and both tools are fully open.

Run (stdio):  python -m mcp_tool.server      · Wire it in via .mcp.json (repo root).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

RG_URL = os.environ.get("REGRESS_GUARD_URL", "http://47.84.227.215").rstrip("/")
RG_TOKEN = os.environ.get("REGRESS_GUARD_TOKEN", "")
USE_HTTP = os.environ.get("REGRESS_GUARD_LOCAL", "") != "1"

app = FastMCP("regress-guard")


def _headers() -> dict:
    return {"x-demo-token": RG_TOKEN} if RG_TOKEN else {}


def _render(lessons: list[dict]) -> str:
    """A compact block the agent can paste into its own context. Anti-patterns render as
    active inhibitions; everything else as guidance."""
    if not lessons:
        return "(no lessons recalled — nothing to avoid here yet)"
    lines = ["Recalled coding conventions from Regress-Guard — follow these:"]
    for l in lessons:
        rule = str(l.get("lesson", "")).strip()
        scope = l.get("scope") or "general"
        if l.get("kind") == "anti_pattern":
            lines.append(f"  ⛔ DO NOT (known past regression, {l.get('severity', 'high')}): {rule} (scope: {scope})")
        else:
            lines.append(f"  - [{l.get('severity', 'med')}] {rule} (scope: {scope})")
    return "\n".join(lines)


@app.tool()
def recall(context: str, k: int = 5) -> dict:
    """Recall lessons relevant to what you are about to code, so you don't repeat a past mistake.
    `context` = a short description of the task / file / function you're working on. Returns the
    lessons to follow (each with lesson, scope, severity, confidence) plus a ready-to-paste block."""
    if USE_HTTP:
        import httpx
        r = httpx.get(f"{RG_URL}/recall", params={"q": context, "k": k}, headers=_headers(), timeout=30.0)
        r.raise_for_status()
        lessons = r.json().get("lessons", [])
        return {"lessons": lessons, "inject": _render(lessons), "source": RG_URL}
    from backend import config, ledger, memory
    ledger.init_db(config.LEDGER_PATH)
    out = memory.recall(context, k=k, path=config.LEDGER_PATH)
    return {"lessons": out["lessons"], "inject": memory.render_injection(out["lessons"]), "source": "local"}


@app.tool()
def record(test_output: str, diff: str) -> dict:
    """Record a lesson AFTER you fixed a failing test. `test_output` = the red test output,
    `diff` = the fix you applied. The lesson is distilled and stored so it is recalled next time."""
    if USE_HTTP:
        import httpx
        r = httpx.post(f"{RG_URL}/ingest", json={"test_output": test_output[:20000], "diff": diff[:20000]},
                       headers=_headers(), timeout=45.0)
        r.raise_for_status()
        return r.json()
    from backend import config, ledger, memory
    ledger.init_db(config.LEDGER_PATH)
    return memory.ingest(test_output, diff, path=config.LEDGER_PATH)


if __name__ == "__main__":
    app.run()
