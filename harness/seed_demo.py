"""Realistic demo lessons — a coding memory worth showing.

15 diverse, real coding rules an agent would actually learn from red tests. Diverse on purpose:
keyword-free paraphrase queries (evaluation.evaluate) can't be solved by word-overlap alone, so
Recall@1 is meaningful (< 100%) and the semantic leg earns its lift. Also the demo deck's content.

Run:  python -m harness.seed_demo [path]   (defaults to the live ledger; embeds via real Qwen)
"""
from __future__ import annotations

import sys

from backend import config, ledger, memory

# (trigger, lesson, scope, severity)
SEED: list[tuple[str, str, str, str]] = [
    ("listing orders for a user",
     "Never call all_orders() and filter in Python — scope the query by tenant_id so one tenant can never read another tenant's rows.",
     "api/orders", "high"),
    ("parsing a user-supplied date",
     "Reject timestamps with no explicit timezone; only assume UTC after validation, never the server's local time.",
     "input/time", "med"),
    ("building a SQL query from request params",
     "Use parameterized queries; never string-format request values straight into SQL.",
     "db", "high"),
    ("accepting an uploaded file",
     "Validate the file type from its actual content bytes, not the filename extension a client can spoof.",
     "upload", "high"),
    ("retrying a failed payment charge",
     "Send an idempotency key so a retried charge can't double-bill the customer.",
     "payments", "high"),
    ("returning an error to the client",
     "Never echo raw exceptions or stack traces to the response — log them server-side and return a generic message.",
     "api/errors", "med"),
    ("caching a response that depends on the caller",
     "Put the user/tenant id in the cache key, or one user will be served another user's cached data.",
     "cache", "high"),
    ("comparing a secret, token or signature",
     "Use a constant-time comparison, not ==, so response timing can't leak the correct value byte by byte.",
     "crypto", "med"),
    ("opening a file or socket",
     "Close the handle in a finally block or context manager so it is released even when the body raises.",
     "resources", "low"),
    ("storing a user password",
     "Hash with bcrypt or argon2 and a per-user salt; never a fast unsalted digest like md5 or sha1.",
     "auth", "high"),
    ("running an external command",
     "Pass arguments as a list to subprocess; never shell=True with interpolated user input.",
     "shell", "high"),
    ("paginating a list endpoint",
     "Clamp the page size on the server so a client can't request the entire table in one call.",
     "api/paging", "med"),
    ("deserializing data from a request",
     "Never pickle.loads untrusted bytes; parse JSON against a schema instead.",
     "input/deser", "high"),
    ("verifying a JSON Web Token",
     "Pin the expected signing algorithm and reject 'none'; don't trust the alg field carried inside the token.",
     "auth/jwt", "high"),
    ("moving money between two balances",
     "Do the debit and the credit inside one database transaction so a crash can't leave the transfer half-applied.",
     "payments/ledger", "high"),
]


def seed(path: str | None = None, *, check_conflicts: bool = False) -> list[int]:
    ids = []
    for trigger, lesson, scope, severity in SEED:
        # store verbatim as a human lesson; skip contradiction check while bulk-seeding
        l = memory.add_note(f"{trigger}: {lesson}", scope=scope, severity=severity,
                            author="seed", check_conflicts=check_conflicts, path=path)
        # rewrite the trigger to the crisp short form (add_note derives it from the first line)
        ledger.edit_lesson(l["id"], trigger=trigger, lesson=lesson, path=path)
        ids.append(l["id"])
    return ids


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    ledger.init_db(target)
    made = seed(target)
    print(f"seeded {len(made)} lessons into {target}: ids {made[0]}..{made[-1]}")
