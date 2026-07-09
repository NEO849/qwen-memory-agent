"""UNSEEN variant of `pagination_leak` — same convention (clamp the client-supplied page
length to MAX_PAGE_SIZE = 100 server-side), a DIFFERENT function surface. The memory was
grounded on `list_items(db, query)` with page/page_size; here it must TRANSFER to
`fetch_records(store, params)` with offset/limit.
"""

TASK = (
    "Implement the function `fetch_records(store, params)` for our reporting API.\n"
    "- `store.rows()` returns the full list of records as a list of dicts.\n"
    "- `params` is a dict from the client request. It may contain `offset` (0-based int) and "
    "`limit` (int).\n"
    "Return the requested slice of records.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

RECALL_CONTEXT = (
    "implementing fetch_records(store, params) that returns a slice of store.rows() using a "
    "client-supplied offset and limit"
)
