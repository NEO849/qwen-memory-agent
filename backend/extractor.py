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

from . import qwen_client

SEVERITIES = ("low", "med", "high")

_SYSTEM = (
    "You are a senior code-review memory. A test went red and a human fixed it. "
    "Distill ONE reusable lesson that would stop an AI coding agent from reintroducing "
    "this class of bug in a future session. Be general enough to transfer, specific "
    "enough to act on. Return ONLY a JSON object with exactly these keys: "
    "trigger (the situation that should surface this lesson), "
    "lesson (an imperative rule, one or two sentences). If the fix hinges on a specific "
    "comparison, name BOTH sides of it concretely with their exact field access — the field "
    "on the resource/object being filtered AND the field on the subject/user — so the rule "
    "can be applied without guessing (e.g. \"keep only rows where order['tenant_id'] == "
    "user['tenant_id']\"); never name only one side of the comparison. "
    "scope (where it applies: file / module / symbol / glob, free-form), "
    "severity (one of: low, med, high). "
    "The lesson MUST be a transferable rule, not a copy of the literal fixed code."
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
        model=model,
        temperature=0,
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
