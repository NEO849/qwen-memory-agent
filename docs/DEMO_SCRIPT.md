# 3-minute demo script (video)

Honest framing throughout (survived an adversarial review): **without the remembered convention
the agent mis-scopes data access and fails a hidden tenant-isolation test; memory fixes it, and its
confidence is grounded in the real test outcome.** Do NOT claim Arm A "leaks across tenants" — say it
gets the access scoping wrong. The hidden test enforces isolation (it would catch a leak too).

Setup before recording: backend running on the ECS instance (`--workers 1`), browser open on it,
ledger empty (fresh `data/ledger.sqlite`). Have a terminal visible for the A/B run.

---

**0:00 — Problem (15s).**
"AI coding agents forget across sessions — fix a bug today, a fresh session reintroduces it tomorrow.
Chat memory remembers facts you tell it; it can't tell whether a remembered rule actually works.
Regress-Guard is a memory grounded in real test outcomes."

**0:15 — The proof, first (35s).** Terminal: `python -m harness.ab_runner --k 5 --verbose`.
Show the table: **Arm A 0/5 green, Arm B 5/5 green**, temp=0, same task, only difference = the
injected lesson. Point at Arm A's code (invents a `user_id` filter → fails the isolation test) vs
Arm B's code (`tenant_id` scoping). "Same model, same task — the only variable is memory."

**0:50 — See the memory (25s).** Browser. Flip a flashcard: front = the rule, back = the
**Beta(α,β) sparkline** — "confidence isn't an opinion, it's the posterior of real pass/fail." Show
the confidence hue + bar.

**1:15 — Learn live (25s).** Run the agent (▶). First attempt goes **RED** — the deck is empty, no
lesson recalled. "It doesn't know this project scopes orders by tenant."

**1:40 — Steer it out-of-band (30s) — the money shot.** While the agent is still looping, type in the
"by the way" console: *"by the way — in get_orders return only orders where tenant_id equals the
user's tenant_id; never return all orders."* A new card materializes in the deck; the console says the
agent interrupts and re-plans. The **next attempt turns GREEN**, and the recalled card cross-highlights.
"I edited its memory while it ran — next attempt it obeyed."

**2:10 — Outcome-grounded confidence (20s).** The green test bumped the lesson's confidence; show the
Beta curve sharpen / hue shift toward green on that card. "Real outcome, real confidence move."

**2:30 — Self-correction (20s).** Console: `/revise the codebase now enforces tenant scoping globally
in the DB layer; callers must not filter by tenant_id`. Qwen judges the lesson obsolete → the card gets
the **OBSOLETE stamp** and sinks. "A memory that forgets what's wrong — the big assistants don't do this."

**2:50 — Close (10s).** "Four Qwen roles — distill, recall, revise, self-check — deployed on Alibaba Cloud.
Confidence grounded in real tests. Public repo, MIT. That's Regress-Guard." Show the ECS URL + GitHub.

---

## Optional B-roll / proof shots
- `systemctl status regress-guard` (active) — deploy proof.
- `.mcp.json` + a Claude Code session calling `recall` — real MemoryAgent integration.
- `curl http://<ecs-ip>:8000/ab` — the A/B result served from the deployed instance.
