"""Controlled staging check for the Welle-1 Qwen-depth flags — ONE paid DISTILL call.

Run this yourself (it bills a single Qwen call), with the flags forced on, to confirm the
reasoning-stream + structured-output paths behave against the REAL endpoint before we deploy them:

    cd ~/qwen_hackathon && \
    RG_REASONING_ENABLED=1 RG_STRUCTURED_OUTPUT=1 RG_MODEL_ROUTING=1 \
    .venv/bin/python -m deploy.verify_wave1_staging

It prints, for a tiny fixed red-test+diff:
  * which model served DISTILL (routing),
  * whether the distilled lesson JSON is well-formed (structured output),
  * whether a Qwen3 reasoning_content trace was captured (reasoning stream).

Interpreting it:
  * lesson JSON present + model shown  → routing + (schema or json_object fallback) OK to deploy.
  * reasoning trace present            → reasoning stream works on this model → safe to show in UI/video.
  * reasoning trace EMPTY              → this model doesn't stream thinking; keep RG_REASONING_ENABLED
                                         OFF in prod (feature degrades silently, nothing breaks),
                                         or point RG_MODEL_DISTILL at a thinking-capable model.
Nothing here writes to the live ledger; it only exercises the Qwen client.
"""
from __future__ import annotations

from backend import config, extractor, telemetry

_RED = ("FAILED test_tenant_isolation - AssertionError: tenant B saw tenant A's orders\n"
        "get_orders() returned rows across tenants")
_DIFF = ("--- a/app.py\n+++ b/app.py\n"
         "-    return db.query('SELECT * FROM orders')\n"
         "+    return db.query('SELECT * FROM orders WHERE tenant_id = ?', user['tenant_id'])")


def main() -> None:
    print("flags:", {"RG_REASONING": config.RG_REASONING,
                     "RG_STRUCTURED_OUTPUT": config.RG_STRUCTURED_OUTPUT,
                     "RG_MODEL_ROUTING": config.RG_MODEL_ROUTING,
                     "distill_model": config.model_for("distill")})
    telemetry.reset()
    lesson = extractor.extract_lesson(_RED, _DIFF)          # one paid DISTILL call
    print("\nlesson JSON well-formed:", all(k in lesson for k in ("trigger", "lesson", "scope", "severity")))
    print("lesson:", lesson)
    snap = telemetry.snapshot()["roles"].get("distill", {})
    print("\nDISTILL served by model:", snap.get("model"))
    traces = telemetry.reasoning_snapshot()
    if traces:
        print("reasoning trace CAPTURED (chars):", len(traces[0]["reasoning"]))
        print("  preview:", traces[0]["reasoning"][:240].replace("\n", " "))
        print("\n=> reasoning stream works — safe to surface at /reasoning + in the video.")
    else:
        print("reasoning trace EMPTY.")
        print("=> keep RG_REASONING_ENABLED OFF in prod, or route DISTILL to a thinking-capable model.")


if __name__ == "__main__":
    main()
