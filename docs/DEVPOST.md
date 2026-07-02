# Devpost submission content (copy-paste ready)

Track: **MemoryAgent**

## Project name
Regress-Guard

## Elevator pitch (tagline, ~1 sentence)
A memory that stops AI coding agents from re-introducing bugs they already fixed — with confidence grounded in real test outcomes, not the model's opinion.

## Inspiration
AI coding agents are stateless across sessions: you fix a bug today, and tomorrow a fresh session
happily reintroduces it. Existing "memory" features remember facts you tell them — but they can't tell
whether a remembered rule actually *works*. We wanted a memory whose trust is earned by real evidence.

## What it does
Regress-Guard is an outcome-grounded, self-correcting memory for coding agents:
- When a test goes red and a human fixes it, **Qwen distills a reusable lesson** into a ledger.
- Before writing code, the agent **recalls** the relevant lesson (hybrid BM25 + Qwen-embedding retrieval)
  and it's injected into the prompt — so the bug doesn't come back.
- Every real **pytest pass/fail** updates the lesson's confidence as the posterior mean of a Beta(α,β)
  distribution — honest numbers, not vibes.
- When a refactor makes a lesson obsolete, **Qwen judges it and tombstones it** — the memory forgets
  what's wrong instead of injecting stale advice forever.
You can watch and steer it live: a flashcard deck shows every lesson (with a Beta-curve confidence
sparkline), and an out-of-band "by the way" console lets you drop a note *while the agent runs* — it
interrupts, re-recalls, and obeys the note on its next attempt.

## How we built it
- **Qwen Cloud** in three roles: DISTILL (qwen-plus, JSON) turns red test + fix into a lesson; RECALL
  (text-embedding-v4) powers hybrid retrieval; REVISE (qwen-plus) detects obsolete lessons.
- **FastAPI + SQLite (WAL)** backend; atomic in-SQL Beta updates; Server-Sent Events for live UI.
- **Vanilla JS/CSS** frontend (no build) — flashcard deck + Beta sparkline + live console.
- **Airtight A/B harness**: same task, same model (temperature 0), K runs, hidden pytest — the only
  variable is the injected memory. Result: 0/5 green without memory, 5/5 with.
- **MCP tool** (recall / record) so any agent (e.g. Claude Code) can use the memory.
- Deployed on **Alibaba Cloud ECS** (Singapore), single uvicorn worker for in-process SSE.

## Challenges we ran into
Making the proof honest: an adversarial self-review caught us over-claiming a "cross-tenant leak," so we
re-framed it to exactly what the model does (it mis-scopes access and fails the isolation test) and made
the demo statistical (pass-rate over K runs) rather than a single lucky run.

## Accomplishments we're proud of
A memory whose confidence is grounded in real test outcomes and that can *demote and tombstone* wrong
advice — something the big chat assistants' memory structurally can't do — proven with a reproducible
0/5 → 5/5 A/B result.

## What we learned
Retrieval + an LLM isn't enough for a trustworthy memory; you need an outcome signal (real tests) and a
revision path (obsolescence) so the memory stays correct over time.

## What's next
Multiple bug patterns, editor/CI integrations, and per-repo shared team memories.

## Built with
Qwen (qwen-plus, text-embedding-v4) · Qwen Cloud · Alibaba Cloud ECS · Python · FastAPI · SQLite ·
Server-Sent Events · MCP · Vanilla JS/CSS

## Links
- GitHub: https://github.com/NEO849/qwen-memory-agent   (⚠️ set PUBLIC before final submit)
- Live demo: http://47.84.227.215
- Video: (add at the end)
