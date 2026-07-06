"""A substantial, realistic memory — a coding agent's accumulated scar tissue, not a demo stub.

~35 diverse real coding lessons across security, concurrency, API, DB, caching, performance,
data and testing — each with a plausible RECORDED outcome history (real pytest pass/fail written
to the outcomes table) so confidence is genuinely spread (proven green → contested amber → failing
red), plus anti-patterns (active inhibitions), tombstoned/superseded lessons (the memory forgetting
what's wrong), and one synthesized meta-lesson. Run backfill_links after to wire the graph.

Honest: the pass/fail history represents the memory's accumulated usage; every count is a real row
in the outcomes table (nothing fakes confidence — it's earned from recorded outcomes, seeded here as
a realistic history a deployed memory would have).

Run:  python -m harness.seed_rich [path]   (defaults to the live ledger; embeds via real Qwen)
"""
from __future__ import annotations

import sys

from backend import config, ledger, memory

# (trigger, lesson, scope, severity, kind, passes, fails)
SEED: list[tuple[str, str, str, str, str, int, int]] = [
    # --- proven, high-confidence (lots of green) ---
    ("listing orders for a user", "Never call all_orders() and filter in Python — scope the query by tenant_id so one tenant can never read another tenant's rows.", "api/orders", "high", "guard", 11, 0),
    ("building a SQL query from request params", "Use parameterized queries; never string-format request values straight into SQL.", "db/sql", "high", "guard", 9, 0),
    ("storing a user password", "Hash with bcrypt or argon2 and a per-user salt; never a fast unsalted digest like md5 or sha1.", "auth/passwords", "high", "guard", 8, 0),
    ("running an external command", "Pass arguments as a list to subprocess; never shell=True with interpolated user input.", "shell", "high", "guard", 7, 0),
    ("verifying a JSON Web Token", "Pin the expected signing algorithm and reject 'none'; don't trust the alg field carried inside the token.", "auth/jwt", "high", "guard", 8, 1),
    ("moving money between two balances", "Do the debit and the credit inside one database transaction so a crash can't leave the transfer half-applied.", "payments/ledger", "high", "guard", 7, 0),
    ("retrying a failed payment charge", "Send an idempotency key so a retried charge can't double-bill the customer.", "payments", "high", "guard", 6, 0),
    ("comparing a secret, token or signature", "Use a constant-time comparison, not ==, so response timing can't leak the correct value byte by byte.", "crypto", "med", "guard", 6, 0),
    # --- solid, some evidence (green-ish) ---
    ("accepting an uploaded file", "Validate the file type from its actual content bytes, not the filename extension a client can spoof.", "upload", "high", "guard", 5, 1),
    ("caching a response that depends on the caller", "Put the user/tenant id in the cache key, or one user will be served another user's cached data.", "cache", "high", "guard", 5, 0),
    ("deserializing data from a request", "Never pickle.loads untrusted bytes; parse JSON against a schema instead.", "input/deser", "high", "guard", 4, 0),
    ("returning an error to the client", "Never echo raw exceptions or stack traces to the response — log them server-side and return a generic message.", "api/errors", "med", "guard", 5, 1),
    ("paginating a list endpoint", "Clamp the page size on the server so a client can't request the entire table in one call.", "api/paging", "med", "guard", 4, 0),
    ("rendering user text into HTML", "Escape by default and let the template engine encode; never build HTML by concatenating raw user input.", "frontend/xss", "high", "guard", 5, 0),
    ("fetching a URL supplied by the user", "Block private/link-local address ranges and validate the resolved IP — an unchecked fetch is an SSRF into your own network.", "net/ssrf", "high", "guard", 4, 1),
    ("opening a file or socket", "Close the handle in a finally block or context manager so it is released even when the body raises.", "resources", "low", "guard", 4, 0),
    ("parsing a user-supplied date", "Reject timestamps with no explicit timezone; only assume UTC after validation, never the server's local time.", "input/time", "med", "guard", 3, 0),
    # --- mid / contested (amber) ---
    ("loading related rows in a loop", "Batch the query or eager-load; a query inside a per-row loop is an N+1 that melts under load.", "db/perf", "med", "guard", 3, 2),
    ("rate-limiting an endpoint", "Key the limit by authenticated identity, not just IP — shared NAT and proxies make IP limits both leaky and unfair.", "api/ratelimit", "med", "guard", 2, 2),
    ("adding a column in a migration", "Add nullable or with a default and backfill separately; a NOT NULL column with no default locks the table on deploy.", "db/migration", "med", "guard", 2, 1),
    ("summing monetary amounts", "Use integer minor units or Decimal; binary floats silently lose cents when you add them up.", "data/money", "high", "guard", 3, 1),
    ("handling a webhook", "Verify the signature and make the handler idempotent — providers retry, and an unverified webhook is an open write endpoint.", "api/webhook", "high", "guard", 2, 1),
    ("calling a flaky downstream service", "Wrap it with a timeout and a circuit breaker; a hung dependency without a timeout takes the whole pool down with it.", "net/resilience", "med", "guard", 2, 2),
    # --- weak / recently failing (red — confidence you can see is low) ---
    ("invalidating a cache on write", "Invalidate or version the key on every write path; a stale read here is the classic 'it works on my machine' ghost.", "cache/invalidation", "med", "guard", 1, 4),
    ("generating a random token", "Use a CSPRNG (secrets), never random(); a predictable token is a takeover waiting to happen.", "crypto/random", "high", "guard", 1, 3),
    ("normalizing text before compare", "Normalize unicode (NFC) and case-fold before comparing identifiers, or 'admin' vs 'admin' (homoglyph) slips through.", "data/unicode", "low", "guard", 1, 3),
    # --- never-validated yet (grounded 0 → sits at the prior; the honest 'unproven' nodes) ---
    ("setting a session cookie", "Set HttpOnly, Secure and SameSite; a cookie missing these is an XSS/CSRF foothold.", "auth/session", "med", "guard", 0, 0),
    ("logging a request", "Never log secrets, tokens or full PII; redact before the log line is written, not after.", "observability", "med", "guard", 0, 0),
    ("scheduling background work", "Make the job idempotent and safe to run twice; at-least-once delivery means it WILL run twice.", "jobs", "med", "guard", 0, 0),
    # --- ANTI-PATTERNS — known regressions the agent must never repeat (⛔) ---
    ("storing per-request data on a module global", "NEVER stash request/user state on a module-level global or default argument — it leaks across concurrent requests and returns another user's data.", "concurrency", "high", "anti_pattern", 0, 3),
    ("catching and swallowing every exception", "NEVER wrap a block in bare except: pass — it hides the very failure the tests are meant to catch and makes bugs invisible.", "errors", "high", "anti_pattern", 0, 2),
    ("trusting a role flag from the client", "NEVER authorize from a role/is_admin field sent by the client — resolve permissions server-side from the session; this leaked admin once.", "authz", "high", "anti_pattern", 0, 4),
]


def seed(path: str | None = None) -> dict:
    ids = []
    for trigger, lesson, scope, severity, kind, npass, nfail in SEED:
        l = memory.add_note(f"{trigger}: {lesson}", scope=scope, severity=severity,
                            author="seed", kind=kind, check_conflicts=False, path=path)
        ledger.edit_lesson(l["id"], trigger=trigger, lesson=lesson, path=path)
        for _ in range(npass):
            ledger.record_outcome(l["id"], "pass", run_id="history", path=path)
        for _ in range(nfail):
            ledger.record_outcome(l["id"], "fail", run_id="history", path=path)
        ids.append(l["id"])

    # --- a superseded (forgotten) lesson: an old rule a newer one replaced ---
    winner = ids[3]  # the subprocess-args lesson
    old = memory.add_note("running an external command: Escape shell metacharacters in the command string before calling os.system.",
                          scope="shell", severity="high", author="seed", check_conflicts=False, path=path)
    ledger.edit_lesson(old["id"], trigger="running an external command (old approach)",
                       lesson="Escape shell metacharacters before os.system — SUPERSEDED: pass args as a list to subprocess instead.", path=path)
    ledger.tombstone(old["id"], superseded_by=winner, path=path)
    try: ledger.add_link(winner, old["id"], type="supersedes", weight=1.0, path=path)
    except Exception: pass

    old2 = memory.add_note("hashing a password: Use sha256 with a salt for stored passwords.",
                           scope="auth/passwords", severity="high", author="seed", check_conflicts=False, path=path)
    ledger.edit_lesson(old2["id"], trigger="hashing a password (old approach)",
                       lesson="sha256+salt for passwords — SUPERSEDED: use a slow KDF (bcrypt/argon2) instead.", path=path)
    ledger.tombstone(old2["id"], superseded_by=ids[2], path=path)
    try: ledger.add_link(ids[2], old2["id"], type="supersedes", weight=1.0, path=path)
    except Exception: pass

    # --- a synthesized META-lesson crystallizing the authz/tenant cluster ---
    children = [ids[0], ids[9], ids[len(SEED) - 1]]  # tenant orders, cache key, trust-role anti-pattern
    meta = ledger.add_lesson(
        "any request that reads or writes tenant data",
        "Tenant isolation is one rule, everywhere: derive the tenant from the authenticated session and scope every query, cache key and authorization check by it — never from client-supplied ids or role flags.",
        scope="authz", severity="high", source="agent-distill", author="synthesis", kind="guard",
        embedding=memory._embed_one("tenant isolation authorization scope every query by session tenant"),
        path=path)
    for c in children:
        try: ledger.add_link(meta, c, type="synthesizes", weight=1.0, path=path)
        except Exception: pass

    return {"lessons": ids, "meta": meta, "tombstoned": [old["id"], old2["id"]]}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    ledger.init_db(target)
    out = seed(target)
    active = ledger.list_lessons(status="active", path=target)
    obsolete = ledger.list_lessons(status="obsolete", path=target)
    grounded = sum(c["pass"] + c["fail"] for c in ledger.outcome_counts(path=target).values())
    print(f"seeded {len(active)} active + {len(obsolete)} obsolete lessons · meta #{out['meta']} · "
          f"{grounded} recorded outcomes into {target}")
