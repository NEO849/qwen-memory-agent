# Changelog

All notable changes to Regress-Guard are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-07-09

First public release: an outcome-grounded, self-correcting memory for AI coding agents.

### Added
- **Outcome-grounded confidence** — every lesson's confidence is the posterior mean of a
  Beta(α,β) that moves only on real pytest pass/fail; lessons that fail get demoted or
  tombstoned ("timely forgetting").
- **Qwen Cloud in five roles** — DISTILL, RECALL (`text-embedding-v4` + BM25/RRF), REVISE,
  SELF-CHECK, and FUNCTION-CALLING (the model decides, via a `recall_memory` tool, when to
  consult memory).
- **MCP drop-in tool** (`recall` / `record`) that talks to the hosted Alibaba Cloud deployment
  (zero local setup) or a local backend.
- **Live UI** — editable memory deck, Chat / Duel / Proof views, and a persistent 3D knowledge
  globe that lights up as lessons are recalled.
- **3-arm honest benchmark** (`./bench.sh`) — no-memory vs naive add-only vs earned-confidence
  gating, on seen and unseen bug variants, with Wilson CIs and McNemar. Reproducible, cached.
- **`/receipts/{id}`** — traces any lesson's confidence back to the append-only list of real
  test outcomes that earned it (surfaced in the deck too).
- **Observability** — per-Qwen-role latency/token telemetry (`/telemetry`), a correlation id
  across the DISTILL→RECALL→REVISE→SELF-CHECK chain, and an enriched `/health`.
- **`regress-guard` CLI** — `doctor` (one-command readiness check), `mcp` (stdio server),
  `serve` (local backend + UI).
- **Resilience** — typed retry with exponential backoff + jitter and a circuit breaker on the
  Qwen path; graceful degradation everywhere (memory never hard-fails an answer).
- **Poisoned-memory defense** — recalled lessons are sanitized before injection; adversarial
  suite (`tests/test_injection_defense.py`) goes vulnerable → safe.

### Behind a flag (built, measured, off by default)
- **qwen3-rerank** cross-encoder retrieval stage — shipped and tested, but **off**: on our
  current memory RRF already ranks the right lesson (~0.95 MRR) so it adds latency without a
  measured lift (see `docs/benchmark.md`). Kept for when a memory grows large enough to need it.
- **Token streaming** for chat and a **bounded multi-step tool loop** (recall → traverse the
  associative graph → answer) — enable with `STREAMING_ENABLED` / `TOOL_LOOP_ENABLED`.
