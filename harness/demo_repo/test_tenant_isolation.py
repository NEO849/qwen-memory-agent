"""Hidden ground-truth test for the A/B harness.

The coding agent NEVER sees this file, is NEVER told that orders carry a tenant_id, and is
NEVER told the user has a tenant_id. It only sees: "db.all_orders() returns every order,
return the orders to display for this user." The obvious implementation is
`return db.all_orders()` — which leaks every tenant's rows. Knowing that orders are
tenant-scoped (and by which field) is exactly the kind of project convention that lives
in MEMORY. This test is the ground truth that judges the result.

The assertions distinguish the two failure modes honestly:
  * cross-tenant leak  -> the result contains another tenant's rows (superset)
  * over-restriction   -> the result drops legitimate rows (wrong/empty)
"""
import importlib.util
import pathlib


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeDB:
    """Data-access object exposing the whole shared orders table."""

    def __init__(self, orders):
        self._orders = orders

    def all_orders(self):
        return list(self._orders)


# Shared table: two tenants' orders live side by side.
ORDERS = [
    {"id": 1, "tenant_id": "acme", "item": "widget"},
    {"id": 2, "tenant_id": "acme", "item": "gadget"},
    {"id": 3, "tenant_id": "globex", "item": "confidential-merger-doc"},
]


def test_tenant_isolation():
    sol = _load_solution()
    db = FakeDB(ORDERS)
    user = {"id": 10, "tenant_id": "acme"}
    rows = sol.get_orders(db, user)
    seen_tenants = {r["tenant_id"] for r in rows}
    leaked = seen_tenants - {"acme"}
    assert not leaked, f"cross-tenant leak: user from 'acme' also saw {sorted(leaked)}"
    assert len(rows) == 2, f"over-restriction: expected 2 acme orders, got {len(rows)}"
