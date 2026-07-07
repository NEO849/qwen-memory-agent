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

You can watch and steer it live from one clean surface: **Chat** with the agent, edit the memory beside it (a flashcard deck with a Beta-curve confidence meter — pin, demote or forget any lesson), and toggle into a **3D knowledge globe** or the **🏆 Proof** view in the same frame. Teach a rule while the agent runs and it re-recalls and obeys it on the next attempt.

The memory also carries **anti-patterns** — dead-end rules a past regression proved wrong — which are injected as active **⛔ DO NOT** inhibitions rather than guidance, so the agent is steered *away* from a known bad path, not just toward a good one. And it can **crystallize** a cluster of related lessons into one higher-level meta-lesson (ExpeL-style synthesis) that then earns its own confidence from real tests like any other.

The memory is also **associative in a brain-*inspired* way** (honest wording — associative memory, not consciousness): lessons recalled together **wire together** via a Hebbian synapse whose weight grows with co-recall (capped), and an opt-in **spreading-activation** recall follows the strongest synapses to surface associated neighbours pure search misses. Crucially, this wiring **never touches a lesson's confidence** — that stays earned from real test outcomes.

**The 3D knowledge globe** makes the whole memory legible (currently **66 nodes / 196 edges**): every lesson is a node (size = evidence α+β, colour = confidence, grey = forgotten, dark-red = anti-pattern), wired by *related* (179) / *supersedes* (1, belief revision) / *synthesizes* (16, crystallization) edges; each edge's strength is initialised from embedding-cosine similarity and then further strengthened by Hebbian co-recall on the synapses that actually co-fire (capped). Click any node and its strands light up by type — you see at a glance what a memory connects to, what replaced it, and what it was distilled into.

**The memory also measures, tunes and corrects itself:**
- **Self-evaluation.** Qwen writes *keyword-free* paraphrase questions (so lexical BM25 can't win on word overlap) and we measure **Recall@1 / MRR** with the semantic leg on vs off — the memory grades its own retrieval quality on evidence, not vibes.
- **Self-tuning.** It grid-searches its BM25+vector fusion weights against that measured Recall@1 and **adopts new weights only if they beat the baseline** — a memory that tunes *how* it remembers (in our runs, Recall@1 **0.75 → 1.00**).
- **Contradiction detection.** When you teach a new rule, a cheap→expensive check (vector-cosine shortlist → Qwen judge) spots a rule that **contradicts** an existing one and tombstones the loser — the memory never holds two opposite rules.
A live "memory-quality" panel surfaces Recall@1, the semantic lift, a **calibration gap** (displayed confidence vs empirical pass-rate), and grounded-outcome count.

## The proof
An A/B harness runs the same task, same model (`qwen-plus`, temperature 0) against a hidden `pytest` the agent never sees. The task never states our tenant convention, so the knowledge must come from memory. Three honest measurements, not one number:

    Floor    (no memory)                          : 0/5 GREEN   → invents order['user_id'] == user['id']
    Ceiling  (remembered developer fix, verbatim)  : 5/5 GREEN   → scopes  order['tenant_id'] == user['tenant_id']
    Distillation reliability (shipped auto-distiller): 10/10 pass, Wilson95 [72,100]%

> **Honest framing:** the **ceiling** (5/5) is the *capability ceiling* of memory injection — the remembered human fix replayed verbatim — not the shipped default. What we ship is an **auto-distiller** that turns the red test + fix into a lesson; measured separately, **10 of 10 independent distillations** passed the hidden test (Wilson95 [72,100]%). The core contribution is **test-grounded self-correction**: a distillation that drops the concrete comparison **fails the hidden test and is demoted**, so confidence tracks what actually works. The temp-0 in-run trials are a consistency check, not an independent sample — only the distillations are, which is why the Wilson interval lives there. We never claim "guaranteed 100%".

**Generalisation across 3 bug classes** (`harness/generalization.py`) kills the cherry-pick objection. Memory flips the two classes the base model gets **wrong** by default — *tenant isolation* and *pagination leak* — from **0/3 → 3/3** each. On *money rounding* Qwen already writes correct code unaided (floor **3/3**), so memory adds **no** lift and does **no** harm (ceiling 3/3). Two independent 0→100 flips defeat cherry-picking; the third shows the memory is harmless when it isn't needed. The shipped auto-distiller is **18/18** (Wilson95 82–100%) across all three classes.

## How we built it
- **Qwen Cloud** in four roles: DISTILL (`qwen-plus`, JSON), RECALL (`text-embedding-v4`), REVISE (`qwen-plus`), and SELF-CHECK (`qwen-plus` — paraphrase-based self-evaluation + contradiction judging).
- **Self-measurement layer** (`evaluation.py`): keyword-free Recall@1/MRR, RRF weight self-tuning (persisted only if it beats baseline), and a calibration snapshot from *real* recorded outcomes.
- **FastAPI + SQLite (WAL)** backend with atomic in-SQL Beta updates and Server-Sent Events for the live UI.
- **Vanilla JS/CSS** frontend (no build): one clinical surface — Chat, an editable memory deck with a Beta confidence meter, a **3D force-directed knowledge globe** (self-contained, CDN-free) with click-to-highlight strands, and the 🏆 Proof view.
- **A-MEM auto-linking + ExpeL crystallization** (`graph.py`, `synthesis.py`): lessons wire themselves into a graph (related / supersedes / synthesizes) and clusters can be distilled into meta-lessons that earn their own confidence.
- **Associative memory** (Hebbian wiring + spreading activation): lessons recalled together strengthen a capped synapse weight, and an opt-in spreading-activation recall walks the strongest synapses to surface neighbours pure retrieval misses — neuroscience-*inspired*, and deliberately kept separate from confidence (which stays test-earned). The globe now shows **66 nodes / 196 edges** with variable synapse strength.
- **Anti-pattern inhibitions**: dead-end lessons render as **⛔ DO NOT** directives so the agent avoids a known regression, not just repeats a known fix.
- **MCP tool** (`recall` / `record`) so any agent — Claude Code, Qwen, any coding agent — can use the memory as a drop-in.
- **Memory-injection defense** (`memory.py`): recalled lessons enter the prompt as *untrusted data* behind structural markers and a **deterministic sanitizer** that strips embedded instruction/role directives — so a poisoned lesson can't become a command (second-order prompt injection). Validated by our own red-team.
- Deployed on **Alibaba Cloud ECS** (Singapore).

## Challenges we ran into
Making the proof honest: an adversarial self-review caught us over-claiming, so we re-framed the demo to exactly what the model does and made it statistical (pass-rate over K runs) instead of one lucky run.

## Accomplishments that we're proud of
A memory whose confidence is grounded in real test outcomes, that can **demote and tombstone** wrong advice, and that **measures and tunes its own retrieval** and **resolves contradictions on teach** — things the big chat assistants' memory structurally can't do. Proven with a reproducible **floor 0/5 → ceiling 5/5**, a shipped auto-distiller measured at **10/10 (Wilson95 72–100%)**, **generalisation across 3 bug classes** (two independent 0→100 flips plus one class where memory is correctly harmless), and a self-measured **Recall@1 0.75 → 1.00**.

We also **red-teamed our own agent**: because recalled lessons are injected into the system prompt, a poisoned lesson is a real attack surface (memory-poisoning). We hardened it — structural isolation + a deterministic sanitizer + persona rules — flipping our poisoned-memory probe from **vulnerable → safe** and passing a 60-case automated red-team scan clean.

## What we learned
Retrieval plus an LLM isn't enough for a memory you can trust: you also need an **outcome signal** (real test pass/fail) so confidence is *earned*, and a **revision path** (obsolescence detection) so the memory stays correct as the codebase changes. Grounding trust in evidence — not the model's own confidence — was the key insight. Generalising the proof to three bug classes taught us a second discipline: to be honest you have to **show the class where your idea does nothing** (money rounding), not just the ones where it shines. And when we added brain-*inspired* associative wiring (Hebbian synapses, spreading activation), the rule that kept it honest was to keep that wiring **out of the confidence signal** — association helps recall find things; only real tests move trust.

## What's next for Regress-Guard
More bug patterns beyond the current three, editor/CI integrations, and shared per-repo team memories.
---

## Built with (tags)
Qwen, qwen-plus, text-embedding-v4, Qwen Cloud, Alibaba Cloud, ECS, Python, FastAPI, SQLite, Server-Sent Events, MCP, JavaScript

## Try it out links
- https://github.com/NEO849/qwen-memory-agent   (⚠️ set PUBLIC before final submit)
- http://regressguard.duckdns.org   (live demo — friendly URL, also works behind IP-blocking filters)
- http://47.84.227.215   (same server, direct-IP fallback)

## Media
- Thumbnail / cover: assets/thumbnail.png  (download: http://47.84.227.215/thumbnail.png) → upload to the Devpost image gallery (first image = cover)
- Demo video (< 3 min): (add at the end) → **YouTube / Vimeo / Youku (NOT Facebook)**, PUBLIC, **English**
  (or English subtitles — required by the Official Rules).
- Alibaba deploy proof: per the binding Official Rules the required proof is the **code-file link** below
  (`backend/qwen_client.py`). A short `deploy/deploy_proof.sh` recording on the ECS box is OPTIONAL/recommended.
- Keep the ECS server running until the Judging Period ends (~Jul 31) — the project must stay testable.

## Additional-info answers (recap)
Individual · Germany · Newly built · start 07-01-26 · Track MemoryAgent · repo URL · code-file URL
(backend/qwen_client.py — demonstrates Qwen Cloud / DashScope API use) · architecture diagram PNG ·
Alibaba deploy PROOF (separate short recording via deploy/deploy_proof.sh) · AI tools text · all 3 checkboxes.
