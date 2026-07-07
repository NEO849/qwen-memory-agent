"""Hidden ground-truth test for the `money_rounding` A/B pattern.

The coding agent NEVER sees this file. It is only told: "each line item carries a
`price_cents` integer and a `quantity`; return the cart total in dollars." The obvious
implementation converts each line to dollars (`price_cents / 100`) and accumulates in a
float — which silently drifts (0.1 + 0.2 == 0.30000000000000004). Money must be exact to
the cent; the drift leaks straight into the API/JSON and the customer is billed a value
that is off by a floating-point residue. Knowing that money is handled as INTEGER CENTS
(sum the cents, divide by 100 exactly once at the boundary) is precisely the kind of
project convention that lives in MEMORY — never stated in the task.

The assertion checks REAL correctness: the returned total must equal the exact value
derived from integer cents, with no floating-point residue.
"""
import importlib.util
import pathlib
from decimal import Decimal


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# A realistic 3-line cart: $10.10 + $20.20 + $30.30 = exactly $60.60.
# Accumulating those as float dollars drifts to 60.599999999999994.
LINE_ITEMS = [
    {"sku": "keyboard", "price_cents": 1010, "quantity": 1},
    {"sku": "mouse", "price_cents": 2020, "quantity": 1},
    {"sku": "monitor", "price_cents": 3030, "quantity": 1},
]


def _expected_dollars(items):
    """Ground truth via integer cents — the only correct way to total money."""
    total_cents = sum(item["price_cents"] * item["quantity"] for item in items)
    return total_cents, total_cents / 100


def test_money_is_exact_to_the_cent():
    sol = _load_solution()
    expected_cents, expected_dollars = _expected_dollars(LINE_ITEMS)

    got = sol.cart_total(LINE_ITEMS)

    # 1) No floating-point residue: the total must equal the exact cent-derived value.
    assert got == expected_dollars, (
        f"rounding drift: cart_total returned {got!r}, expected {expected_dollars!r} "
        f"(={expected_cents} cents). Money accumulated as float dollars leaks residue."
    )
    # 2) Decimal-exact — catches the 60.599999999999994 tail even if '==' were fuzzy.
    assert Decimal(str(got)) == Decimal(expected_cents) / 100, (
        f"cart_total returned a non-cent-exact value {got!r}"
    )


def test_quantities_are_respected():
    """Guards against over-correction: the fix must still multiply by quantity."""
    sol = _load_solution()
    items = [{"sku": "pen", "price_cents": 150, "quantity": 4}]  # $1.50 x4 = $6.00
    got = sol.cart_total(items)
    assert got == 6.0, f"expected 6.0 for 4x $1.50, got {got!r}"
