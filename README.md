# Regress-Guard

**A memory that stops an AI coding agent from re-introducing a bug it already fixed — and its confidence is grounded in real test outcomes, not an LLM's opinion.**

Built for the **Global AI Hackathon Series with Qwen Cloud** — track **MemoryAgent**.

> Not "a chatbot with memory" (the big assistants already have that). Regress-Guard closes the
> gap they *don't*: a memory that is **outcome-grounded** (confidence moves on real `pytest`
> pass/fail) and **self-correcting** (it can demote and tombstone advice that a refactor made
> wrong). A memory that forgets what's wrong.

---

## The problem

AI coding agents are stateless across sessions. Fix a bug today, and a fresh session tomorrow
happily reintroduces it — it never learned the lesson. Chat "memory" features remember *facts you
told them*; they can't tell whether a remembered rule actually *works*.

## What Regress-Guard does

1. A test goes red and a human fixes it. **Qwen distills a reusable lesson** from the red test +
   the fix diff and stores it in a ledger.
2. In a later session, before writing code, the agent **recalls** the relevant lesson (hybrid
   BM25 + Qwen-embedding retrieval) and it is injected into the prompt — so the bug doesn't come back.
3. Every time an injected lesson leads to a **real test outcome**, its confidence updates as the
   posterior mean of a **Beta(α, β)** distribution (pass → α+1, fail → β+1). Honest numbers, not vibes.
4. When a refactor makes a lesson obsolete, **Qwen judges it and tombstones it** — the memory
   self-corrects instead of injecting stale advice forever.

## Qwen's three roles

| # | Role | Model | Where |
|---|------|-------|-------|
| 1 | **DISTILL** — red test + fix diff → lesson JSON | `qwen-plus` (JSON mode) | `backend/extractor.py` |
| 2 | **RECALL** — embed lessons + context, fuse with BM25 (RRF) | `text-embedding-v4` (1024-d) | `backend/retrieval.py`, `memory.py` |
| 3 | **REVISE** — judge whether a lesson is obsolete after a change → tombstone | `qwen-plus` | `backend/reviser.py` |

Even the coding agent in the proof harness is Qwen — Qwen both *causes* and *cures* the bug via
memory, so the demonstration is fully Qwen-native.

## The proof (this is the point)

`harness/ab_runner.py` runs the **same** coding task twice, same model (`qwen-plus`, temperature 0),
against a **hidden** `pytest`, K times each — the only difference is whether a recalled lesson is injected:

```
  A/B RESULT — get_orders tenant isolation  (model=qwen-plus, temp=0)
  Arm A  (no memory)   : 0/5 GREEN  (0%)
  Arm B  (with memory) : 5/5 GREEN  (100%)
  Δ pass-rate          : +100 points
```

Honest framing (survived an adversarial skeptical-validator pass): without the remembered project
convention the agent **mis-scopes the data access** (it invents an unsupported `user_id` filter) and
fails the tenant-isolation test; the recalled lesson steers it to the correct `tenant_id` scoping.
The hidden test enforces true tenant isolation, so it would also catch a cross-tenant leak. Runs are
statistical (pass-rate over K), and the harness uses a throwaway ledger asserted to never be the live
one — the interactive UI can't contaminate the proof.

## The UI — memory you can see and steer

- **Flashcard deck** (top-left): every lesson as a browsable, flippable card. The back shows a
  **Beta-PDF sparkline** drawn from α/β — a sharp peak = confident, flat = unsure. Confidence is also
  a border hue + fill bar. Obsolete lessons get an "OBSOLETE" stamp and sink out of the deck.
- **"By the way" console** (bottom-left): an out-of-band channel to annotate memory live —
  `/note`, `/pin`, `/demote`, `/tombstone`, `/edit`, `/revise`, or just type `by the way, …`.
- **Recall theater** (main): run a controllable coding agent in a loop; **pause / resume / stop** it,
  and drop a by-the-way note *while it runs* — it interrupts, re-recalls, and obeys the note on the
  next attempt (red → green, live). Recalled cards cross-highlight in the deck.

## Architecture

See [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) and
[`architecture/diagram.svg`](architecture/diagram.svg).

```
[Coding agent = Qwen]──MCP recall/record──►[Regress-Guard API (FastAPI, Alibaba ECS)]
      ▲ injected lesson                          ├─(1) DISTILL  qwen-plus
      │                                          ├─(2) RECALL   text-embedding-v4 + BM25/RRF
[red pytest + fix diff]──────────────►          ├─(3) REVISE   qwen-plus
                                                 ├─ Ledger (SQLite, WAL): lessons + α/β + status
                                                 └─ SSE live updates ──► Browser (deck · console · theater)
```

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

Tests: `pytest` (offline) · `pytest -m live` (hits Qwen).

## MCP integration

`mcp_tool/server.py` exposes `recall(context)` and `record(test_output, diff)` over MCP; wire it into
Claude Code (or any MCP client) via [`.mcp.json`](.mcp.json) so a real agent gains the memory.

## Attribution & license

MIT (see [`LICENSE`](LICENSE)). The retrieval fusion (BM25 + Reciprocal Rank Fusion) is adapted from
the author's own MIT-licensed [markmem](https://github.com/) engine; everything else — the ledger,
the outcome-grounded Beta confidence, the A/B harness, the Qwen wiring, the UI and the controllable
agent loop — is new for this hackathon.
