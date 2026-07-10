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

> **Watch this in 60 seconds** — three things nothing else in this track does:
> - **The proof:** same AI, same task, temperature 0 — **0/5 without memory → 5/5 with Regress-Guard**, five hidden `pytest` running live.
> - **Qwen recalls its own memory:** the model *decides on its own* to call a `recall_memory` tool — and it **forgets what's wrong** (a lesson that fails real tests is tombstoned, not injected forever).
> - **Earned, not asserted:** every confidence number traces to append-only test outcomes at `/receipts/{id}` — nobody hand-writes them.

## Inspiration
AI coding agents are stateless across sessions: you fix a bug today, and tomorrow a fresh session happily reintroduces it. Existing "memory" features remember *facts you tell them* — they can't tell whether a remembered rule actually **works**. We wanted a memory whose trust is earned by real evidence, and that forgets advice a refactor made wrong.

## What it does
Regress-Guard is a **persistent memory that autonomously accumulates experience** from an agent's own work, so the agent makes **increasingly accurate decisions across multi-turn, cross-session interactions**.

When a test goes red and a human fixes it, **Qwen distills a reusable lesson** into a ledger (**efficient memory storage and retrieval** — hybrid BM25 + Qwen-embedding recall). Before writing code, the agent **recalls** the relevant lesson, injected into its prompt — top-k recall plus active anti-pattern inhibitions is exactly **recalling critical memories within limited context windows** — so the bug doesn't come back. In chat the agent consults its memory **autonomously via a Qwen function-call** (a `recall_memory` tool it decides to invoke, and formulates the query for, on its own). Every real **pytest pass/fail** updates the lesson's confidence as the posterior mean of a Beta distribution:

$$ \text{confidence} = \mathbb{E}\big[\text{Beta}(\alpha,\beta)\big] = \frac{\alpha}{\alpha+\beta}, \qquad \text{pass} \Rightarrow \alpha{+}1, \quad \text{fail} \Rightarrow \beta{+}1 $$

When a refactor makes a lesson obsolete, **Qwen judges it and tombstones it** — that is **timely forgetting of outdated information**: the memory forgets what's wrong instead of injecting stale advice forever.

We make **"limited context windows"** literal, not rhetorical: an optional **value-density packer** (`confidence × relevance ÷ token_cost` under a hard token budget) injects the critical lesson in **~37 % fewer tokens at identical recall**, and tombstoning a wrong lesson cuts harmful injection **100 % → 0 %** — both reproducible offline with no API key (`python -m harness.context_window_bench`, [`docs/benchmark.md`](../docs/benchmark.md)). *(Honest scope: a domain-specific subset. We also run an external **LongMemEval `knowledge-update`** anchor (oracle split — see The proof), but not the full-haystack LoCoMo / LongMemEval leaderboard runs.)*

*How it maps to the track (MemoryAgent):* a persistent memory that autonomously accumulates experience for increasingly accurate decisions across multi-turn, cross-session interactions — with efficient storage/retrieval, timely forgetting of outdated information (tombstone/supersede), and recall of critical memories within limited context windows (value-density token-budget packing + anti-pattern injection).

You watch and steer it live from one **living-memory** surface — three columns in one frame. **LEFT:** the editable memory (a card deck — **pin / demote / forget / revise**, **Teach** a rule, add a **⛔ don't**, and **Run / Pause / Stop** the agent, each lesson with a Beta-curve confidence meter). **MIDDLE:** a normal AI chat with a **[💬 Chat · 🏆 Proof · ⚔️ Duel]** toggle. **RIGHT:** the **persistent 3D knowledge globe, always visible**. **Live-recall highlight:** when chat or the agent recalls lessons, exactly those nodes pulse live on the globe (white flash + particles over their real edges) while the answer streams — so you see the memory *and* its use at once. Only the **real recalled lesson IDs** pulse (the same IDs as the "answered using N lessons: #.." strip). Teach a rule while the agent runs and it re-recalls and obeys it on the next attempt; on mobile the layout degrades to a stack.

The **⚔️ Live Duel** tab makes the whole thesis fireable on demand: one prompt, two AIs side by side — **"plain AI · no memory"** vs. **"AI + Regress-Guard"**. Hit **▶ Run 5 live** and 5 hidden `pytest` run in real time, a green/red counter ticking over each arm and the winner pane glowing — **0/5 vs 5/5**, live. It is the *live, un-recorded* twin of the 🏆 Proof replay (which stays the instant, flicker-safe recording of the same experiment). Honest by design: the memory arm injects the remembered concrete lesson through a **determinism guard**, disclosed in the SSE stream as `"injected":"canonical (determinism guard)"`, so an on-camera run can't flake — it is the injection *ceiling* live, never a live distillation, and never framed as "guaranteed".

This isn't a closed demo — it's a **drop-in tool**, and you can watch it carry a fix across two sessions of the live cloud memory (`python -m harness.mcp_vignette`). **Session 1** is a fresh agent with empty memory: it writes `get_orders`, the hidden test goes **red** (it invents a `user_id` filter — a cross-tenant bug), and the developer **records** the fix to the cloud. **Session 2** is a later, fresh agent that **recalls** that exact rule from the cloud before coding → **green**. The bug the first session fixed does not come back in the second — carried across sessions by the cloud memory alone, over the same MCP `recall`/`record` path any agent uses (and it self-cleans, tombstoning the recorded lesson so the live deck stays pristine). Because the recorded rule *is* the developer's concrete fix (verbatim), it's reliable — not a staged result.

And the core thesis is **grounded live** on the deployment: real code-gen + pytest outcomes are written into the live ledger, so confidence is *earned*, not a prior — and it earns a **varied, honest spread**. Correct lessons earn it from real passes — tenant-scoping **0.92** (8/8), pagination **0.89** (5/5), money **0.86** (3/3), each a validated node with a solid confidence meter — while a wrong money variant (float dollars) took **3/3 real fails → tombstoned** (a grey "forgotten" node). Untested lessons honestly stay at their Beta prior, shown with a **dashed** meter — we never fabricate a number. `/metrics` reports **`grounded_outcomes` 16** and an honest **`calibration_gap` of 0.112** (displayed confidence vs. empirical pass-rate) instead of a misleading 0.0.

The memory also carries **anti-patterns** — dead-end rules a past regression proved wrong — which are injected as active **⛔ DO NOT** inhibitions rather than guidance, so the agent is steered *away* from a known bad path, not just toward a good one. And it can **crystallize** a cluster of related lessons into one higher-level meta-lesson (ExpeL-style synthesis) that then earns its own confidence from real tests like any other.

The memory is also **associative in a brain-*inspired* way** (honest wording — associative memory, not consciousness): lessons recalled together **wire together** via a Hebbian synapse whose weight grows with co-recall (capped), and an opt-in **spreading-activation** recall follows the strongest synapses to surface associated neighbours pure search misses. Crucially, this wiring **never touches a lesson's confidence** — that stays earned from real test outcomes.

**The 3D knowledge globe** makes the whole memory legible (a live, growing globe — ~75 nodes / ~230 edges): every lesson is a node (size = evidence α+β, colour = confidence, grey = forgotten, dark-red = anti-pattern), wired by *related*, *supersedes* (belief revision) and *synthesizes* (crystallization) edges; each edge's strength is initialised from embedding-cosine similarity and then further strengthened by Hebbian co-recall on the synapses that actually co-fire (capped). Click any node and its strands light up by type — you see at a glance what a memory connects to, what replaced it, and what it was distilled into. **A time-travel slider** scrubs the globe through the memory's own history (bi-temporal point-in-time, `/graph?as_of=` + `/timeline`) — drag it back and a since-tombstoned lesson reappears exactly as it stood *valid* then; validity time is kept strictly separate from transaction time.

**The memory also measures, tunes and corrects itself:**
- **Self-evaluation.** Qwen writes *keyword-free* paraphrase questions (so lexical BM25 can't win on word overlap) and we measure **Recall@1 / MRR** with the semantic leg on vs off — turning the vector arm on lifts **Recall@1 0.35 → 0.50** (MRR 0.46 → 0.63) on those paraphrases (gold_sample = 20). The memory grades its own retrieval quality on evidence, not vibes.
- **Self-tuning.** It grid-searches its BM25+vector fusion weights on a **TRAIN split** and **adopts them only if they beat the neutral baseline on a HELD-OUT val split** — a memory that tunes *how* it remembers, with the honesty of a holdout: held-out **Recall@1 0.40 → 0.60** (adopted; committed to `tune_result.json`). *(Honest caveat: n=10 held-out probes — an illustrative lift, not a statistically significant one; the point is the holdout discipline.)*
- **Contradiction detection.** When you teach a new rule, a cheap→expensive check (vector-cosine shortlist → Qwen judge) spots a rule that **contradicts** an existing one and tombstones the loser — the memory never holds two opposite rules.
A live "memory-quality" panel surfaces Recall@1, the semantic lift, a **calibration gap** (displayed confidence vs empirical pass-rate), and grounded-outcome count.

## The proof
An A/B harness runs the same task, same model (`qwen-plus`, temperature 0) against a hidden `pytest` the agent never sees. The task never states our tenant convention, so the knowledge must come from memory. Three honest measurements, not one number:

    Floor    (no memory)                          : 0/5 GREEN   → invents order['user_id'] == user['id']
    Ceiling  (remembered developer fix, verbatim)  : 5/5 GREEN   → scopes  order['tenant_id'] == user['tenant_id']
    Distillation reliability (shipped auto-distiller): 10/10 pass, Wilson95 [72,100]%

> **Honest framing:** the **ceiling** (5/5) is the *capability ceiling* of memory injection — the remembered human fix replayed verbatim — not the shipped default. What we ship is an **auto-distiller** that turns the red test + fix into a lesson; measured separately, **10 of 10 independent distillations** passed the hidden test (Wilson95 [72,100]%). The core contribution is **test-grounded self-correction**: a distillation that drops the concrete comparison **fails the hidden test and is demoted**, so confidence tracks what actually works. The temp-0 in-run trials are a consistency check, not an independent sample — only the distillations are, which is why the Wilson interval lives there. We never claim "guaranteed 100%".

**Generalisation across 3 bug classes** (`harness/generalization.py`) kills the cherry-pick objection. Memory flips the two classes the base model gets **wrong** by default — *tenant isolation* and *pagination leak* — from **0/3 → 3/3** each. On *money rounding* Qwen already writes correct code unaided (floor **3/3**), so memory adds **no** lift and does **no** harm (ceiling 3/3). Two independent 0→100 flips defeat cherry-picking; the third shows the memory is harmless when it isn't needed. The shipped auto-distiller is **18/18** (Wilson95 82–100%) across all three classes.

**A 3-arm honest benchmark** (`./bench.sh`, `docs/benchmark.md`) isolates our *actual* innovation — gating injection on **confidence earned from real tests** — against the obvious baseline, on bug variants the memory never stored verbatim. Same retrieval, same model, same pinned seeds; the arms differ in **one scalar** (the confidence threshold). Over **N=50** (5 classes × {seen,unseen} × 5 seeds, `qwen-plus`), fix-pass@1 with 95% Wilson CIs:

    A · no memory        SEEN 0.60 [0.41,0.77]   UNSEEN 0.60 [0.41,0.77]
    B · naive add-only   SEEN 0.88 [0.70,0.96]   UNSEEN 0.60 [0.41,0.77]
    C · Regress-Guard    SEEN 1.00 [0.87,1.00]   UNSEEN 0.80 [0.61,0.91]   ← earned-gating wins

**Regress-Guard strictly beats both** in both regimes. On *unseen* variants it fixes **5 cases naive add-only misses, breaking none** (McNemar +5/−0). Honestly, that unseen edge concentrates in one class (`email_normalize`) while the others tie — what generalises is the *mechanism*: across all **8** offline bug classes the gate cleanly separates earned from unproven lessons (gate-sweep). It wins because a naive add-only memory lets an unproven/wrong lesson crowd the *earned* one out of the retrieved top-K, and the confidence gate withholds it. This is the honest answer to "of course the stored fix passes": it's not *having* memory that wins, it's memory whose trust is **earned**. Every lesson's confidence is auditable at **`/receipts/{id}`** — the append-only list of the real test outcomes that moved its Beta(α,β).

> **What we do NOT claim (benchmark).** N is small — McNemar p≈0.0625 is the *floor* achievable at this N (directional, not yet p<0.05), and we say so. The gate (0.62) is chosen a-priori just above the 0.50 unproven prior, **not tuned on results**; the suite/split were fixed before the run. The unseen head-to-head edge over naive add-only concentrates in one class (`email_normalize`) — the gating *mechanism* generalises across all 8 offline bug classes, the head-to-head margin does not yet. We also built a **`qwen3-rerank`** cross-encoder stage and **turned it off** — at our memory size RRF already ranks the right lesson (~0.95 MRR), so it adds latency with no measured lift; we report that null rather than feature it.

**New self-proofs — external anchor + the forgetting/confidence machinery (all in `docs/benchmark.md`):**
- **External benchmark — LongMemEval `knowledge-update` (oracle, N=40):** memory lifts QA from a **5 %** no-memory floor to **82.5 %** (Wilson95 [68, 91]) — validating our retrieval + injection leg end-to-end on a recognised benchmark. Honest: oracle split (*not* leaderboard-comparable), and a recency-ablation arm showed a **+0.0** null, reported as such; LongMemEval has no executable outcomes, so it does *not* test our core contribution.
- **Poison-demotion curve** (`harness/poison_curve.py`, offline, no API key): a plausible-but-wrong lesson loses confidence on every real `pytest` failure — below the inject-gate after the **first** fail, tombstoned after 0/6 — and the same holds across **all 8 bug classes** (offline, deterministic; gate-sweep + poison-demotion). The forgetting is a property of the mechanism, not one example.
- **Non-circular calibration/transfer** (`harness/calibration.py`): confidence is grounded on a *seen* task and success measured on an *unseen* variant. It separates high- from low-signal lessons — and **honestly surfaces a real miss** (one high-confidence lesson claimed 0.9 but transferred 0/8). A coarse high/low separation, not a fine calibration curve — we report the limit, not just the win.

## How we built it
- **Qwen Cloud** in five roles across **four Qwen models**: DISTILL (`qwen-plus`, JSON), RECALL (`text-embedding-v4`), REVISE (`qwen-max` judge), SELF-CHECK (`qwen-turbo` paraphrase + `qwen-max` contradiction judge), and FUNCTION-CALLING in chat on flagship **`qwen-max`** (below). The live deployment **routes each role to the model that measured best for it** (`/telemetry` shows it live); the reproducible A/B and 131-test baseline fix a single `qwen-plus`, byte-identical.
- **Qwen function-calling in chat** (`backend/qwen_client.py::chat_with_tools`, `backend/main.py::/chat`, `_RECALL_TOOL`): the chat hands Qwen a `recall_memory` tool and lets the **model itself decide** whether to consult its long-term memory — it calls the tool for coding/engineering questions (writing its own query, e.g. *"safe pagination for list endpoints"*) and skips it for casual ones (verified: *"capital of France?"* → no tool call). We execute the real recall, **sanitize** the lessons (the poisoned-memory defense still applies to tool results), feed them back as the tool result, then Qwen answers — surfaced in the UI as *"🔧 Qwen called recall('…') → answered using N lessons"*. It **fails open** to the direct pre-injection recall path if tool-calling is unavailable.
- **Self-measurement layer** (`evaluation.py`): keyword-free Recall@1/MRR, RRF weight self-tuning (persisted only if it beats baseline), and a calibration snapshot from *real* recorded outcomes.
- **FastAPI + SQLite (WAL)** backend with atomic in-SQL Beta updates and Server-Sent Events for the live UI.
- **Vanilla JS/CSS** frontend (no build): one **living-memory** surface — the editable memory deck (Beta confidence meter) on the left, a normal AI chat in the middle (💬 Chat · 🏆 Proof toggle), and a **persistent 3D force-directed knowledge globe** (self-contained, CDN-free) on the right, always visible.
- **Live-recall bridge**: the globe stays mounted while chat/agent runs; when a response recalls lessons, the backend streams the **real recalled lesson IDs** and the chat pane hands them to the persistent globe via **postMessage**, which pulses exactly those nodes (white flash + particles over their real edges). Only genuine recalled IDs light up — the same IDs shown in the "answered using N lessons: #.." strip — verified end-to-end with Playwright.
- **Live A/B duel** (`GET /duel`, SSE): streams the same prompt to a plain model and to the same model + the recalled lesson, round-by-round, so the green/red counters tick live (**0/5 vs 5/5**). Reliable on camera via a **determinism guard** — a concrete recalled lesson is used verbatim, otherwise its canonical concrete form is injected (temp-0 + a fixed concrete lesson = deterministic), disclosed in the payload as `"injected":"canonical (determinism guard)"`; it has its own rate-limit bucket (4/min) and a per-round retry against Qwen hiccups.
- **Grounding the thesis live** (`harness/ground_demo.py` + `harness/rebuild_demo.py`): runs real code-gen + pytest per bug-class pattern and writes the outcomes into the live ledger, so lessons earn a *varied* confidence spread — tenant **0.92** (8/8), pagination **0.89** (5/5), money **0.86** (3/3) — while a wrong variant is **tombstoned** on real fails and untested lessons stay at their prior. `/metrics` reports `grounded_outcomes` 16 and a real `calibration_gap` 0.112.
- **A-MEM auto-linking + ExpeL crystallization** (`graph.py`, `synthesis.py`): lessons wire themselves into a graph (related / supersedes / synthesizes) and clusters can be distilled into meta-lessons that earn their own confidence.
- **Associative memory** (Hebbian wiring + spreading activation): lessons recalled together strengthen a capped synapse weight, and an opt-in spreading-activation recall walks the strongest synapses to surface neighbours pure retrieval misses — neuroscience-*inspired*, and deliberately kept separate from confidence (which stays test-earned). The globe now shows **~75 lessons and ~230 edges** (a live, growing graph) with variable synapse strength.
- **Anti-pattern inhibitions**: dead-end lessons render as **⛔ DO NOT** directives so the agent avoids a known regression, not just repeats a known fix.
- **MCP tool** (`recall` / `record`) so any agent — Claude Code, Qwen, any coding agent — can use the memory as a drop-in. A recordable **cross-session vignette** (`harness/mcp_vignette.py`) drives that same MCP `recall`/`record` data path end-to-end against the live cloud: Session 1 records a fix, a later fresh Session 2 recalls it and doesn't reintroduce the bug — carried across sessions by the cloud memory alone, with self-cleanup (the recorded lesson is tombstoned).
- **Memory-injection defense** (`memory.py`): recalled lessons enter the prompt as *untrusted data* behind structural markers and a **deterministic sanitizer** that strips embedded instruction/role directives — so a poisoned lesson can't become a command (second-order prompt injection). Validated by our own red-team. **The MCP tool carries the same defense** (`mcp_tool/_safety.py`, unit-tested): recalled lessons are neutralized + untrusted-marked at the point they enter *any* consuming agent (Claude Code, Cursor) — the protection travels with the integration, not just the web chat — and every tool call fails open, so a backend hiccup never crashes the caller.
- **Auditable receipts** (`GET /receipts/{id}`): any lesson's confidence traces back to the append-only list of real pytest outcomes (pass/fail, timestamp, run id) that moved its Beta(α,β) — surfaced on each deck card ("earned from N real tests"). Honesty made clickable and machine-readable for the automated judge.
- **Observability**: per-Qwen-role telemetry (`/telemetry` — call count, p50/p95 latency, token cost for DISTILL/RECALL/REVISE/SELF-CHECK/CHAT) with a correlation id across the chain; enriched `/health` (version, uptime, grounded outcomes, calibration gap).
- **Resilience**: typed retry with exponential backoff + jitter and a **circuit breaker** on the Qwen path; a reproducible disk-cache for the paid benchmark; graceful degradation so a dependency outage never hard-fails an answer.
- **`regress-guard` CLI**: a one-command `doctor` readiness check (deps, hosted cloud reachable, MCP tool), plus `mcp` and `serve`; `pyproject.toml` makes it pip/uvx-installable.
- Deployed on **Alibaba Cloud ECS** (Singapore).

## Challenges we ran into
Making the proof honest: an adversarial self-review caught us over-claiming, so we re-framed the demo to exactly what the model does and made it statistical (pass-rate over K runs) instead of one lucky run.

## Accomplishments that we're proud of
A memory whose confidence is grounded in real test outcomes, that can **demote and tombstone** wrong advice, and that **measures and tunes its own retrieval** and **resolves contradictions on teach** — things the big chat assistants' memory structurally can't do. Proven with a reproducible **floor 0/5 → ceiling 5/5**, a shipped auto-distiller measured at **10/10 (Wilson95 72–100%)**, **generalisation across 3 bug classes** (two independent 0→100 flips plus one class where memory is correctly harmless), and a self-measured retrieval win with a **train/val holdout** — semantic arm lifts Recall@1 **0.35 → 0.50**, and self-tuned weights are adopted only after beating baseline on a **held-out** split (held-out Recall@1 **0.40 → 0.60** on a small n=10 held-out set — illustrative, not statistically significant; committed to `tune_result.json`).

We also **red-teamed our own agent**: because recalled lessons are injected into the system prompt, a poisoned lesson is a real attack surface (memory-poisoning). We hardened it — structural isolation + a deterministic sanitizer + persona rules — flipping our poisoned-memory probe from **vulnerable → safe** and passing a 60-case automated red-team scan clean. The **same defense guards the MCP tool** (`mcp_tool/_safety.py`): we put it through an adversarial `skeptical-validator` gauntlet that found — and we closed — two structural fence-escape variants before it passed. Security we *proved*, not just claimed.

## What we learned
Retrieval plus an LLM isn't enough for a memory you can trust: you also need an **outcome signal** (real test pass/fail) so confidence is *earned*, and a **revision path** (obsolescence detection) so the memory stays correct as the codebase changes. Grounding trust in evidence — not the model's own confidence — was the key insight. Generalising the proof to three bug classes taught us a second discipline: to be honest you have to **show the class where your idea does nothing** (money rounding), not just the ones where it shines. And when we added brain-*inspired* associative wiring (Hebbian synapses, spreading activation), the rule that kept it honest was to keep that wiring **out of the confidence signal** — association helps recall find things; only real tests move trust.

## What's next for Regress-Guard
More bug patterns beyond the current three, editor/CI integrations, and shared per-repo team memories.
---

## Built with (tags)
Qwen, qwen-plus, qwen-max, qwen-turbo, text-embedding-v4, Qwen Cloud, Alibaba Cloud, ECS, Python, FastAPI, SQLite, NumPy, Server-Sent Events, MCP, JavaScript

## Try it out links
- https://github.com/NEO849/qwen-memory-agent   (⚠️ set PUBLIC before final submit)
- http://regressguard.duckdns.org   (live demo — friendly URL, also works behind IP-blocking filters)
- http://47.84.227.215   (same server, direct-IP fallback)

## Media
- Thumbnail / cover: assets/thumbnail.png  (download: http://47.84.227.215/thumbnail.png) → upload to the Devpost image gallery (first image = cover)
- Demo video (< 3 min): (add at the end) → **YouTube / Vimeo / Facebook**, PUBLIC, **English**
  (or English subtitles — required by the Official Rules).
- Alibaba deploy proof: per the binding Official Rules the required proof is the **code-file link** below
  (`backend/qwen_client.py`). A short `deploy/deploy_proof.sh` recording on the ECS box is OPTIONAL/recommended.
- Keep the ECS server running until the Judging Period ends (~Jul 31) — the project must stay testable.

## Additional-info answers (recap)
Individual · Germany · Newly built · start 07-01-26 · Track MemoryAgent · repo URL · code-file URL
(backend/qwen_client.py — demonstrates Qwen Cloud / DashScope API use) · architecture diagram PNG ·
Alibaba deploy PROOF (separate short recording via deploy/deploy_proof.sh) · AI tools text · all 3 checkboxes.
