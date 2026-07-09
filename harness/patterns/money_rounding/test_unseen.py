"""Hidden test for the UNSEEN `money_rounding` variant — `invoice_total(lines)`.

Same convention as the SEEN task (money is integer cents; sum cents, divide by 100 once), a
different function + dict keys. Float accumulation drifts to 60.599999999999994.
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


LINES = [
    {"sku": "a", "unit_price_cents": 1010, "qty": 1},
    {"sku": "b", "unit_price_cents": 2020, "qty": 1},
    {"sku": "c", "unit_price_cents": 3030, "qty": 1},
]


def test_invoice_exact_to_the_cent():
    sol = _load_solution()
    total_cents = sum(l["unit_price_cents"] * l["qty"] for l in LINES)
    got = sol.invoice_total(LINES)
    assert got == total_cents / 100, (
        f"rounding drift: invoice_total returned {got!r}, expected {total_cents/100!r}")
    assert Decimal(str(got)) == Decimal(total_cents) / 100, f"non-cent-exact value {got!r}"


def test_quantities_respected():
    sol = _load_solution()
    got = sol.invoice_total([{"unit_price_cents": 150, "qty": 4}])  # $1.50 x4 = $6.00
    assert got == 6.0, f"expected 6.0 for 4x $1.50, got {got!r}"
