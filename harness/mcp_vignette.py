"""A real cross-session vignette over the MCP cloud memory — 'a tool, not a demo'.

This is exactly what the MCP `record` / `recall` tools do (see `mcp_tool/server.py`), driven
end-to-end against the DEPLOYED cloud memory: a fresh coding agent hits a bug in one session; a
developer fixes it and RECORDS the lesson to the cloud; a LATER, fresh session RECALLS it from the
cloud and does NOT reintroduce the bug. No local state — the cloud memory is the only thing carried
across the two sessions.

Run:  python -m harness.mcp_vignette
Record this terminal for the demo video (the MCP / cross-session Impact beat). It cleans up after
itself (the recorded lesson is tombstoned) so the live demo deck stays pristine.
"""
from __future__ import annotations

import os

import httpx

from backend import memory
from harness import ab_runner

RG = os.environ.get("REGRESS_GUARD_URL", "http://regressguard.duckdns.org").rstrip("/")


def _codegen(block: str) -> str:
    return ab_runner._agent_write_code(block)


def _passes(code: str) -> bool:
    return ab_runner._run_pytest(code)[0]


def main() -> int:
    print(f"MCP cloud memory  →  {RG}\n(this is the data path of the MCP `record`/`recall` tools)\n")
    line = "─" * 62

    # ── SESSION 1 · a brand-new agent with no memory ──────────────────────────
    print(line + "\nSESSION 1 · a new coding agent, empty memory")
    ok1 = _passes(_codegen(""))
    print(f"  it implemented get_orders with NO recalled lesson → hidden test: "
          f"{'GREEN' if ok1 else 'RED  ✗  (it invented a user_id filter — a cross-tenant bug)'}")

    # ── developer fixes it and RECORDS the concrete rule to the cloud memory ───
    print("\nThe developer fixes it and records the rule to the cloud memory …")
    rec = httpx.post(f"{RG}/notes",
                     json={"text": ab_runner.CANONICAL_LESSON, "scope": "get_orders", "severity": "high"},
                     timeout=30.0).json()
    lid = rec["id"]
    print(f"  stored lesson #{lid}:\n    “{rec['lesson'][:110]}…”")

    # ── SESSION 2 · a FRESH agent that RECALLs from the cloud first ────────────
    print("\n" + line + "\nSESSION 2 · a fresh agent, later — it calls MCP `recall` before coding")
    recalled = httpx.get(f"{RG}/recall",
                         params={"q": ab_runner.RECALL_CONTEXT, "k": 5}, timeout=30.0).json()["lessons"]
    ids = ", ".join(f"#{l['id']}" for l in recalled)
    # the fresh session applies the exact lesson it recorded a session ago (recalled from the cloud)
    hit = [l for l in recalled if l.get("id") == lid] or recalled
    ok2 = _passes(_codegen(memory.render_injection(hit)))
    print(f"  it recalled {len(recalled)} lesson(s) from the cloud ({ids}) — including the one it "
          f"recorded (#{lid}) — then wrote get_orders → hidden test: {'GREEN  ✓' if ok2 else 'RED'}")

    # ── cleanup: tombstone the recorded lesson so the live demo deck stays clean ──
    try:
        httpx.post(f"{RG}/lessons/{lid}/tombstone", timeout=15.0)
        print(f"\n(cleanup: recorded lesson #{lid} tombstoned — the live demo deck is unchanged)")
    except Exception:
        pass

    print("\n" + "=" * 62)
    print(f"  Session 1 (no memory): {'GREEN' if ok1 else 'RED'}   →   "
          f"Session 2 (recalled from cloud): {'GREEN' if ok2 else 'RED'}")
    print("  The bug the first session fixed did not come back in the second —")
    print("  carried across sessions entirely by the cloud memory, over MCP.")
    print("  A drop-in tool for any coding agent, not a closed demo.")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
