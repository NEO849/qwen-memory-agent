"""CEILING — the correct implementation with the remembered convention applied.

The project rule (recalled from memory): never trust a client-supplied page_size. Clamp it
server-side to MAX_PAGE_SIZE before slicing, and floor page/page_size to sane minimums.
Honest paging is unchanged; a hostile page_size can no longer drain the table.
"""

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


def list_items(db, query):
    items = db.all_items()
    page = max(1, int(query.get("page", 1)))
    page_size = int(query.get("page_size", DEFAULT_PAGE_SIZE))
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    start = (page - 1) * page_size
    return items[start:start + page_size]
