<p align="center">
  <img src="assets/banner.png" alt="Regress-Guard — a memory that forgets what's wrong" width="960">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-5FD787?style=flat-square" alt="MIT">
  <img src="https://img.shields.io/badge/Qwen_Hackathon-MemoryAgent-5AC8F5?style=flat-square" alt="Track: MemoryAgent">
  <img src="https://img.shields.io/badge/Built_with-Qwen_Cloud-F0C35A?style=flat-square" alt="Qwen Cloud">
  <img src="https://img.shields.io/badge/Deployed-Alibaba_Cloud_ECS-5FD787?style=flat-square" alt="Alibaba Cloud">
  <img src="https://img.shields.io/badge/UI-no_build_step-8A93A0?style=flat-square" alt="No build">
</p>

<p align="center"><em>A memory that stops AI coding agents from re-introducing bugs they already fixed —<br>with confidence earned from real test outcomes, not the model's opinion.</em></p>

---

## The problem

AI coding agents are stateless across sessions: you fix a bug today, and a fresh session tomorrow
happily reintroduces it. Existing "memory" features remember *facts you tell them* — they can't tell
whether a remembered rule actually **works**. Regress-Guard is a memory whose trust is **earned by
real evidence**, and that **forgets advice a refactor made wrong**.

## The proof (this is the point)

`harness/ab_runner.py` runs the **same** coding task, **same** model (`qwen-plus`, temperature 0),
against a **hidden** `pytest`, K times — the only variable is whether a recalled lesson is injected:

```
  A/B RESULT — get_orders tenant isolation   (model=qwen-plus, temp=0)
  Arm A  (no memory)   : 0/5 GREEN   (0%)
  Arm B  (with memory) : 5/5 GREEN   (100%)
  Δ pass-rate          : +100 points
```

**Honest framing** (it survived an adversarial self-review): without the remembered project
convention the agent **mis-scopes data access** — it invents an unsupported `user_id` filter and fails
the hidden tenant-isolation test; the recalled lesson steers it to the correct `tenant_id` scoping. The
test enforces true isolation, so it would also catch a cross-tenant leak. Reproduce it yourself:

```bash
python -m harness.ab_runner --k 5 --verbose
```

## Qwen's three roles

| # | Role | Model | Where |
|---|------|-------|-------|
| 1 | **DISTILL** — red test + fix diff → lesson JSON | `qwen-plus` (JSON mode) | `backend/extractor.py` |
| 2 | **RECALL** — embed lessons + context, fuse with BM25 (RRF) | `text-embedding-v4` (1024-d) | `backend/retrieval.py`, `memory.py` |
| 3 | **REVISE** — is a lesson now obsolete? → tombstone | `qwen-plus` | `backend/reviser.py` |

Even the coding agent in the proof harness is Qwen — Qwen both *causes* and *cures* the bug via memory.

## Architecture

<p align="center"><img src="architecture/diagram.png" alt="Architecture" width="880"></p>

Outcome-grounded confidence lives in a SQLite ledger (WAL, atomic in-SQL Beta updates); the browser is
fed live over Server-Sent Events; an MCP tool exposes the memory to any agent. Details:
[`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md).

## What you can see and steer

- **Flashcard deck** — every lesson as a browsable, flippable card. The back draws a **Beta(α,β)
  sparkline** from the real pass/fail counts (sharp peak = confident, flat = unsure). Confidence is also
  a border hue + fill bar; obsolete lessons get an "OBSOLETE" stamp and sink out of the deck.
- **"By the way" console** — an out-of-band channel to edit memory live: `/note`, `/pin`, `/demote`,
  `/tombstone`, `/edit`, `/revise`, or just type `by the way, …`.
- **Recall theater** — run a controllable coding agent in a loop (**pause / resume / stop**), and drop a
  by-the-way note *while it runs*: it interrupts, re-recalls, and obeys the note on its next attempt
  (red → green, live). Recalled cards cross-highlight in the deck.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set DASHSCOPE_API_KEY + QWEN_BASE_URL (Qwen Cloud workspace host)

python -m backend.qwen_client          # connectivity test against Qwen
python -m harness.ab_runner --k 5 -v   # reproduce the A/B proof
uvicorn backend.main:app --workers 1   # then open http://localhost:8000
```

> **`--workers 1` is required** — the live-update fan-out (SSE) is in-process.
> Tests: `pytest` (offline) · `pytest -m live` (hits Qwen).

## MCP integration

`mcp_tool/server.py` exposes `recall(context)` and `record(test_output, diff)` over MCP; wire it into
Claude Code (or any MCP client) via [`.mcp.json`](.mcp.json) so a real agent gains the memory.

## Deployment

Runs as a single process on **Alibaba Cloud ECS** (Singapore) — see [`deploy/README.md`](deploy/README.md).

## Attribution & license

MIT (see [`LICENSE`](LICENSE)). The retrieval fusion (BM25 + Reciprocal Rank Fusion) is adapted from the
author's own MIT-licensed **markmem** engine; everything else — the ledger, the outcome-grounded Beta
confidence, the A/B harness, the Qwen wiring, the UI, and the controllable agent loop — is new for this
hackathon.
