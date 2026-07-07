"""A/B pattern spec — `money_rounding` (float/round dollars vs integer cents).

Same shape as the seed strings in harness/ab_runner.py: an under-specified TASK, a seeded
red-test + human fix (SEED_TEST_OUTPUT / SEED_DIFF) from which the lesson is distilled, the
CANONICAL_LESSON (verbatim fallback), and the RECALL_CONTEXT used to fetch it.

Floor (no memory)  -> accumulates money as float dollars -> rounding drift -> hidden test RED.
Ceiling (memory)   -> sums integer cents, /100 once       -> exact total     -> hidden test GREEN.
"""

# The under-specified task the coding agent sees. It says NOTHING about integer cents or
# float drift — the "money is integer cents" rule must come from memory.
TASK = (
    "Implement the function `cart_total(line_items)` for our checkout service.\n"
    "- `line_items` is a list of dicts. Each dict has `price_cents` (int, the unit price in "
    "cents) and `quantity` (int).\n"
    "- Return the total price of the cart in DOLLARS (e.g. 60.6 means $60.60).\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

# What arm B learns from FIRST (a prior red test + human fix), then recalls for TASK. This is
# where the domain convention (money is integer cents; never accumulate as float dollars)
# enters the system — the agent is never told it in the task.
SEED_TEST_OUTPUT = (
    "FAILED test_money_is_exact_to_the_cent - AssertionError: cart_total returned "
    "60.599999999999994, expected 60.6 (=6060 cents). Money accumulated as float dollars "
    "leaks residue.\n"
    "Root cause + fix: money must be handled as INTEGER CENTS. Dividing each line by 100 into "
    "a float running total (price_cents / 100) accumulates floating-point error. Sum the cents "
    "as integers first — total_cents = sum(item['price_cents'] * item['quantity']) — and divide "
    "by 100 exactly once at the very end."
)
SEED_DIFF = (
    "--- a/checkout.py\n+++ b/checkout.py\n"
    "-    total = 0.0\n"
    "-    for item in line_items:\n"
    "-        total += item['price_cents'] / 100 * item['quantity']\n"
    "-    return total\n"
    "+    total_cents = sum(item['price_cents'] * item['quantity'] for item in line_items)\n"
    "+    return total_cents / 100"
)

# The context arm B uses to RECALL the lesson (mirrors the coding situation).
RECALL_CONTEXT = (
    "implementing cart_total(line_items) that sums price_cents * quantity to return an "
    "invoice/cart total in dollars"
)

# Canonical form of the remembered convention (verbatim from the seeded human fix). Injected
# as the deterministic fallback so the on-camera proof cannot flake on a vague distillation.
CANONICAL_LESSON = (
    "Money is integer cents, never float dollars. In cart_total, do NOT accumulate "
    "item['price_cents'] / 100 into a float — that drifts (0.1 + 0.2 == 0.30000000000000004). "
    "Sum the cents as integers: total_cents = sum(item['price_cents'] * item['quantity'] for "
    "item in line_items), then divide by 100 exactly once at the boundary: return total_cents / 100."
)
