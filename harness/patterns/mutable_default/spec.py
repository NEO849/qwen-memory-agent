"""A/B pattern spec — `mutable_default` (shared mutable default arg vs None sentinel).

Same shape as harness/patterns/money_rounding/spec.py.

Floor (no memory) -> `def append_event(event, log=[])` -> the default list is created ONCE and
                     shared across calls -> state leaks between independent calls -> RED.
Ceiling (memory)  -> `log=None; if log is None: log = []` -> a fresh list per call            -> GREEN.
"""

# The under-specified task. A careful reader is nudged ("start a new empty log"), but the
# mutable-default trap is exactly the kind of Python convention that lives in memory.
TASK = (
    "Implement the function `append_event(event, log=None)` for our audit trail.\n"
    "- Append `event` to `log` and return `log`.\n"
    "- When called without a `log`, it should start a NEW empty log for that call.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

# What arm B learns from FIRST (a prior red test + human fix), then recalls for TASK.
SEED_TEST_OUTPUT = (
    "FAILED test_each_call_starts_fresh - AssertionError: the second independent call to "
    "append_event returned ['login', 'logout'], expected ['logout']. The function was defined "
    "as `def append_event(event, log=[])` — the default list is evaluated ONCE at definition "
    "time and shared across every call, so events leak between unrelated calls.\n"
    "Root cause + fix: never use a mutable default argument. Default to None and create a fresh "
    "list inside: `def append_event(event, log=None): if log is None: log = []`."
)
SEED_DIFF = (
    "--- a/audit.py\n+++ b/audit.py\n"
    "-def append_event(event, log=[]):\n"
    "+def append_event(event, log=None):\n"
    "+    if log is None:\n"
    "+        log = []\n"
    "     log.append(event)\n"
    "     return log"
)

# The context arm B uses to RECALL the lesson (mirrors the coding situation).
RECALL_CONTEXT = (
    "implementing append_event(event, log) that appends to a list argument and returns it, "
    "starting a new list when none is passed"
)

# Canonical form of the remembered convention (verbatim from the seeded human fix).
CANONICAL_LESSON = (
    "Never use a mutable default argument (e.g. `log=[]`): the default is created once at "
    "definition time and shared across all calls, so state leaks between independent calls. "
    "Default to None and create a fresh object inside the function: "
    "`def append_event(event, log=None): if log is None: log = []`."
)
