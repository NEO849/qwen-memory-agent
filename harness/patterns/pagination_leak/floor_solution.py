"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

Given "return the requested page using the client's page and page_size", the obvious code
reads both values straight off the request and slices. It looks correct and pages fine for
honest clients — but it trusts `page_size` unconditionally, so `page_size=10000` returns the
whole table. Genuinely how over-fetch/scraping bugs ship; not deliberately broken.
"""


def list_items(db, query):
    items = db.all_items()
    page = query.get("page", 1)
    page_size = query.get("page_size", 20)
    start = (page - 1) * page_size
    return items[start:start + page_size]
