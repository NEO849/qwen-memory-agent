# Security Policy

Regress-Guard ingests text (test output, diffs, notes) and injects recalled lessons into an LLM
prompt, so **prompt injection via poisoned memory** is a first-class threat we test for.

## What we defend against
- **Poisoned-memory / indirect prompt injection.** Recalled lessons are neutralised before they
  reach the model (embedded directives are stripped/flagged), and a recalled *anti-pattern* can
  inhibit a lesson rather than obey it. The adversarial suite
  [`tests/test_injection_defense.py`](tests/test_injection_defense.py) drives the system from
  **vulnerable → safe**; we also fuzz it with garak/Promptfoo.
- **Cost / resource abuse.** The API applies body-size caps and per-IP rate limits on the paid
  Qwen path (see `backend/main.py`), and the Qwen client has a circuit breaker + graceful
  degradation so a dependency outage can't cascade.
- **Secret hygiene.** The `DASHSCOPE_API_KEY` lives only in `.env` / the deployment environment
  (git-ignored) and is never logged or returned by any endpoint.

## Reporting a vulnerability
Please open a **private** report via GitHub Security Advisories on
[NEO849/qwen-memory-agent](https://github.com/NEO849/qwen-memory-agent/security/advisories), or
open an issue that describes impact without a working exploit payload. We aim to acknowledge
within a few days. Please do not include real secrets or third-party personal data in reports.
