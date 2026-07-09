"""UNSEEN variant of `mutable_default` — same convention (never use a mutable default argument;
default to None and create a fresh object inside), a DIFFERENT container. The memory was
grounded on a list (`append_event`); here it must TRANSFER to a dict (`register`).
"""

TASK = (
    "Implement the function `register(key, value, store=None)` for our registry.\n"
    "- Set `store[key] = value` and return `store`.\n"
    "- When called without a `store`, it should start a NEW empty dict for that call.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)

RECALL_CONTEXT = (
    "implementing register(key, value, store) that assigns into a dict argument and returns it, "
    "starting a new dict when none is passed"
)
