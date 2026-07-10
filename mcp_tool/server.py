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

Security: recalled lessons are treated as UNTRUSTED data — each is single-lined and any injected
fence marker is stripped, so content is CONFINED inside <<<UNTRUSTED_MEMORY>>> markers it cannot
escape; injection/role/override directives are additionally best-effort neutralized (defense-in-
depth, not a completeness guarantee — the consuming agent must still treat the block as data). See
_safety.py. Writes to the shared cloud are token-gated; the backend is http-only, so use
REGRESS_GUARD_LOCAL or your own HTTPS instance for sensitive data. Every tool call fails open — a
backend error (unreachable, 4xx/5xx, or a non-JSON body) never crashes the calling agent.

Run (stdio):  python -m mcp_tool.server      · Wire it in via .mcp.json (repo root).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp_tool._safety import render_lessons  # noqa: E402  — sanitizes untrusted recalled memory

RG_URL = os.environ.get("REGRESS_GUARD_URL", "http://47.84.227.215").rstrip("/")
RG_TOKEN = os.environ.get("REGRESS_GUARD_TOKEN", "")
USE_HTTP = os.environ.get("REGRESS_GUARD_LOCAL", "") != "1"

app = FastMCP("regress-guard")


def _headers() -> dict:
    return {"x-demo-token": RG_TOKEN} if RG_TOKEN else {}


# Recalled lessons are UNTRUSTED — other agents/humans write them. `_render` neutralizes injection
# directives and wraps the lessons in untrusted-data markers before they ever reach the consuming
# agent (defense-in-depth at the injection point, independent of the backend). See _safety.py.
_render = render_lessons


@app.tool()
def recall(context: str, k: int = 5) -> dict:
    """Recall lessons relevant to what you are about to code, so you don't repeat a past mistake.
    `context` = a short description of the task / file / function you're working on. Returns the
    lessons to follow (each with lesson, scope, severity, confidence) plus a ready-to-paste block."""
    if USE_HTTP:
        import httpx
        try:
            r = httpx.get(f"{RG_URL}/recall", params={"q": context, "k": k}, headers=_headers(), timeout=30.0)
            r.raise_for_status()
            lessons = r.json().get("lessons", [])
        except (httpx.HTTPError, ValueError) as e:         # incl. non-JSON 200 — never crash the caller
            return {"lessons": [], "inject": "(memory backend unreachable — proceeding without recall)",
                    "error": str(e), "source": RG_URL}
        return {"lessons": lessons, "inject": _render(lessons), "source": RG_URL}
    from backend import config, ledger, memory
    ledger.init_db(config.LEDGER_PATH)
    out = memory.recall(context, k=k, path=config.LEDGER_PATH)
    return {"lessons": out["lessons"], "inject": _render(out["lessons"]), "source": "local"}


@app.tool()
def record(test_output: str, diff: str) -> dict:
    """Record a lesson AFTER you fixed a failing test. `test_output` = the red test output,
    `diff` = the fix you applied. The lesson is distilled and stored so it is recalled next time."""
    if USE_HTTP:
        import httpx
        try:
            r = httpx.post(f"{RG_URL}/ingest", json={"test_output": test_output[:20000], "diff": diff[:20000]},
                           headers=_headers(), timeout=45.0)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:                 # friendly, not a raw crash
            if e.response.status_code in (401, 403):
                return {"recorded": False, "error": "writing to the SHARED cloud memory needs an operator "
                        "token — set REGRESS_GUARD_TOKEN in this MCP server's env, or set "
                        "REGRESS_GUARD_LOCAL=1 to record to your own ledger (recall stays open)."}
            return {"recorded": False, "error": f"memory backend returned HTTP {e.response.status_code}"}
        except (httpx.HTTPError, ValueError) as e:         # incl. non-JSON body — friendly, never a crash
            return {"recorded": False, "error": f"cannot reach memory backend: {e}"}
    from backend import config, ledger, memory
    ledger.init_db(config.LEDGER_PATH)
    return memory.ingest(test_output, diff, path=config.LEDGER_PATH)


if __name__ == "__main__":
    app.run()
