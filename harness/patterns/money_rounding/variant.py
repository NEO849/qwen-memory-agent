"""UNSEEN variant of `money_rounding` — same convention (money is integer cents), a DIFFERENT
function surface than the seeded SEEN task. The memory was grounded on `cart_total`; here the
agent must TRANSFER the integer-cents rule to `invoice_total` with different dict keys.
"""

TASK = (
    "Implement the function `invoice_total(lines)` for our billing service.\n"
    "- `lines` is a list of dicts. Each has `unit_price_cents` (int) and `qty` (int).\n"
    "- Return the invoice total in DOLLARS (e.g. 60.6 means $60.60).\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

RECALL_CONTEXT = (
    "implementing invoice_total(lines) that sums unit_price_cents * qty across billing lines to "
    "return an invoice total in dollars"
)
