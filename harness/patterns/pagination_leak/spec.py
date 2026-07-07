"""A/B pattern spec — `pagination_leak` (server trusts client page_size vs clamps it).

Same shape as the seed strings in harness/ab_runner.py: an under-specified TASK, a seeded
red-test + human fix (SEED_TEST_OUTPUT / SEED_DIFF) from which the lesson is distilled, the
CANONICAL_LESSON (verbatim fallback), and the RECALL_CONTEXT used to fetch it.

Floor (no memory)  -> trusts client page_size -> whole table returned -> hidden test RED.
Ceiling (memory)   -> clamps to MAX_PAGE_SIZE  -> bounded page         -> hidden test GREEN.
"""

# The under-specified task the coding agent sees. It says NOTHING about clamping page_size or
# a maximum — the "never trust client page_size" rule must come from memory.
TASK = (
    "Implement the function `list_items(db, query)` for our catalog API.\n"
    "- `db.all_items()` returns the full list of items as a list of dicts.\n"
    "- `query` is a dict from the client request. It may contain `page` (1-based int) and "
    "`page_size` (int).\n"
    "Return the requested page of items.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

# What arm B learns from FIRST (a prior red test + human fix), then recalls for TASK. This is
# where the domain convention (clamp page_size server-side; a max page is 100) enters the
# system — the agent is never told it in the task.
SEED_TEST_OUTPUT = (
    "FAILED test_oversized_page_size_is_clamped - AssertionError: client asked for "
    "page_size=10000 and got 500 rows (expected <= 100). The server trusted client-supplied "
    "page_size.\n"
    "Root cause + fix: never trust a client-supplied page_size. A request with page_size=10000 "
    "returned the entire table (mass data extraction / resource exhaustion). Clamp page_size "
    "server-side to MAX_PAGE_SIZE = 100 before slicing: "
    "page_size = max(1, min(int(query.get('page_size', 20)), 100))."
)
SEED_DIFF = (
    "--- a/catalog.py\n+++ b/catalog.py\n"
    "     items = db.all_items()\n"
    "     page = query.get('page', 1)\n"
    "-    page_size = query.get('page_size', 20)\n"
    "+    page_size = max(1, min(int(query.get('page_size', 20)), MAX_PAGE_SIZE))  # MAX_PAGE_SIZE = 100\n"
    "     start = (page - 1) * page_size\n"
    "     return items[start:start + page_size]"
)

# The context arm B uses to RECALL the lesson (mirrors the coding situation).
RECALL_CONTEXT = (
    "implementing list_items(db, query) that returns a page of items from db.all_items() using "
    "client-supplied page and page_size"
)

# Canonical form of the remembered convention (verbatim from the seeded human fix). Injected
# as the deterministic fallback so the on-camera proof cannot flake on a vague distillation.
CANONICAL_LESSON = (
    "Never trust a client-supplied page_size. In list_items, clamp it server-side before "
    "slicing: page_size = max(1, min(int(query.get('page_size', 20)), MAX_PAGE_SIZE)) with "
    "MAX_PAGE_SIZE = 100. An unclamped page_size lets a client pull the entire table in one "
    "request (mass data extraction / resource exhaustion)."
)
