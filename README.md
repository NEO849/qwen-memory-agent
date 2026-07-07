<p align="center">
  <img src="assets/banner.png" alt="Regress-Guard — a memory that forgets what's wrong" width="960">
</p>

<h1 align="center">Regress-Guard</h1>

<p align="center">
  <b>A memory that stops AI coding agents from re-introducing bugs they already fixed —<br>
  with confidence <i>earned from real test outcomes</i>, not the model's opinion.</b>
</p>

<p align="center">
  <a href="http://regressguard.duckdns.org"><img src="https://img.shields.io/badge/live_demo-online-5FD787?style=for-the-badge&labelColor=0c1119" alt="Live demo"></a>
  <img src="https://img.shields.io/badge/A%2FB_proof-floor→ceiling_×_3_bug_classes-5FD787?style=for-the-badge&labelColor=0c1119" alt="A/B proof floor to ceiling across 3 bug classes">
  <img src="https://img.shields.io/badge/tests-54%2F54_green-5FD787?style=for-the-badge&labelColor=0c1119" alt="54/54 tests">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Qwen_Hackathon-MemoryAgent-5AC8F5?style=flat-square&labelColor=0c1119" alt="Track: MemoryAgent">
  <img src="https://img.shields.io/badge/Qwen_Cloud-qwen--plus_·_embedding--v4-F0C35A?style=flat-square&labelColor=0c1119&logo=alibabacloud&logoColor=white" alt="Qwen Cloud">
  <img src="https://img.shields.io/badge/Alibaba_Cloud-ECS_Singapore-FF6A00?style=flat-square&labelColor=0c1119&logo=alibabacloud&logoColor=white" alt="Alibaba Cloud ECS">
  <img src="https://img.shields.io/badge/FastAPI_·_SQLite_·_SSE-009688?style=flat-square&labelColor=0c1119&logo=fastapi&logoColor=white" alt="FastAPI · SQLite · SSE">
  <img src="https://img.shields.io/badge/MCP-drop--in_tool-B9A6E8?style=flat-square&labelColor=0c1119" alt="MCP tool">
  <img src="https://img.shields.io/badge/UI-no_build_step-8A93A0?style=flat-square&labelColor=0c1119" alt="No build">
  <img src="https://img.shields.io/badge/License-MIT-5FD787?style=flat-square&labelColor=0c1119" alt="MIT">
</p>

---

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

The live instance ships **grounded outcomes**: a correct money lesson (integer cents) earned **confidence 0.86** from **3/3 real pytest passes** (a validated node), while a refuted one (float dollars) was **live-tombstoned** on **3/3 real fails** — a grey "forgotten" node. So `/metrics` now reports `grounded_outcomes > 0` and an honest **`calibration_gap` (0.143)** — displayed confidence vs. empirical pass-rate from real outcomes, not a prior.

Or just open **[regressguard.duckdns.org](http://regressguard.duckdns.org)** → the **🏆 Proof** or **⚔️ Duel** tab.

---

## What you can see and steer

One clinical surface — a **living-memory** layout: the **editable memory on the left**, a normal AI chat in the **middle** (toggle **💬 Chat · 🏆 Proof**), and the **persistent 3D knowledge globe on the right, always visible**. When chat or the agent recalls lessons, exactly those nodes pulse **live** on the globe while the answer streams — memory *and* its use on one screen:

<p align="center"><img src="docs/media/living-memory.png" alt="Living memory — editable memory deck (left), chat (middle), persistent 3D globe (right); recalled lessons pulse live on the globe" width="920"></p>

| | Feature | What it means |
|---|---|---|
| 🧠 | **Living memory (globe + chat together, live recall highlight)** | Three columns in one frame: **LEFT** the editable memory (card deck — **pin / demote / forget / revise**, **Teach** a rule, add a **⛔ don't**, and **Run / Pause / Stop** the agent), **MIDDLE** a normal AI chat with a **[💬 Chat · 🏆 Proof]** toggle, **RIGHT** the **persistent 3D globe (always visible)**. **Live-recall highlight:** when chat or the agent recalls lessons, exactly those nodes pulse live on the globe (white flash + particles over their real edges) while the answer streams. Only the **real recalled lesson IDs** pulse — the same IDs as the "answered using N lessons: #.." strip (verified via Playwright). Mobile degrades to a stack. |
| ⚔️ | **Live duel (plain AI vs. AI + Regress-Guard)** | A third middle tab beside **💬 Chat · 🏆 Proof**: one prompt → two AIs side by side, **"plain AI · no memory"** vs. **"AI + Regress-Guard"**. Hit **▶ Run 5 live** and 5 hidden `pytest` run in real time — a green/red counter ticks over each arm and the winner pane glows: **0/5 vs 5/5**, verified live. It is the *live, un-recorded* twin of the 🏆 Proof tab (which stays the instant, flicker-safe replay of the **same** experiment). Honest by design: the memory arm injects the remembered concrete lesson through a **determinism guard** (the same one `harness/ab_runner` uses), disclosed in the SSE stream as `"injected":"canonical (determinism guard)"`; the plain arm structurally mis-scopes and fails. It is deliberately the injection *ceiling* live — not a live distillation (that lives separately in [`ab_result.json`](ab_result.json): auto-distiller 10/10, Wilson95 [72,100]%). Never framed as "guaranteed". |
| 💬 | **Chat + editable memory** | Talk to the agent; beside it, a flashcard deck shows every lesson with a **Beta(α,β) confidence meter** — **pin**, **demote** or **forget** any lesson in a click. |
| 🌐 | **3D knowledge globe** | The whole memory as a rotating globe (currently **66 nodes / 196 edges**): node size = evidence (α+β), colour = confidence, grey = forgotten, dark-red = anti-pattern; **edge strength is initialised from embedding-cosine similarity**, then further strengthened by Hebbian co-recall on the synapses that co-fire (capped). **Click a node and its strands light up by type** — *related* (blue), *supersedes* (red), *synthesizes* (violet) — so you see at a glance what a memory connects to. |
| 🏆 | **The proof** | The signature A/B moment above, replayable on demand — the decisive token pulses, the pass-rate lift counts up. |
| ⛔ | **Anti-pattern inhibitions** | Dead-end rules a past regression proved wrong are injected as active **⛔ DO NOT** directives — the agent is steered *away* from a known bad path, not just toward a good one. |
| ✦ | **Crystallization (ExpeL)** | A cluster of related lessons can be distilled into one higher-level meta-lesson that then **earns its own confidence** from real tests like any other. |
| 🧠 | **Associative memory (Hebbian + spreading activation)** | Neuroscience-*inspired*, not mystical: lessons recalled together **wire together** — the edge weight grows with co-recall (capped), never touching confidence (that stays test-earned). An opt-in **spreading-activation** recall then follows the strongest synapses to surface associated neighbours that pure search misses. |
| 🛡 | **Poison defense** | Recalled lessons enter the prompt as *untrusted data* behind structural markers + a deterministic sanitizer — a poisoned lesson can't become a command. |

<p align="center"><img src="docs/media/globe.png" alt="3D knowledge globe — clicking a node lights up its strands by type" width="820"></p>

---

## Qwen's five roles

| # | Role | Model | Where |
|---|------|-------|-------|
| 1 | **DISTILL** — red test + fix diff → lesson JSON | `qwen-plus` (JSON mode) | `backend/extractor.py` |
| 2 | **RECALL** — embed lessons + context, fuse with BM25 (RRF) | `text-embedding-v4` (1024-d) | `backend/retrieval.py`, `memory.py` |
| 3 | **REVISE** — is a lesson now obsolete? → tombstone | `qwen-plus` | `backend/reviser.py` |
| 4 | **SELF-CHECK** — keyword-free paraphrase eval + contradiction judge | `qwen-plus` | `backend/evaluation.py`, `reviser.py` |
| 5 | **FUNCTION-CALLING** — chat gives Qwen a `recall_memory` tool; the model decides on its own to call it for coding questions and writes the query itself | `qwen-plus` (tool-calling) | `backend/qwen_client.py::chat_with_tools`, `backend/main.py::/chat` |

*Even the coding agent in the proof harness is Qwen — Qwen both **causes** and **cures** the bug via memory.*

In chat, we don't decide when to consult the memory — **Qwen does**. It's handed a `recall_memory` tool and *autonomously* calls it for coding/engineering questions (formulating its own query, e.g. *"password storage best practices"*), while skipping it for casual ones (*"What is the capital of France?"* → no tool call). We run the real recall, **sanitize** the lessons (the poisoned-memory defense stays intact) and feed them back as the tool result before Qwen answers — shown in the UI as *"🔧 Qwen called recall('…') → answered using N lessons"*. It fails open to the direct pre-injection path if tool-calling is unavailable.

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
> Tests: `pytest` (offline, 54/54) · `pytest -m live` (hits Qwen).

---

## MCP integration — a real tool, not just a demo

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
