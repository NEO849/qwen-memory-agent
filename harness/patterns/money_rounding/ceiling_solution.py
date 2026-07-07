"""CEILING — the correct implementation with the remembered convention applied.

The project rule (recalled from memory): money is INTEGER CENTS. Sum the cents as ints,
then divide by 100 exactly once at the boundary. `sum(price_cents * quantity)` is exact,
and `total_cents / 100` yields the nearest double to the true dollar value with no
per-item residue.
"""


def cart_total(line_items):
    total_cents = sum(item["price_cents"] * item["quantity"] for item in line_items)
    return total_cents / 100
