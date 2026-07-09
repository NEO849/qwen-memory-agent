# Does earned-confidence memory actually help? — a 3-arm honest benchmark

The floor→ceiling proof (0/5 → 5/5) shows memory *can* help, but a skeptic reads it as
tautological: of course the stored fix passes. **This benchmark isolates Regress-Guard's actual
innovation** — gating injection on confidence *earned from real pytest outcomes* — against the
obvious baseline, on bug variants the memory never stored verbatim.

Reproduce in one line (every paid Qwen call is disk-cached; seeds are pinned):

```bash
./bench.sh            # k=5 seeds, ground=3, temp=0.7, gate=0.62  ->  bench_result.json
```

## Setup

Three arms. **Same retrieval, same model (qwen-plus), same pinned seeds.** They differ in exactly
one scalar — the confidence threshold passed to `should_inject` (`backend/confidence.py`):

| arm | what it does |
|---|---|
| **A — no memory** | control / floor: the agent codes with no lesson injected |
| **B — naive add-only** | `recall(threshold=0.0)`: inject the top-retrieved lesson regardless of earned confidence (literally today's default) |
| **C — Regress-Guard** | `recall(threshold=0.62)`: inject only lessons whose **Beta posterior mean cleared the gate**; unproven / plausible-but-wrong lessons are withheld |

**Store (built once, shared by B and C):** each of 5 bug classes contributes a *correct* lesson,
**grounded by real pytest runs** so it earns confidence (~0.80). Three *plausible-but-wrong*
lessons (authoritative, on-topic, but bug-reintroducing) are added and **never earn confidence**
— they sit at the Beta(1,1)=0.50 prior, below the gate. B injects them; C withholds them.

**Two regimes per class:** **SEEN** (the exact task the seed came from) and **UNSEEN** (a
same-convention *variant* — different function/surface — the distiller never stored verbatim).
UNSEEN is where transfer, not memorization, is measured. 5 classes: `money_rounding`,
`pagination_leak`, `email_normalize`, `sql_param`, `mutable_default`.

## Result (N = 50: 5 classes × 2 regimes × 5 seeds, qwen-plus, temp 0.7)

fix-pass@1 with 95% Wilson intervals:

| arm | SEEN | UNSEEN |
|---|---|---|
| A · no memory | 0.60 [0.41, 0.77] | 0.60 [0.41, 0.77] |
| B · naive add-only | 0.88 [0.70, 0.96] | 0.60 [0.41, 0.77] |
| **C · Regress-Guard** | **1.00 [0.87, 1.00]** | **0.80 [0.61, 0.91]** |

**C strictly dominates both A and B on both regimes.** On UNSEEN variants, earned-confidence
gating fixes **5 cases that naive add-only misses, breaking none** (McNemar B-vs-C: +5 / −0,
p = 0.0625). The mechanism: a naive add-only memory lets an *unproven / wrong* lesson crowd the
*earned* one out of the retrieved top-K; the gate withholds the unproven lesson, so the earned
one surfaces and drives the transfer fix.

**Harmful-injection: 0/50 under both memory arms** — neither broke a test the no-memory arm
passed in this suite. So the gate's win here is on **transfer fix-rate**, not harmful-injection;
the adversarial poisoned-memory case is demonstrated separately by the red-team suite
(`tests/test_injection_defense.py`, garak/promptfoo: vulnerable → safe).

## Honesty notes (what we do NOT claim)

- The gate **0.62** is chosen *a priori*, just above the 0.50 unproven prior — **not tuned on
  results**. The SEEN/UNSEEN split and the class suite were fixed before the run (no p-hacking).
- **N is small.** A McNemar p = 0.0625 (5 discordant, all one-way) is the *minimum achievable*
  at this N — directional, not yet p < 0.05. Where a Wilson CI overlaps, the result is
  directional and reported as such.
- Eval codegen uses temp > 0 so the pass-rates carry honest CIs; seeds are pinned so the whole
  table is reproducible from a clean clone.
- The baseline B is a *reasonable* memory (it retrieves relevant fixes) — not a strawman. The
  only thing it lacks is the confidence gate, which is precisely Regress-Guard's contribution.

## Ablation: does a qwen3-rerank stage help? (an honest negative)

We built a third retrieval stage — the `qwen3-rerank` cross-encoder after BM25+vector RRF
(`backend/qwen_client.py:rerank`, wired into `memory.recall` behind `RERANK_ENABLED`) — and
measured whether it improves *findability of the correct lesson* over the 5 classes
(`.venv/bin/python -m harness.rerank_eval`, n=10 seen+unseen contexts):

| retrieval | Recall@1 | Recall@3 | MRR |
|---|---|---|---|
| RRF only | 0.90 | 1.00 | 0.95 |
| + qwen3-rerank | 0.90 | 1.00 | 0.95 |

**No measured lift.** At our current memory size RRF already ranks the right lesson ~0.95 MRR,
so a cross-encoder has nothing to fix — and it adds ~880 ms per recall (well over our 400 ms
budget for the single-worker SSE path). So **rerank ships built, tested and graceful, but OFF
by default**: it earns its place only once a memory grows large/ambiguous enough that ranking
gets hard. We'd rather report the honest null than feature a stage that doesn't help at our scale.

## Context-window efficiency — packing critical memories under a token budget

The MemoryAgent track asks for *"recalling critical memories within limited context windows."*
We made that literal: `RG_RECALL_BUDGET` replaces top-*k*-by-count with greedy **value-density
packing** — `confidence × relevance ÷ token_cost` — under a hard token budget
(`backend/memory.py:_pack_budget`). A judge can reproduce the number offline, **no API key**
(BM25-only, deterministic): `python -m harness.context_window_bench`.

On a domain-specific subset (a seeded coding-lesson deck, 4 bug classes):

| recall strategy | avg tokens injected | recall of the critical lesson |
|---|---|---|
| naive top-5 | 153.8 | 1.00 |
| value-density packing (budget) | **96.5** | **1.00** |

**~37 % fewer tokens at identical recall** — the density packer keeps the earned-confidence lesson
and drops the low-value filler. And because the score is driven by *earned* confidence, tombstoning
a plausible-but-wrong lesson (**timely forgetting**) removes it from injection entirely:

| | harmful-injection rate |
|---|---|
| wrong lesson active | 1.00 |
| wrong lesson tombstoned | **0.00** |

> **Honest scope.** This is a *domain-specific subset*, not a full **LoCoMo / LongMemEval** run —
> those remain the field-standard agent-memory benchmarks this design aligns with. We report the
> subset delta only, with no generalized SOTA claim.

## Latency — vectorized cosine (an honest constant-factor win)

The pairwise-cosine hot loop can run as a numpy matmul (`RG_VECTORIZED`, numpy imported
defensively — absent numpy or flag off falls straight back to the scalar path). Reproduce offline:
`python -m harness.latency_bench`.

| N embeddings (dim 1024) | scalar Python | numpy matmul | speedup |
|---|---|---|---|
| 1 000 | 196.5 ms | 62.7 ms | **3.1×** |
| 10 000 | 1757.8 ms | 539.6 ms | **3.3×** |

Ranking is **numerically identical** to the scalar path (max score diff ≈ 1e-16 — never crosses a
threshold or reorders distinct scores; asserted in `tests/test_vectorized.py`). Framed honestly:
this shrinks the **constant factor** and unlocks a future ANN index — it does **not** change the
O(N) asymptotics, and we don't claim it does.

## External anchor — LongMemEval `knowledge-update` (does our memory help on a STANDARD benchmark?)

Every self-built number above answers "does the *mechanism* help?" — but a memory-track judge also
asks "what's your score on a benchmark I recognise?" So we ran the official **LongMemEval** (ICLR
2025) `knowledge-update` questions (a fact is updated across sessions; the correct answer is the
most recent value) through our **real** pipeline — ingest every timestamped session turn →
`memory.recall` → `render_injection` → Qwen answers → LongMemEval-style yes/no judge (+ exact-match
fallback). Reproduce: `python -m harness.longmemeval_eval --n 40`.

| arm | correct | accuracy (Wilson 95%) |
|---|---|---|
| no memory (floor) | 2 / 39 | **5.1 %** [1.4, 16.9] |
| **Regress-Guard memory** | 33 / 39 | **84.6 %** [70.3, 92.8] |

**Our memory lifts knowledge-update QA from 5 % to 85 % on an external benchmark** — a +79-point
lift, the first number here that isn't self-defined. It validates our **retrieval leg** end-to-end.

**Honest scope & an honest null (two of them):**
- **Oracle split** (evidence sessions only) — easier than the full haystack, so this is **not**
  leaderboard-comparable to published full-haystack scores. We report the memory-vs-no-memory lift.
- **Recency ablation = 0.0.** A third arm injected the *same retrieved facts with timestamps
  stripped*; it scored **identically (84.6 %)**. So on this subset our explicit recency signal added
  **no measurable value** — the QA model resolves "most recent" on its own. We report that null
  rather than dress it up, exactly as we did for `qwen3-rerank`.
- LongMemEval has **no executable outcomes**, so it cannot test our actual contribution — the
  *outcome-grounded confidence gate*. No public benchmark scores outcome-grounded forgetting yet;
  that gap is our moat, measured by the self-built benchmarks above. (1 malformed record skipped → N=39.)
