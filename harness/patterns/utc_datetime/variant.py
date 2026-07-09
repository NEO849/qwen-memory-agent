"""UNSEEN variant of `utc_datetime` — same convention (timestamps are timezone-aware UTC; use
datetime.now(timezone.utc), never the naive datetime.now()), a DIFFERENT function surface. The
memory was grounded on `is_expired(token)`; here it must TRANSFER to `seconds_until(deadline)`.
"""

TASK = (
    "Implement the function `seconds_until(deadline)` for our scheduler.\n"
    "- `deadline` is an ISO-8601 timestamp string.\n"
    "- Return the number of seconds from now until the deadline (a float; negative if the "
    "deadline is already in the past).\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

RECALL_CONTEXT = (
    "implementing seconds_until(deadline) that parses an ISO deadline timestamp and subtracts "
    "the current time to return the seconds remaining"
)
