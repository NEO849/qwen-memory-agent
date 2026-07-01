"""Regress-Guard MCP server — exposes the memory to a coding agent (e.g. Claude Code).

Two tools:
  recall(context)          -> lessons to inject BEFORE writing code (avoid past mistakes)
  record(test_output, diff) -> learn a lesson AFTER a red test is fixed

This is what makes Regress-Guard a real MemoryAgent integration rather than a demo: an
agent calls `recall` at the start of a task and `record` when it fixes a failing test, so
the same class of bug does not come back in a later session.

Run (stdio):  python -m mcp_tool.server
Wire into Claude Code via .mcp.json (see repo root).
"""
from __future__ import annotations

import sys
from pathlib import Path

# make the repo root importable when launched as a standalone stdio process
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from backend import config, ledger, memory  # noqa: E402

app = FastMCP("regress-guard")


@app.tool()
def recall(context: str, k: int = 5) -> dict:
    """Recall lessons relevant to what you are about to code, so you don't repeat a past
    mistake. `context` = a short description of the task / file / function you're working on.
    Returns the lessons to follow (each with lesson text, scope, severity, confidence)."""
    ledger.init_db(config.LEDGER_PATH)
    out = memory.recall(context, k=k, path=config.LEDGER_PATH)
    return {"lessons": out["lessons"],
            "inject": memory.render_injection(out["lessons"])}


@app.tool()
def record(test_output: str, diff: str) -> dict:
    """Record a lesson AFTER you fixed a failing test. `test_output` = the red test output,
    `diff` = the fix. The lesson is distilled and stored so it is recalled next time."""
    ledger.init_db(config.LEDGER_PATH)
    return memory.ingest(test_output, diff, path=config.LEDGER_PATH)


if __name__ == "__main__":
    app.run()
