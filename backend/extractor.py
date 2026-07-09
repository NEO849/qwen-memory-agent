"""Qwen role 1 — DISTILL: turn a red test + human fix into a reusable lesson.

Given the failing test output and the diff that fixed it, Qwen distills a compact,
generalizable rule so the same class of bug is not reintroduced in a later session.

Output schema (validated, never trusted raw):
    {
      "trigger":  str,   # the situation that should recall this lesson
      "lesson":   str,   # the imperative rule to follow
      "scope":    str,   # where it applies (file/module/symbol/glob), free-form
      "severity": str,   # one of: low | med | high
    }
"""
from __future__ import annotations

from . import config, qwen_client

SEVERITIES = ("low", "med", "high")

# Strict JSON Schema for the distilled lesson — enforced model-side when RG_STRUCTURED_OUTPUT is
# on (graceful fallback to json_object otherwise). Mirrors the four validated keys + severity enum.
LESSON_SCHEMA = {
    "type": "object",
    "properties": {
        "trigger": {"type": "string"},
        "lesson": {"type": "string"},
        "scope": {"type": "string"},
        "severity": {"type": "string", "enum": ["low", "med", "high"]},
    },
    "required": ["trigger", "lesson", "scope", "severity"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are a senior code-review memory. A test went red and a human fixed it. "
    "Distill ONE reusable lesson that stops an AI coding agent from reintroducing this class of "
    "bug in a future session. A good lesson is BOTH principled AND directly actionable, so write "
    "the `lesson` as TWO sentences: "
    "(1) the general principle, then "
    "(2) the concrete rule using the EXACT identifiers that appear in the diff and test — the real "
    "function name, the field on the object being filtered, and the field on the subject/user. "
    "Do NOT replace those identifiers with generic placeholders like 'resource', 'object' or 'item'; "
    "keep the actual names (e.g. if the code is get_orders and the guard is "
    "order['tenant_id'] == user['tenant_id'], say exactly that, not 'resource[...]'). "
    "If the bug came from confusing two fields (e.g. user['tenant_id'] vs the numeric user['id']), "
    "state explicitly which one to compare against AND which one NOT to use. "
    "Return ONLY a JSON object with exactly these keys: "
    "trigger (the situation that should surface this lesson), "
    "lesson (the two sentences above), "
    "scope (where it applies: file / module / symbol / glob, free-form), "
    "severity (one of: low, med, high)."
)


def _clamp_severity(value: object) -> str:
    v = str(value or "").strip().lower()
    if v in SEVERITIES:
        return v
    # tolerate common synonyms from the model
    return {"medium": "med", "moderate": "med", "critical": "high", "warning": "low"}.get(v, "med")


def extract_lesson(test_output: str, diff: str, model: str | None = None) -> dict:
    """Distill a lesson from a red test + fix diff. Returns the validated schema dict."""
    user = (
        "FAILING TEST OUTPUT:\n"
        f"{test_output.strip()[:6000]}\n\n"
        "FIX DIFF:\n"
        f"{diff.strip()[:6000]}\n\n"
        "Return the lesson JSON now."
    )
    raw = qwen_client.chat_json(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        model=model or config.model_for("distill"),
        schema=LESSON_SCHEMA,
        capture_reasoning=True,
        temperature=0,
        role="distill",
    )
    return {
        "trigger": str(raw.get("trigger", "")).strip(),
        "lesson": str(raw.get("lesson", "")).strip(),
        "scope": str(raw.get("scope", "")).strip(),
        "severity": _clamp_severity(raw.get("severity")),
    }


if __name__ == "__main__":
    demo_test = (
        "FAILED test_tenant_isolation - AssertionError: tenant B saw 3 of tenant A's orders\n"
        "get_orders() returned rows across tenants"
    )
    demo_diff = (
        "--- a/app.py\n+++ b/app.py\n"
        "-    return db.query('SELECT * FROM orders')\n"
        "+    return db.query('SELECT * FROM orders WHERE tenant_id = ?', user.tenant_id)"
    )
    from pprint import pprint
    pprint(extract_lesson(demo_test, demo_diff))
