"""UNSEEN variant of `email_normalize` — same convention (normalize strip+lower before
comparing an email), a DIFFERENT function surface. The memory was grounded on a dict lookup
(`find_account`); here it must TRANSFER to a set membership check (`is_registered`).
"""

TASK = (
    "Implement the function `is_registered(emails, email)` for our signup service.\n"
    "- `emails` is a set of registered email addresses.\n"
    "- Return True if `email` is registered, else False.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

RECALL_CONTEXT = (
    "implementing is_registered(emails, email) that checks whether an email address is present "
    "in a set of registered emails"
)
