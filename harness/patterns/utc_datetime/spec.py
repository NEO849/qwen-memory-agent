"""A/B pattern spec — `utc_datetime` (naive local datetime vs timezone-aware UTC).

Same shape as harness/patterns/money_rounding/spec.py. An under-specified TASK, a seeded
red-test + human fix (SEED_TEST_OUTPUT / SEED_DIFF) the lesson is distilled from, a verbatim
CANONICAL_LESSON fallback, and the RECALL_CONTEXT used to fetch it.

Floor (no memory) -> compares fromisoformat(created_at) (aware) to datetime.now() (naive)
                     -> `TypeError: can't compare offset-naive and offset-aware datetimes` -> RED.
Ceiling (memory)  -> datetime.now(timezone.utc), aware throughout                          -> GREEN.
"""

# The under-specified task. It says NOTHING about timezones — that timestamps are tz-aware
# UTC is a project convention that must come from memory.
TASK = (
    "Implement the function `is_expired(token)` for our auth service.\n"
    "- `token` is a dict with `created_at` (an ISO-8601 timestamp string) and `ttl_seconds` (int).\n"
    "- Return True if the token has expired (i.e. now is later than created_at + ttl_seconds), "
    "else False.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

# What arm B learns from FIRST (a prior red test + human fix), then recalls for TASK. The
# domain convention (timestamps are timezone-aware UTC) enters here — never told in the task.
SEED_TEST_OUTPUT = (
    "FAILED test_expired_token_is_detected - TypeError: can't compare offset-naive and "
    "offset-aware datetimes. is_expired parsed created_at='2020-01-01T00:00:00+00:00' into an "
    "AWARE datetime but compared it against datetime.now() (NAIVE local time).\n"
    "Root cause + fix: all timestamps in this codebase are timezone-aware UTC. Never call the "
    "naive datetime.now(); use datetime.now(timezone.utc) so both sides of the comparison are "
    "aware."
)
SEED_DIFF = (
    "--- a/auth.py\n+++ b/auth.py\n"
    "-from datetime import datetime\n"
    "+from datetime import datetime, timezone, timedelta\n"
    "     created = datetime.fromisoformat(token['created_at'])\n"
    "-    return datetime.now() > created + timedelta(seconds=token['ttl_seconds'])\n"
    "+    return datetime.now(timezone.utc) > created + timedelta(seconds=token['ttl_seconds'])"
)

# The context arm B uses to RECALL the lesson (mirrors the coding situation).
RECALL_CONTEXT = (
    "implementing is_expired(token) that parses an ISO created_at timestamp and compares it to "
    "the current time to decide if a token/session has expired"
)

# Canonical form of the remembered convention (verbatim from the seeded human fix). Injected
# as the deterministic fallback so the proof cannot flake on a vague distillation.
CANONICAL_LESSON = (
    "Timestamps in this codebase are timezone-aware UTC. Never use the naive datetime.now() — "
    "comparing it to an aware datetime (e.g. datetime.fromisoformat('...+00:00')) raises "
    "'can't compare offset-naive and offset-aware datetimes'. Use datetime.now(timezone.utc) so "
    "both sides are aware."
)
