# Use Regress-Guard in your own coding agent (MCP) — 30 seconds

Regress-Guard isn't just a demo — it's a real **MCP tool**. Wire it into a coding agent
(Claude Code, Qwen Code, Cursor, …) and that agent gains a shared memory, **hosted on Alibaba
Cloud**, that it recalls before writing code and updates after fixing a failing test. Against the
hosted cloud, `recall` needs **no local setup and no API key**; because that memory is **shared**,
`record` (writes) needs an operator token — or run your own instance (`REGRESS_GUARD_LOCAL=1`),
where both tools are open. Either way the cloud does the distilling and retrieval.

## Two tools the agent gets
| Tool | When the agent calls it | What it does |
|---|---|---|
| `recall(context)` | **before** writing code | returns the lessons to follow (so it doesn't repeat a past mistake) + a ready-to-paste block |
| `record(test_output, diff)` | **after** fixing a red test | distills and stores a new lesson, so the bug can't come back next session |

## Setup (Claude Code)
1. Install the two deps once: `pip install mcp httpx`
2. Drop this into your project's `.mcp.json` (or your Claude Code MCP settings):

```json
{
  "mcpServers": {
    "regress-guard": {
      "command": "python",
      "args": ["-m", "mcp_tool.server"],
      "env": { "REGRESS_GUARD_URL": "http://47.84.227.215" }
    }
  }
}
```
3. Open Claude Code in this repo — the `recall` and `record` tools appear automatically.

That's it. Ask your agent to *"recall lessons before implementing get_orders"* and it will pull
the shared cloud memory; after it fixes a failing test, ask it to *"record that lesson"* — writes to
the **shared** cloud need `REGRESS_GUARD_TOKEN` in the env, or set `REGRESS_GUARD_LOCAL=1` to keep
your own ledger (where both tools are open).

## Options
- **Friendly URL:** set `REGRESS_GUARD_URL=http://regressguard.duckdns.org` (works from any machine with normal DNS).
- **Fully local:** set `REGRESS_GUARD_LOCAL=1` to use your own ledger (`data/ledger.sqlite`) + your own `DASHSCOPE_API_KEY` instead of the cloud.
- **Private deployment:** point `REGRESS_GUARD_URL` at your own instance and set `REGRESS_GUARD_TOKEN` if you enabled the gate.

## Security (why this is safe to point at a shared memory)
- **Untrusted by default.** Recalled lessons come from a store other agents/humans write to, so the
  tool treats them as untrusted (`_safety.py`, unit-tested) **before** they reach your agent: each is
  single-lined and any injected `<<<…>>>` fence marker is stripped, so content is **confined** inside
  `<<<UNTRUSTED_MEMORY>>>` markers it can't escape; injection/role/override directives are additionally
  **best-effort neutralized** (defense-in-depth, not a completeness guarantee). Same layer the backend
  uses for chat, applied at the tool.
- **Writes are gated.** On the shared cloud, `record` needs `REGRESS_GUARD_TOKEN`; `recall` is open.
- **Fails open.** A 403 / unreachable backend returns a friendly message — it never crashes your agent.
- **Transport note:** the public backend is http-only; for sensitive lessons self-host over HTTPS
  (`REGRESS_GUARD_LOCAL=1` or your own TLS instance) so the token/lessons aren't sent in cleartext.

## Verified working
```
recall("implementing get_orders …")  → #1 "Never call all_orders() and filter in Python — scope by tenant_id …"
record(red test + fix)               → learned lesson, distilled by Qwen on the cloud
recall("validating an email …")      → the just-learned lesson is now returned first
```
Any agent, anywhere, shares one outcome-grounded memory — reads open, writes token-gated so the shared cloud can't be poisoned.
