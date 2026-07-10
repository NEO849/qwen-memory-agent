<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"  srcset="assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
    <img alt="Regress-Guard — memory for AI coding agents that forgets what's wrong" src="assets/banner-dark.svg" width="880">
  </picture>
</p>

<p align="center">
  <b>A memory that stops AI coding agents from re-introducing bugs they already fixed —<br>
  with confidence <i>earned from real test outcomes</i>, not the model's opinion.</b>
</p>

<p align="center">
  <a href="http://regressguard.duckdns.org"><img src="https://img.shields.io/badge/live_demo-online-059669?style=for-the-badge&labelColor=0b0f14" alt="Live demo"></a>
  <img src="https://img.shields.io/badge/tests-120%2F120_green-059669?style=for-the-badge&labelColor=0b0f14" alt="120/120 tests">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-059669?style=for-the-badge&labelColor=0b0f14" alt="MIT license"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Qwen_Cloud-qwen--plus_%C2%B7_text--embedding--v4-F0C35A?style=flat-square&labelColor=0b0f14&logo=alibabacloud&logoColor=white" alt="Powered by Qwen Cloud">
  <img src="https://img.shields.io/badge/Alibaba_Cloud-ECS_%C2%B7_Singapore-FF6A00?style=flat-square&labelColor=0b0f14&logo=alibabacloud&logoColor=white" alt="Deployed on Alibaba Cloud">
  <img src="https://img.shields.io/badge/MCP-drop--in_tool-B9A6E8?style=flat-square&labelColor=0b0f14" alt="MCP drop-in tool">
  <img src="https://img.shields.io/badge/track-MemoryAgent-5AC8F5?style=flat-square&labelColor=0b0f14" alt="Track: MemoryAgent">
</p>

<p align="center">
  <b>
  <a href="http://regressguard.duckdns.org">▶&nbsp;Live&nbsp;demo</a> &nbsp;·&nbsp;
  <a href="#powered-by-qwen-cloud-on-alibaba-cloud">Qwen&nbsp;usage</a> &nbsp;·&nbsp;
  <a href="#architecture">Architecture</a> &nbsp;·&nbsp;
  <a href="#quickstart">Quickstart</a> &nbsp;·&nbsp;
  <a href="#use-as-an-mcp-tool">MCP&nbsp;tool</a> &nbsp;·&nbsp;
  <a href="docs/benchmark.md">Benchmark</a> &nbsp;·&nbsp;
  <a href="docs/JUDGING.md">Rubric&nbsp;map</a>
  </b>
</p>

<p align="center">
  <img src="docs/media/proof-globe.png" width="900" alt="The proof: same AI, same task, temperature 0 — 0/5 without memory vs 5/5 with Regress-Guard, beside the live 3D knowledge globe">
</p>

---

> **Powered by Qwen Cloud — five roles across four Qwen models:** flagship **`qwen-max`** for chat & the high-stakes judges · `qwen-turbo` for cheap paraphrase · `qwen-plus` for structured distillation · `text-embedding-v4` for recall — each role routed to the model that measured best for it (three Qwen Cloud APIs), deployed on **Alibaba Cloud**. Deploy proof (code): [`backend/qwen_client.py`](backend/qwen_client.py). [Full role table ↓](#powered-by-qwen-cloud-on-alibaba-cloud)

## Install

**Try it with zero install** — open the live demo: **[regressguard.duckdns.org](http://regressguard.duckdns.org)**, or hit `GET /health` and `GET /receipts/{id}` to audit it yourself.

**Use it in your own agent** — one command to verify, then wire it into any MCP client:

```bash
git clone https://github.com/NEO849/qwen-memory-agent && cd qwen-memory-agent
pip install -e . && regress-guard doctor      # ✅ deps · hosted cloud reachable · MCP tool
```

```jsonc
// .mcp.json — talks to our hosted Alibaba Cloud backend, so no API key or database of your own
{ "mcpServers": { "regress-guard": {
    "command": "regress-guard", "args": ["mcp"],
    "env": { "REGRESS_GUARD_URL": "http://regressguard.duckdns.org" } } } }
```

Works with **any MCP-speaking agent** — Claude Code, Cursor, Qwen Code. Two tools: `recall`
(lessons to follow before writing code) and `record` (learn from a fixed test).

## The problem

AI coding agents are **stateless across sessions**: you fix a bug today, and a fresh session tomorrow
happily reintroduces it. Existing "memory" features remember *facts you tell them* — they can't tell
whether a remembered rule actually **works**. Regress-Guard is a memory whose trust is **earned by real
evidence**, and that **forgets advice a refactor made wrong**.

---

## The proof — same AI twice, the only difference is memory

<p align="center"><img src="docs/media/proof.png" alt="A/B proof: floor 0/5 without memory, ceiling 5/5 with the remembered fix, shipped auto-distiller 10/10" width="920"></p>

`harness/ab_runner.py` runs the **same** coding task, **same** model (`qwen-plus`, temperature 0),
against a **hidden** `pytest` the agent never sees. The task never states our tenant convention, so
the knowledge *must* come from memory. Three honest measurements, not one number:

```text
  A/B RESULT — get_orders tenant isolation   (model=qwen-plus, temp=0)
  Floor    (no memory)                       : 0/5 GREEN  →  invents order['user_id'] == user['id']   ✗
  Ceiling  (remembered developer fix, verbatim): 5/5 GREEN  →  scopes  order['tenant_id'] == user['tenant_id']  ✓
  Distillation reliability (shipped auto-distiller): 10/10 pass, Wilson95 [72,100]%
```

> **Honest framing** (survived an adversarial self-review): the **ceiling** (5/5) is the *capability
> ceiling* of memory injection — the remembered human fix replayed verbatim — **not** the shipped
> default. What we actually ship is an **auto-distiller** that turns the red test + fix into a lesson;
> measured separately, **10 of 10 independent distillations** produced a lesson that passed the hidden
> test (Wilson95 **[72,100]%**). The core contribution is **test-grounded self-correction**: a
> distillation that drops the concrete comparison **fails the hidden test and gets demoted**, so
> confidence tracks what actually works. The temp-0 in-run trials are a *consistency* check, not an
> independent sample — the independent unit is the distillation (one draw per run), which is why the
> Wilson interval lives there. We never claim "guaranteed 100%".
>
> **Generalisation across 3 bug classes** (`harness/generalization.py`): memory flips the two classes
> the base model gets **wrong** by default — *tenant isolation* and *pagination leak* — from **0/3 →
> 3/3** each. On *money rounding* Qwen already writes correct code unaided (floor **3/3**), so memory
> adds **no** lift and does **no** harm (ceiling 3/3). Two independent 0→100 flips kill the
> cherry-pick objection; the third shows the memory is harmless when it isn't needed. Auto-distiller
> **18/18** (Wilson95 82–100%) across all three. Reproduce it yourself:

```bash
python -m harness.ab_runner --k 5 --distill-samples 10 --verbose   # floor / ceiling / distillation
python -m harness.generalization --k 3 --distill-samples 6         # all 3 bug classes
```

---

## Does the memory actually *help*? — a 3-arm honest benchmark

The floor→ceiling proof shows memory *can* help, but a skeptic reads it as tautological. So we
isolate our real innovation — **gating injection on confidence earned from real tests** — against
the obvious baseline, on bug variants the memory never stored verbatim. Same retrieval, same
model, same pinned seeds; the arms differ in **one scalar** (the confidence threshold).
Reproduce: **`./bench.sh`** (details + honesty notes: [`docs/benchmark.md`](docs/benchmark.md)).

```text
fix-pass@1 (95% Wilson CI) — N=50 (5 classes × {seen,unseen} × 5 seeds), qwen-plus
                         SEEN                 UNSEEN
  A · no memory          0.60 [0.41,0.77]     0.60 [0.41,0.77]
  B · naive add-only     0.88 [0.70,0.96]     0.60 [0.41,0.77]
  C · Regress-Guard      1.00 [0.87,1.00]     0.80 [0.61,0.91]   ← earned-gating wins
```

**Regress-Guard strictly beats both.** On unseen variants it fixes **5 cases naive add-only
misses, breaking none** (McNemar +5/−0) — a naive memory lets an *unproven/wrong* lesson crowd
the earned one out of the retrieved set; the gate withholds it. Every card's confidence is
auditable at **`/receipts/{id}`** — the append-only test outcomes that earned it.

**Two more self-proofs** (offline, no API key — [`docs/benchmark.md`](docs/benchmark.md)): a
**poison-demotion curve** watches a plausible-but-wrong lesson lose confidence on every real pytest
failure — below the inject-gate after the *first* fail, tombstoned after 0/6 — and the same holds
across **all 5 bug classes**, not just money. And a small **non-circular transfer test** (confidence
grounded on a seen task, success measured on an *unseen* variant) shows the confidence separates
signal from noise — while honestly surfacing one case where it did **not** (a lesson claimed 0.9 but
transferred 0/8). We report the limit, not only the win.

And on an **external, recognised benchmark** — not a self-built one — our memory lifts
**LongMemEval `knowledge-update` QA from 5 % (no memory) to ~82 %** (33/40, Wilson95 [68, 91];
`harness/longmemeval_eval.py`). Honest scope: oracle split (not leaderboard-comparable), and a
recency-ablation arm showed **no** lift (+0.0 pts) — reported as a null, not dressed up ([`docs/benchmark.md`](docs/benchmark.md)).

One more headline number, reproducible **offline with no API key**:
**value-density packing injects the critical lesson in ~37 % fewer tokens at identical recall**, and
tombstoning a wrong lesson cuts harmful-injection **100 % → 0 %** (`harness/context_window_bench.py`).
*(A vectorized-cosine constant-factor speedup is documented in the benchmark too — engineering hygiene, not headlined as innovation.)*

> **What we do NOT claim.** N is small (McNemar p≈0.0625 — directional, not yet p<0.05); we say
> so. `qwen3-rerank` is built but **off** — it shows no lift at our memory size, and we report
> that null rather than feature it. The 5/5 is the injection *ceiling*, not a guaranteed default.
> Full rubric mapping + limits: [`docs/JUDGING.md`](docs/JUDGING.md).

---

## How it compares — where we're different, honestly

Agent-memory in 2026 is a crowded field (Mem0, Zep/Graphiti, Letta/MemGPT). Almost all of them
ground *what to trust* in **recency** ("most recent wins") or an **LLM's own judgement** — and the
field openly distrusts the latter. Regress-Guard grounds it in **verifiable execution outcomes**
(real `pytest` pass/fail → a Beta posterior). That is the one row where only we are green — and we're
honest about the rows where the incumbents beat us.

| | **Regress-Guard** | Mem0 | Zep/Graphiti | Letta/MemGPT |
|---|---|---|---|---|
| Trust grounded in | **execution outcome (real tests)** | recency / salience | recency + graph | recency / self-edit |
| Forgets what's *wrong* (not just old) | **yes — demote/tombstone on a real fail** | TTL / eviction | invalidate by recency | self-edit |
| Token-budget-aware recall | yes (value-density) | yes | yes | via context mgmt |
| Temporal invalidation | **supersede/tombstone + bi-temporal point-in-time** | partial | **bitemporal graph** | partial |
| Standard-benchmark breadth | LongMemEval subset (honest) | **LoCoMo + LongMemEval (full)** | **LongMemEval (full)** | DMR |
| Scale | single-process (honest cap) | managed | **graph, scalable** | managed |
| Agent integration | MCP (drop-in, any agent) | SDK / API | SDK | framework |

The incumbents win on **benchmark breadth** and **scale** — we say so. But none of them earns a
memory's confidence from *ground-truth execution*, and the field's own leaders admit **no public
benchmark yet scores outcome-grounded forgetting, memory writes, or token-budgeted recall**
([Mem0, *State of AI Agent Memory 2026*](https://mem0.ai/blog/ai-memory-benchmarks-in-2026)) — the
exact gap our thesis fills.

## Verify it in 60 seconds

No install — hit the live deployment:

```bash
# 1) the captured causal proof (0/5 → 5/5)
curl -s http://regressguard.duckdns.org/ab | python -m json.tool

# 2) the memory as a graph (nodes = lessons, edges = related / supersedes / synthesizes)
curl -s http://regressguard.duckdns.org/graph | python -m json.tool | head -40

# 3) ask the agent — the answer is steered by recalled, outcome-grounded lessons
curl -s http://regressguard.duckdns.org/chat -H 'content-type: application/json' \
     -d '{"message":"How should I list orders for a user?"}'

# 4) the memory's own honesty panel — confidence earned from REAL test outcomes
curl -s http://regressguard.duckdns.org/metrics | python -m json.tool   # grounded_outcomes, calibration_gap
```

The live instance ships **earned confidence**: correct lessons earn it from real pytest passes — tenant-scoping **0.92** (8/8), pagination **0.89** (5/5), money **0.86** (3/3), each a validated node with a solid meter — while a refuted money variant (float dollars) was **live-tombstoned** on **3/3 real fails** (a grey "forgotten" node). Untested lessons keep a **dashed** prior meter (never fabricated). So `/metrics` reports **`grounded_outcomes` 16** and an honest **`calibration_gap` 0.112** — displayed confidence vs. empirical pass-rate from real outcomes.

Or just open **[regressguard.duckdns.org](http://regressguard.duckdns.org)** → the **🏆 Proof** or **⚔️ Duel** tab.

---

## What you can see and steer

One clinical surface — a **living-memory** layout: the **editable memory on the left**, a normal AI chat in the **middle** (toggle **💬 Chat · 🏆 Proof · ⚔️ Duel**), and the **persistent 3D knowledge globe on the right, always visible**. When chat or the agent recalls lessons, exactly those nodes pulse **live** on the globe while the answer streams — memory *and* its use on one screen:

<p align="center"><img src="docs/media/living-memory.png" alt="Living memory — editable memory deck (left), chat (middle), persistent 3D globe (right); recalled lessons pulse live on the globe" width="920"></p>

| | Feature | What it means |
|---|---|---|
| 🧠 | **Living memory (globe + chat together)** | Three columns in one frame: **LEFT** the editable card deck (**pin / demote / forget / revise**, **Teach** a rule, add a **⛔ don't**, **Run / Pause / Stop** the agent), **MIDDLE** the chat, **RIGHT** the always-on 3D globe. When chat or the agent recalls a lesson, exactly those nodes pulse **live** on the globe while the answer streams — only the **real recalled IDs** light up (verified via Playwright). Mobile stacks. |
| ⚔️ | **Live duel (plain AI vs. AI + Regress-Guard)** | One prompt, two arms — **"plain AI · no memory"** vs **"AI + Regress-Guard"**. Hit **▶ Run 5 live** and 5 hidden `pytest` fire in real time; the counters tick to **0/5 vs 5/5**. The *live, un-recorded* twin of 🏆 Proof — the memory arm uses a **disclosed determinism guard** (`"injected":"canonical"`), so it is the injection *ceiling*, never "guaranteed". |
| 💬 | **Chat + editable memory** | Talk to the agent; beside it, a flashcard deck shows every lesson with a **Beta(α,β) confidence meter** — **pin**, **demote** or **forget** any lesson in a click. |
| 🕐 | **Bi-temporal time-travel** | A slider under the globe scrubs the whole knowledge base through **its own history** — drag it back and lessons that were later tombstoned reappear as they stood *valid then*. Point-in-time recall (`/graph?as_of=…`, `/timeline`), validity time kept strictly separate from transaction time. Honest: bi-temporal supersession, not a full Graphiti graph. |
| 🌐 | **3D knowledge globe** | The whole memory as a rotating globe (**74 nodes and ~230 edges**): node size = evidence (α+β), colour = confidence, grey = forgotten, dark-red = anti-pattern; **edge strength is initialised from embedding-cosine similarity**, then further strengthened by Hebbian co-recall on the synapses that co-fire (capped). **Click a node and its strands light up by type** — *related* (blue), *supersedes* (red), *synthesizes* (violet) — so you see at a glance what a memory connects to. |
| 🏆 | **The proof** | The signature A/B moment above, replayable on demand — the decisive token pulses, the pass-rate lift counts up. |
| ⛔ | **Anti-pattern inhibitions** | Dead-end rules a past regression proved wrong are injected as active **⛔ DO NOT** directives — the agent is steered *away* from a known bad path, not just toward a good one. |
| ✦ | **Crystallization (ExpeL)** | A cluster of related lessons can be distilled into one higher-level meta-lesson that then **earns its own confidence** from real tests like any other. |
| 🧠 | **Associative memory (Hebbian + spreading activation)** | Neuroscience-*inspired*, not mystical: lessons recalled together **wire together** — the edge weight grows with co-recall (capped), never touching confidence (that stays test-earned). An opt-in **spreading-activation** recall then follows the strongest synapses to surface associated neighbours that pure search misses. |
| 🛡 | **Poison defense** | Recalled lessons enter the prompt as *untrusted data* behind structural markers + a deterministic sanitizer — a poisoned lesson can't become a command. |

<p align="center"><img src="docs/media/globe.png" alt="3D knowledge globe — clicking a node lights up its strands by type" width="820"></p>

---

## Powered by Qwen Cloud on Alibaba Cloud

Five distinct Qwen roles across **four Qwen models** (`qwen-max` · `qwen-plus` · `qwen-turbo` · `text-embedding-v4`) and three Qwen Cloud APIs. The **live deployment routes each role to the model that measured best for it** (`RG_MODEL_ROUTING` on, `QWEN_MODEL=qwen-max`); the flag-off reproducible baseline — the 120 tests and the A/B — collapses every role to a single `qwen-plus`, byte-identical. **Alibaba Cloud deploy proof (code):** the DashScope / Qwen Cloud client [`backend/qwen_client.py`](backend/qwen_client.py) · deployment notes [`deploy/README.md`](deploy/README.md).

| # | Role | Model | Where |
|---|------|-------|-------|
| 1 | **DISTILL** — red test + fix diff → lesson JSON | `qwen-plus` (JSON mode) | `backend/extractor.py` |
| 2 | **RECALL** — embed lessons + context, fuse with BM25 (RRF) | `text-embedding-v4` (1024-d) | `backend/retrieval.py`, `memory.py` |
| 3 | **REVISE** — is a lesson now obsolete? → tombstone | `qwen-max` (obsolescence/contradiction judge) | `backend/reviser.py` |
| 4 | **SELF-CHECK** — keyword-free paraphrase eval + contradiction judge | `qwen-turbo` paraphrase · `qwen-max` judge | `backend/evaluation.py`, `reviser.py` |
| 5 | **FUNCTION-CALLING** — chat gives Qwen a `recall_memory` tool; the model decides on its own to call it for coding questions and writes the query itself | flagship **`qwen-max`** (tool-calling) | `backend/qwen_client.py::chat_with_tools`, `backend/main.py::/chat` |

*Even the coding agent in the proof harness is Qwen — Qwen both **causes** and **cures** the bug via memory. The Model column is the **live per-role routing**; with `RG_MODEL_ROUTING` off every role collapses to `qwen-plus` for a byte-identical baseline. `/telemetry` shows the live model serving each role (chat = `qwen-max`).*

In chat, we don't decide when to consult the memory — **Qwen does**. It's handed a `recall_memory` tool and *autonomously* calls it for coding/engineering questions (formulating its own query, e.g. *"password storage best practices"*), while skipping it for casual ones (*"What is the capital of France?"* → no tool call). We run the real recall, **sanitize** the lessons (the poisoned-memory defense stays intact) and feed them back as the tool result before Qwen answers — shown in the UI as *"🔧 Qwen called recall('…') → answered using N lessons"*. It fails open to the direct pre-injection path if tool-calling is unavailable.

**Depth beyond a single model** *(active in the live deployment; each stays flag-gated so the reproducible baseline and 120 tests are byte-identical when off)*:

- **Right model for the job** (`RG_MODEL_ROUTING`, on in the live deployment) — chat and the high-stakes obsolescence/contradiction **judges run on flagship `qwen-max`**, the cheap eval paraphrase on `qwen-turbo`, and structured DISTILL stays on `qwen-plus`, which measured most reliable for schema extraction — each role on the model that measured best for it. `/telemetry` shows the model serving each role.
- **Strict structured output** (`RG_STRUCTURED_OUTPUT`) — DISTILL enforces a `json_schema` (four keys + `severity` enum) model-side, with a graceful fallback to `json_object` if a provider rejects it — schema-enforced, never brittle.
- **Reasoning traces** (`RG_REASONING_ENABLED`) — captures Qwen3 *thinking* on DISTILL/REVISE and surfaces it at `/reasoning` (why a lesson was distilled or retired). Pure observability — it **never** moves a lesson's Beta confidence, which stays earned from real tests.

---

## The memory measures, tunes and corrects itself

Beyond learn → recall → grade, Regress-Guard improves its *own* retrieval and consistency:

- **Self-evaluation** — Qwen writes *keyword-free* paraphrase queries so BM25 can't win on word overlap; it measures **Recall@1 / MRR** with the vector leg on vs off. Turning the semantic (vector) arm on lifts **Recall@1 0.35 → 0.50** (MRR 0.46 → 0.63) on those paraphrases (gold_sample = 20). Retrieval quality graded on evidence, not vibes.
- **Self-tuning** — grid-searches the BM25 + vector fusion weights on a **TRAIN split** and **adopts them only if they beat the neutral baseline on a HELD-OUT val split** — held-out **Recall@1 0.40 → 0.60** (adopted; *n=10 held-out probes — illustrative, not statistically significant; the point is the holdout discipline*). The result is committed to [`tune_result.json`](tune_result.json), like [`ab_result.json`](ab_result.json).
- **Contradiction detection** — a new lesson is checked (vector-cosine shortlist → Qwen judge) against active ones; a genuine contradiction tombstones the loser, so the memory never holds two opposite rules.
- **Calibration** — a live panel shows Recall@1, the semantic lift, grounded-outcome count, and the **calibration gap** (displayed confidence vs empirical pass-rate, from *real* outcomes).
- **Associative recall** — lessons recalled together strengthen a Hebbian synapse (weight grows with co-recall, capped); an opt-in spreading-activation pass then walks the strongest synapses to surface associated neighbours pure search misses. This is *associative memory* (Hebbian wiring / spreading activation) — neuroscience-inspired, and it **never** touches a lesson's confidence, which stays earned from real test outcomes.

Every real **pytest pass/fail** updates a lesson's confidence as the posterior mean of a Beta distribution:

```math
\text{confidence} = \mathbb{E}[\text{Beta}(\alpha,\beta)] = \frac{\alpha}{\alpha+\beta}, \qquad \text{pass} \Rightarrow \alpha{+}1, \quad \text{fail} \Rightarrow \beta{+}1
```

---

## Architecture

<p align="center"><img src="architecture/diagram.png" alt="Architecture" width="880"></p>

Outcome-grounded confidence lives in a SQLite ledger (WAL, atomic in-SQL Beta updates); the browser is
fed live over Server-Sent Events; an MCP tool exposes the memory to any agent. Details:
[`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md).

---

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set DASHSCOPE_API_KEY + QWEN_BASE_URL (Qwen Cloud workspace host)

python -m backend.qwen_client          # connectivity test against Qwen
python -m harness.ab_runner --k 5 -v   # reproduce the A/B proof
uvicorn backend.main:app --workers 1   # then open http://localhost:8000
```

> **`--workers 1` is required** — the live-update fan-out (SSE) is in-process.
> Tests: `pytest` (offline, 120/120) · `pytest -m live` (hits Qwen).
> Reproduce the two efficiency numbers offline (no API key): `python -m harness.context_window_bench` · `python -m harness.latency_bench`.

---

## Use as an MCP tool

`mcp_tool/server.py` exposes `recall(context)` and `record(test_output, diff)` over MCP. By default it
talks to the **deployed memory on Alibaba Cloud over HTTP** — so any coding agent (Claude Code, Qwen
Code, Cursor) gains a shared, outcome-grounded memory with **zero local setup** (no ledger, no API key;
the cloud does the distilling + retrieval). An agent calls `recall` before writing code and `record`
after fixing a red test, so the same bug can't come back in a later session.

**See it carry a fix across two sessions** — a recordable terminal proof against the *live* cloud memory:

```bash
python -m harness.mcp_vignette
```

**Session 1** (a fresh agent, empty memory) writes `get_orders` → the hidden test goes **RED** (it invents
a `user_id` filter — a cross-tenant bug); the developer **records** the fix to the cloud memory. **Session 2**
(a later, fresh agent) **recalls** that exact rule from the cloud → **GREEN**. The bug didn't come back —
carried across sessions by the cloud memory alone, over the same `recall`/`record` data path as
`mcp_tool/server.py`. It self-cleans (the recorded lesson is tombstoned so the live deck stays pristine).

**30-second setup + verified transcript:** [`mcp_tool/README.md`](mcp_tool/README.md) · config: [`.mcp.json`](.mcp.json)
(`REGRESS_GUARD_LOCAL=1` switches to a fully local ledger + your own Qwen key.)

> Both the **🏆 Proof** and **⚔️ Duel** views now carry a visible *"ceiling ≠ default"* caption: **5/5 is the
> capability ceiling** — the remembered fix injected verbatim, not a guaranteed default — while the shipped
> auto-distiller is measured separately (**10/10, 95% CI 72–100%**). The honesty is now on screen, not just in the JSON.

---

## Deployment

Runs as a single process on **Alibaba Cloud ECS** (Singapore) — see [`deploy/README.md`](deploy/README.md).
Live: **[regressguard.duckdns.org](http://regressguard.duckdns.org)** (friendly URL, also works behind IP-blocking filters).

## Attribution & license

MIT (see [`LICENSE`](LICENSE)). The retrieval fusion (BM25 + Reciprocal Rank Fusion) is adapted from the
author's own MIT-licensed **markmem** engine; everything else — the ledger, the outcome-grounded Beta
confidence, the A/B harness, the Qwen wiring, the UI, the 3D globe, and the controllable agent loop — is
new for this hackathon.
