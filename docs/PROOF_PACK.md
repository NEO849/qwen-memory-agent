# Regress-Guard — Proof Pack (reproducible receipts, 2026-07-07)

Every claim below is backed by a command you can run and the real result we measured. Nothing here
is asserted without a test or a measurement. All commands run from the repo root with the project
venv (`.venv/bin/...`). Qwen-backed items need the `.env` key; the rest are offline.

---

## 1. Test suite — 51 / 51 green (offline, deterministic)
```
.venv/bin/pytest -q
```
Includes the 6 memory-injection-defense tests, the concurrency test (§4), and the calibration
tests (§3). No network, no Qwen — pure logic + math.

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
.venv/bin/pytest tests/test_injection_defense.py -v         # 6/6 green
BASE=http://regressguard.duckdns.org ./redteam/poisoned_memory_probe.sh   # live: SAFE
```
Recalled lessons enter the prompt as untrusted data behind structural markers + a deterministic
sanitizer, so a poisoned lesson can't become a command (2nd-order prompt injection). Our own
red-team flipped the probe vulnerable→safe; a 60-case scan passed clean.

## 6. Knowledge globe — 42 nodes, all edge/node types (honest data)
```
.venv/bin/python -m harness.seed_demo <ledger-path>         # 35 guards + enrich
```
Rebuilds a memory of **42 nodes / 51 edges** with every type the globe renders:
`related` (42, from real embedding cosine) · `synthesizes` (8, real Qwen ExpeL crystallization) ·
`supersedes` (1, a real belief-revision) · 3 anti-pattern nodes (dark red) · 1 forgotten node (grey).
Every lesson is a genuine coding rule — nothing invented.

---

## Honest limitations (stated up front)
- Distillation reliability is a measured **10/10 (CI 72–100%)**, not a guarantee; the hidden-test
  backstop is what makes an occasional bad distillation safe.
- The A/B demonstrates **one** bug class (tenant isolation). A second class would strengthen the
  generalisation claim (planned).
- The ceiling arm injects the developer's verbatim fix; it is labelled as the ceiling, never as
  default behaviour.
