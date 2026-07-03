# Devpost submission content (copy-paste ready)

Track: **MemoryAgent** · Final-submit URL:
https://devpost.com/submit-to/29966-global-ai-hackathon-series-with-qwen-cloud/manage/submissions/1069845-regress-guard/finalization

## Project name
Regress-Guard

## Elevator pitch (tagline)
A memory that stops AI coding agents from re-introducing bugs they already fixed — confidence grounded in real test outcomes, not the model's opinion.

## About the project (Markdown; Devpost renders Markdown + LaTeX)
> Paste everything between the lines. If the `$$ … $$` formula shows as raw text in the Preview,
> just delete that one line — the rest still reads great.

---
**Regress-Guard is a memory that stops AI coding agents from re-introducing bugs they already fixed — and its confidence is earned from real test outcomes, not the model's opinion.**

## Inspiration
AI coding agents are stateless across sessions: you fix a bug today, and tomorrow a fresh session happily reintroduces it. Existing "memory" features remember *facts you tell them* — they can't tell whether a remembered rule actually **works**. We wanted a memory whose trust is earned by real evidence, and that forgets advice a refactor made wrong.

## What it does
When a test goes red and a human fixes it, **Qwen distills a reusable lesson** into a ledger. Before writing code, the agent **recalls** the relevant lesson (hybrid BM25 + Qwen-embedding retrieval), injected into its prompt — so the bug doesn't come back. Every real **pytest pass/fail** updates the lesson's confidence as the posterior mean of a Beta distribution:

$$ \text{confidence} = \mathbb{E}\big[\text{Beta}(\alpha,\beta)\big] = \frac{\alpha}{\alpha+\beta}, \qquad \text{pass} \Rightarrow \alpha{+}1, \quad \text{fail} \Rightarrow \beta{+}1 $$

When a refactor makes a lesson obsolete, **Qwen judges it and tombstones it** — the memory forgets what's wrong instead of injecting stale advice forever.

You can watch and steer it live: a flashcard deck shows every lesson (with a Beta-curve confidence sparkline), and an out-of-band "by the way" console lets you drop a note *while the agent runs* — it interrupts, re-recalls, and obeys the note on its next attempt.

## The proof
An A/B harness runs the same task, same model (`qwen-plus`, temperature 0) against a hidden `pytest`, K times — the only variable is the injected memory:

    Arm A  (no memory)   : 0/5 GREEN   (0%)
    Arm B  (with memory) : 5/5 GREEN   (100%)
    Δ pass-rate          : +100 points

> **Honest framing:** without the remembered convention the agent mis-scopes data access (it invents an unsupported `user_id` filter) and fails the hidden tenant-isolation test; the recalled lesson steers it to the correct `tenant_id` scoping. It's statistical (pass-rate over K runs), not one lucky run.

## How we built it
- **Qwen Cloud** in three roles: DISTILL (`qwen-plus`, JSON), RECALL (`text-embedding-v4`), REVISE (`qwen-plus`).
- **FastAPI + SQLite (WAL)** backend with atomic in-SQL Beta updates and Server-Sent Events for the live UI.
- **Vanilla JS/CSS** frontend (no build): flashcard deck + Beta sparkline + live console.
- **MCP tool** (`recall` / `record`) so any agent can use the memory.
- Deployed on **Alibaba Cloud ECS** (Singapore).

## Challenges we ran into
Making the proof honest: an adversarial self-review caught us over-claiming, so we re-framed the demo to exactly what the model does and made it statistical (pass-rate over K runs) instead of one lucky run.

## Accomplishments that we're proud of
A memory whose confidence is grounded in real test outcomes, and that can **demote and tombstone** wrong advice — something the big chat assistants' memory structurally can't do — proven with a reproducible **0/5 → 5/5** result.

## What we learned
Retrieval plus an LLM isn't enough for a memory you can trust: you also need an **outcome signal** (real test pass/fail) so confidence is *earned*, and a **revision path** (obsolescence detection) so the memory stays correct as the codebase changes. Grounding trust in evidence — not the model's own confidence — was the key insight.

## What's next for Regress-Guard
Multiple bug patterns, editor/CI integrations, and shared per-repo team memories.
---

## Built with (tags)
Qwen, qwen-plus, text-embedding-v4, Qwen Cloud, Alibaba Cloud, ECS, Python, FastAPI, SQLite, Server-Sent Events, MCP, JavaScript

## Try it out links
- https://github.com/NEO849/qwen-memory-agent   (⚠️ set PUBLIC before final submit)
- http://47.84.227.215

## Media
- Thumbnail / cover: assets/thumbnail.png  (download: http://47.84.227.215/thumbnail.png) → upload to the Devpost image gallery (first image = cover)
- Demo video (~3 min): (add at the end) → YouTube/Vimeo/Facebook, PUBLIC.
- Alibaba deploy proof: a SEPARATE short recording (rules: "separate from your demo") of `deploy/deploy_proof.sh`
  running on the ECS box — proves the backend runs on Alibaba Cloud. Plus the code-file link below.

## Additional-info answers (recap)
Individual · Germany · Newly built · start 07-01-26 · Track MemoryAgent · repo URL · code-file URL
(backend/qwen_client.py — demonstrates Qwen Cloud / DashScope API use) · architecture diagram PNG ·
Alibaba deploy PROOF (separate short recording via deploy/deploy_proof.sh) · AI tools text · all 3 checkboxes.
