"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

Given "each line has price_cents and quantity, return the total in dollars", the obvious
move is to convert every line to dollars and add it into a running float. It reads clean
and passes a hand-check on round numbers — but it accumulates floating-point residue and
returns 60.599999999999994 instead of 60.60. Genuinely how money bugs ship; not
deliberately broken.
"""


def cart_total(line_items):
    total = 0.0
    for item in line_items:
        total += item["price_cents"] / 100 * item["quantity"]
    return total
