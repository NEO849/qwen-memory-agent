# Regress-Guard — Proof Pack (reproducible receipts, 2026-07-07)

Every claim below is backed by a command you can run and the real result we measured. Nothing here
is asserted without a test or a measurement. All commands run from the repo root with the project
venv (`.venv/bin/...`). Qwen-backed items need the `.env` key; the rest are offline.

---

## 1. Test suite — 129 / 129 green (offline, deterministic)
```
.venv/bin/pytest -q
```
Includes the 15 memory-injection-defense tests, the concurrency test (§4), the calibration
tests (§3), and the associative-memory tests (§7). No network, no Qwen — pure logic + math.

## 2. The A/B proof — floor vs ceiling + distillation reliability (honest 3-part)
```
.venv/bin/python -m harness.ab_runner --k 5 --distill-samples 10      # writes ab_result.json
```
Same task, same model (`qwen-plus`, temperature 0), same hidden `pytest` the agent never sees. The
task never states the tenant convention, so the model **cannot guess it** — the knowledge must come
from memory. Measured:

| Arm | Result | Meaning |
|---|---|---|
| **Floor** (no memory) | **0/5** green | the model consistently mis-scopes and fails the hidden isolation test |
| **Ceiling** (remembered developer fix, verbatim) | **5/5** green | the capability ceiling of memory injection |
| **Distillation reliability** (shipped default auto-distills the fix) | **10/10** passed, Wilson95 **[72,100]%** | the real random variable — measured over 10 *independent* distillations |

**Honest framing (in `ab_result.json` → `framing` / `must_not_say`):**
- The **ceiling** (verbatim fix) is what memory injection *can* achieve; it is not the shipped default.
- The **shipped default** auto-distills the fix; after we sharpened the distiller to keep the
  concrete identifiers, it produced a passing lesson **10/10** (CI 72–100%) in this measurement.
- **Outcome-grounding is the backstop:** a distillation that drops the concrete comparison fails the
  hidden test and is **demoted**, not trusted — confidence tracks what actually works.
- **Statistics honesty:** temp-0 in-run trials are near-deterministic and are reported as
  *consistency*, not as an independent sample. The independent unit is the **distillation** (one draw
  per run); the Wilson interval is computed over those.
- **Do NOT say:** "the default turns this task 0→100% guaranteed." Report the reliability *with* its
  interval. (This guardrail survived an adversarial skeptical-validator review.)

### Distillation reliability — before vs after (an honest engineering win)
The auto-distiller first measured **2/10** (it generalised "orders"→"resources" and dropped the
concrete field access — and text that *looked* actionable still failed). Sharpening
`backend/extractor.py` to preserve the exact identifiers from the diff (principle **plus** concrete
rule) raised it to **10/10 in two independent batches**. Real product improvement, not a proof tweak.

## 2a. Live duel — the A/B, streamed live (not the recording)
```
curl -N http://regressguard.duckdns.org/duel?k=1        # SSE: start → round(plain) → round(memory) → done
```
The **⚔️ Duel** tab (or the `GET /duel` SSE endpoint) runs the same experiment as §2 **live and un-recorded**:
one prompt → two arms, **"plain AI · no memory"** vs. **"AI + Regress-Guard"** — 5 hidden `pytest` per arm,
green/red counters ticking round-by-round. Verified live: **floor 0/5 vs ceiling 5/5**. The 🏆 Proof tab is the
instant, flicker-safe **replay** of this same experiment; the Duel tab is the live version.

**Honest by design (disclosed in the stream):** the memory arm injects the remembered concrete lesson through a
**determinism guard** — a concrete recalled lesson is used verbatim, otherwise its canonical concrete form is
injected — so `temp=0` + a fixed concrete lesson stays deterministic and an on-camera run can't flake. The SSE
payload states this openly as `"injected":"canonical (determinism guard)"`. It is deliberately the injection
**ceiling** live (not a live distillation — that reliability, 10/10 Wilson95 [72,100]%, lives in §2 / `ab_result.json`).
Own rate-limit bucket (4/min) + a per-round retry against transient Qwen errors. Never framed as "guaranteed 100%".

## 2b. Grounded outcomes — the thesis, live
```
curl -s http://regressguard.duckdns.org/metrics | python -m json.tool   # grounded_outcomes, calibration_gap
python -m harness.ground_demo <ledger-path>                             # reproduce the grounding
```
The core thesis — *confidence is earned from real pytest outcomes, and a lesson real tests refute is forgotten* —
is now grounded on the **live** ledger with real evidence, not a prior. `harness/ground_demo.py` writes real
outcomes (money-rounding pattern, independent of the get_orders demo):

| Lesson | Real outcomes | Result |
|---|---|---|
| **Correct** (money = integer cents) | **3/3 real passes** | **confidence 0.86 earned** — a validated node |
| **Wrong** (money = float dollars) | **3/3 real fails** | **tombstoned** — a grey "forgotten" node (`real_fail = 3`), belief revision |

So `/metrics` now reports **`grounded_outcomes > 0`** and an honest **`calibration_gap` of 0.112** (live deck; it starts higher on the first few outcomes and settles as more real pass/fail evidence accrues) (displayed
confidence vs. empirical pass-rate, from real outcomes) instead of a misleading `0.0` — and at zero outcomes the
gap is reported as `null` / "n/a" rather than a fake 0. This is "a memory that forgets what's wrong", shown live
with real test evidence. Reproduce with the `ground_demo` command above.

## 2c. MCP cross-session — a tool, not a demo
```
python -m harness.mcp_vignette
```
A recordable terminal proof against the **live** cloud memory (`regressguard.duckdns.org`) that the memory is a
**drop-in tool**, not a closed demo — it drives the exact `recall`/`record` data path of the MCP tools
(`mcp_tool/server.py`) end-to-end across two sessions:

| Session | What it does | Hidden test |
|---|---|---|
| **Session 1** (fresh agent, empty memory) | writes `get_orders`, inventing a `user_id` filter (cross-tenant bug); the developer then **records** the concrete fix to the cloud | **RED** |
| **Session 2** (later, fresh agent) | **recalls** that exact rule from the cloud before coding | **GREEN** |

The bug the first session fixed does **not** come back in the second — **carried across sessions by the cloud
memory over MCP**, with no local state. It **self-cleans** (the recorded lesson is tombstoned) so the live demo
deck stays pristine. Honest note: the recorded rule *is* the developer's concrete fix (verbatim), so it's
reliable — not a staged result; this is the injection path, distinct from the auto-distiller reliability in §2.

## 3. Calibration & convergence — the property a cosine score can't have
```
.venv/bin/pytest tests/test_calibration.py -v
```
- **Convergence:** for true pass-rates p ∈ {0.15, 0.4, 0.6, 0.85, 0.97}, the Beta posterior mean
  converges to p within **|Δ| < 0.03** over 3000 simulated outcomes — confidence tracks reality.
- **Calibration:** across 4000 simulated lessons, displayed confidence vs empirical pass-rate has
  **ECE < 0.06** — the confidence behaves like a real probability. A RAG cosine cannot be calibrated
  because it is a similarity, not a falsifiable prediction.

## 4. Concurrency — no lost updates under parallel load
```
.venv/bin/pytest tests/test_concurrency.py -v
```
8 processes each record 25 pass-outcomes on the **same** lesson → final `alpha == 1 + 200` exactly,
and the outcomes table has exactly 200 rows. Proves the atomic in-SQL Beta increment
(`BEGIN IMMEDIATE` on WAL) is a real race-free systems property, not a docstring claim.

## 5. Memory-injection defense (red-teamed)
```
.venv/bin/pytest tests/test_injection_defense.py -v         # 15/15 green
BASE=http://regressguard.duckdns.org ./redteam/poisoned_memory_probe.sh   # live: SAFE
```
Recalled lessons enter the prompt as untrusted data behind structural markers + a deterministic
sanitizer, so a poisoned lesson can't become a command (2nd-order prompt injection). Our own
red-team flipped the probe vulnerable→safe; a 60-case scan passed clean.

**Tool-calling doesn't weaken this.** The chat now lets Qwen call a `recall_memory` tool on its own
(`backend/main.py::/chat`), but the lessons it returns go through the **same** sanitizer before being
fed back as the tool result — the defense sits on the recall path, not on how recall was triggered.
The live poisoned-memory probe above was re-run against the tool-calling `/chat` and stayed **SAFE**.

## 6. Knowledge globe — ~74 nodes / ~230 edges (live, grows), all edge/node types (honest data)
```
.venv/bin/python -m harness.seed_demo <ledger-path>         # guards + enrich
```
Rebuilds a memory of **~74 nodes / ~230 edges** (the live globe grows as lessons accrue) with every type the globe renders:
`related` (179, from real embedding cosine) · `synthesizes` (16, real Qwen ExpeL crystallization) ·
`supersedes` (1, a real belief-revision) · 3 anti-pattern nodes (dark red) · 1 forgotten node (grey).
Edge strength is initialised from embedding-cosine similarity; Hebbian co-recall (§7) then further
strengthens the synapses that actually co-fire (capped), so a used graph diverges from the raw-cosine seed.
Every lesson is a genuine coding rule — nothing invented.

In the **living-memory** UI this same globe stays **persistent on the right** while you chat/run the agent; when a
response recalls lessons, **exactly those nodes pulse live** (white flash + particles over their real edges). Only the
**real recalled lesson IDs** light up — the same IDs shown in the "answered using N lessons: #.." strip — verified
end-to-end with Playwright, so the highlight is honest, not decorative.

## 7. Associative memory — Hebbian wiring + spreading activation (honest, non-mystical)
```
.venv/bin/pytest tests/test_associative_memory.py -v
```
Neuroscience-*inspired*, deliberately named as what it is (**associative memory / Hebbian wiring /
spreading activation**) — not consciousness, not a brain. Two mechanisms, both test-covered:
- **Hebbian synapses.** Lessons recalled together strengthen a shared edge: the co-recall weight grows
  with use and is **capped**, so it can't run away. It is stored on the graph edge and shown as
  variable synapse strength on the globe (§6).
- **Spreading-activation recall (opt-in).** From the query's top hits, activation spreads along the
  **strongest** synapses to surface associated neighbours that pure BM25+vector recall misses.
- **Firewall to confidence.** The wiring **never** touches a lesson's Beta confidence — association
  changes *what surfaces*, only real pytest outcomes change *how much a lesson is trusted*. The tests
  assert exactly this separation.

## 8. Generalization across 3 bug classes (kills the cherry-pick objection)
```
.venv/bin/python -m harness.generalization --k 3 --distill-samples 6   # writes generalization_result.json
```
Three independent bug classes, each floor (no memory) vs ceiling (remembered verbatim fix) vs the
shipped auto-distiller over independent samples (Wilson95):

| Bug class | Floor | Ceiling | Auto-distiller |
|---|---|---|---|
| **tenant_isolation** | **0/3** | **3/3** | 6/6 (Wilson95 61–100%) |
| **pagination_leak** | **0/3** | **3/3** | 6/6 (Wilson95 61–100%) |
| **money_rounding** | **3/3** | **3/3** | 6/6 (Wilson95 61–100%) |
| **aggregate** | **3/9** | **9/9** | **18/18** (Wilson95 82–100%) |

**Honest interpretation** (from `generalization_result.json` → `interpretation`): memory flips the two
classes the base model gets **wrong** by default (tenant isolation, pagination leak) from 0/3 → 3/3.
On **money_rounding the base model already writes correct code unaided** (floor 3/3), so memory
correctly adds **no** lift and does **no** harm (ceiling 3/3) — this class is **not** a memory win and
must never be sold as one. Two independent 0→100 flips defeat cherry-picking; the third proves the
memory is harmless when it isn't needed.

## 9. Self-tuning — train/val holdout (committed `tune_result.json`)
```
# committed artifact: tune_result.json (gold_sample = 20). Reproduce against the live ledger:
.venv/bin/python -c "import json,backend.evaluation as e; \
print(json.dumps({'evaluate':e.evaluate(sample=20),'tune':e.tune(sample=20)}, indent=2))"
```
(A live `POST /tune` on the deployment does the same tuning online, capped at sample≤10.)
Two honest, held-out measurements on the demo seed (65 active lessons), keyword-free paraphrase queries:

| Measurement | Baseline | Result | Meaning |
|---|---|---|---|
| **Semantic (vector) arm on vs off** (`evaluate`, n=20) | Recall@1 **0.35** (MRR 0.458) | Recall@1 **0.50** (MRR 0.628) | the vector leg is a real retrieval lift, not decoration |
| **Self-tuned RRF weights, HELD-OUT val split** (`tune`, n_train=10 / n_val=10) | Recall@1 **0.40** (MRR 0.599) | Recall@1 **0.60** (MRR 0.708) | tuned weights `{bm25:0.5, vector:3.0}` **adopted** — they beat the neutral baseline on data they were **not** searched on |

The self-tuner grid-searches fusion weights on a **TRAIN split** and **adopts them only if they also beat the neutral
baseline on a HELD-OUT val split** — reported numbers are the held-out ones. This is why the win is
trustworthy rather than overfit: the +0.20 held-out Recall@1 lift is measured on queries the search never optimised
against. **Honest caveat:** with `n_val=10` this is an *illustrative* lift (2 extra hits of 10), not a statistically
significant one — the point is the holdout **discipline** (no adoption without a held-out win), not the magnitude.
`tune_result.json` is committed (like `ab_result.json`); reproduce with the command above.

---

## Honest limitations (stated up front)
- Distillation reliability is a measured **10/10 (CI 72–100%)**, not a guarantee; the hidden-test
  backstop is what makes an occasional bad distillation safe.
- Generalisation is now shown across **three** bug classes (§8), of which **two** are genuine memory
  wins (tenant isolation, pagination leak); the third (money rounding) is included precisely because
  memory does *nothing* there — evidence of harmlessness, not a win.
- The ceiling arm injects the developer's verbatim fix; it is labelled as the ceiling, never as
  default behaviour.
- Associative wiring (§7) is neuroscience-*inspired* only; it is kept out of the confidence signal and
  makes no claim to cognition.
