# How Regress-Guard maps to the judging rubric

One page, mapped to the four criteria in their exact wording, with the evidence and the file
that proves each claim. Numbers are reproducible; nothing here is asserted without a link.

**TL;DR (the one line, repeated everywhere):** *A memory that stops AI coding agents from
re-introducing bugs they already fixed — confidence earned from real test outcomes, not the
model's opinion.* Live: [regressguard.duckdns.org](http://regressguard.duckdns.org) · MIT ·
deployed on Alibaba Cloud ECS · track **MemoryAgent**.

---

## 1 · Technical Depth & Engineering (30%)
*"Sophisticated use of QwenCloud APIs (custom skills, MCP integrations)? Algorithmic or
engineering innovation through novel solutions, custom components, or performance optimization?"*

- **Sophisticated QwenCloud API usage — five roles across three APIs:** DISTILL, REVISE,
  SELF-CHECK (`qwen-plus`, JSON mode), RECALL (`text-embedding-v4` + BM25/RRF hybrid), and
  **FUNCTION-CALLING** — the model itself decides, via a `recall_memory` tool it invokes and
  writes the query for, when to consult memory (`backend/main.py::_chat_prepare`,
  `qwen_client.py::chat_with_tools`). A **bounded multi-step tool loop** (recall → traverse the
  associative graph via `get_related_lessons` → answer) and **token streaming** are built and
  flag-gated (`TOOL_LOOP_ENABLED`, `STREAMING_ENABLED`).
- **Beyond a single model (flag-gated, byte-identical when off):** **per-role model routing**
  (`RG_MODEL_ROUTING`) sends the high-stakes obsolescence/contradiction *judges* to `qwen-max`,
  cheap eval paraphrase to `qwen-turbo`, DISTILL/default to `qwen-plus` — the right model for the
  job, visible per role at `/telemetry`; **strict `json_schema`** for DISTILL with graceful
  `json_object` fallback (`RG_STRUCTURED_OUTPUT`); **Qwen3 reasoning-trace capture** on
  DISTILL/REVISE surfaced at `/reasoning` (`RG_REASONING_ENABLED`) — observability that never
  touches earned confidence.
- **MCP integration:** a drop-in `recall` / `record` MCP tool (`mcp_tool/server.py`) any agent
  wires in; talks to the hosted Alibaba Cloud backend (no key/DB of your own).
- **Algorithmic innovation (novel, and *measured*):** confidence is the **posterior mean of a
  Beta(α,β)** that moves only on real pytest pass/fail; wrong lessons are demoted/tombstoned.
  Our **3-arm benchmark** (`docs/benchmark.md`, `./bench.sh`) shows earned-confidence gating
  **beats naive add-only memory** on unseen bug variants — the honest proof the mechanism, not
  just "having memory", is what helps.
- **Engineering/perf:** typed retry+backoff+jitter and a **circuit breaker** on the Qwen path;
  a disk-cache that makes the paid benchmark reproducible; atomic in-SQL Beta updates.

## 2 · Innovation & AI Creativity (30%)
*"High-quality architecture with strong modularity, scalability, error handling? Clean code and
non-trivial logic? Tech stack sophistication via advanced patterns and thoughtful adoption?"*

- **Modularity:** clear layers — `ledger` (storage + Beta) · `retrieval` (BM25/vector/RRF) ·
  `memory` (recall/inject/sanitize) · `confidence` (the injection gate) · `evaluation`
  (self-eval/tune) · `qwen_client` (resilient API) · `main` (API/SSE). See
  [`architecture/`](../architecture) and the diagram.
- **Error handling / graceful degradation:** every Qwen stage fails open — recall never
  hard-fails an answer; rerank/streaming/tool-loop each degrade to the prior behavior; the
  circuit breaker sheds load on outage.
- **Scalability — honest and bounded:** single-process today; the O(N²) association step and its
  ANN replacement are documented with a plan (`ROADMAP.md`), and `qwen3-rerank` is built but
  **kept off** until a memory is large enough to need it (measured null lift — `docs/benchmark.md`).
  Concrete steps taken, flag-gated + measured: a **numpy-vectorized cosine** (`RG_VECTORIZED`,
  **3.1–3.3× faster at N=1k/10k, bit-identical ranking** — `harness/latency_bench.py`), a
  **bounded async judge fan-out** (`RG_ASYNC_REVISE`, semaphore-capped so rate-limit/breaker hold),
  and **batched gold-set embeddings** (`RG_BATCH_EMBED`). Framed honestly: constant-factor +
  fewer round-trips, not an asymptotic fix.
- **Context-window efficiency (measured):** value-density packing under a hard token budget
  (`RG_RECALL_BUDGET`) injects the critical lesson in **~37 % fewer tokens at identical recall**
  (`harness/context_window_bench.py`) — the literal realization of the track's "limited context
  windows", reproducible offline.
- **Advanced patterns / non-trivial logic:** contradiction detection on teach, ExpeL-style
  crystallization, Hebbian associative wiring kept *out* of the confidence signal, and a
  self-tuning retrieval fuser adopted only after beating a **held-out** baseline.

## 3 · Problem Value & Impact (25%)
*"Real-world relevance solving an authentic technical/business pain? Scalability potential for
productization or open-source community adoption?"*

- **Authentic pain, quantified:** AI agents ship faster and regress more — nearly **half of AI
  coding spend goes to fixing bugs** the agent re-introduces. Every judge who uses a coding agent
  has felt this.
- **Productized today:** MIT, public repo, live cloud deployment; a `regress-guard` CLI with a
  one-command `doctor` readiness check; **zero-install** adoption (point any MCP client at the
  hosted URL — no key, no DB). Verify in under two minutes: open the live demo, hit `/health`
  and `/receipts/{id}`, or `pip install -e . && regress-guard doctor`.
- **OSS adoption signals:** `CHANGELOG.md`, `ROADMAP.md`, `CONTRIBUTING.md` (with a "good first
  issue": add a benchmark bug-class), `SECURITY.md`, and a "works with any MCP agent" story.

## 4 · Presentation & Documentation (15%)
*"Clear technical demo with key logic visualized? Clear documentation including architecture docs?"*

- **Key logic visualized:** the living-memory UI — an editable deck (each card shows its
  **receipts**: the real test outcomes that earned its Beta confidence), a Chat/Duel/Proof view,
  and a persistent 3D knowledge globe whose nodes pulse live as lessons are recalled. The money
  shot: same AI, same task, temperature 0 → **0/5 without memory, 5/5 with it**, and a lesson
  being **tombstoned** when a real test proves it wrong.
- **Docs:** this file, `README.md`, `docs/benchmark.md` (the reproducible result), an
  architecture diagram, and a ~3-minute demo video.

---

## Limits & Negative Results (we report these on purpose)
- **Benchmark N is small (50).** The earned-vs-add-only edge is directional (McNemar p≈0.0625,
  the floor achievable at this N), not yet p<0.05. Growing N is the first roadmap item.
- **qwen3-rerank shows no lift** at our memory size (RRF already ~0.95 MRR) — so it's off. We'd
  rather ship the honest null than a stage that doesn't help.
- **Self-eval / self-tune holdout is n=10** — an illustrative lift (Recall@1 0.35→0.50; held-out
  0.40→0.60), labeled illustrative, kept for the holdout *discipline*, not as significance.

## What we do NOT claim
- Not "guaranteed 100%": the 5/5 is the injection **ceiling** (remembered fix, verbatim); the
  shipped auto-distiller is reported at its **Wilson lower bound (72%)**, not the point estimate.
- Not "leaks across tenants": the base model **fails an isolation test**; we never overstate it.
- The temp-0 in-run trials are a **consistency check**, not independent samples — only the
  distillations are, which is why the Wilson interval lives there.
- Confidence is earned only from real tests; associative wiring and salience **never** move it.
