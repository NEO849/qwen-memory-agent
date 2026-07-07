"""Realistic demo lessons — a coding memory worth showing.

35 diverse, real coding rules an agent would actually learn from red tests, organised into
natural scope clusters (auth, auth/jwt, http, db, input, api, payments …) so that:
  * keyword-free paraphrase queries (evaluation.evaluate) can't be solved by word-overlap alone,
    so Recall@1 is meaningful (< 100%) and the semantic leg earns its lift;
  * cosine-nearest 'related' links (backfill_links) form visible constellations on the 3D globe;
  * scope clusters of >= 3 give ExpeL crystallization (synthesis) something real to distil.

`enrich()` additionally seeds the *shape* of a mature memory — all node/edge types the globe can
render — WITHOUT faking any confidence:
  * anti-patterns  -> dead-end '⛔ DO NOT' nodes (dark red)
  * a superseded pair -> a real belief-revision (grey 'forgotten' node + red 'supersedes' edge)
  * 'related' edges from real embedding cosine (backfill)
  * 'synthesizes' meta-lessons from real Qwen synthesis, which start UNPROVEN (0.5 prior) and must
    earn confidence from real tests like any other lesson.

Run:  python -m harness.seed_demo [path]      # seed 35 guards + enrich (needs real Qwen for embeddings)
"""
from __future__ import annotations

import sys

from backend import config, ledger, memory

# (trigger, lesson, scope, severity)
SEED: list[tuple[str, str, str, str]] = [
    # --- tenant / authorization ---
    ("listing orders for a user",
     "Never call all_orders() and filter in Python — scope the query by tenant_id so one tenant can never read another tenant's rows.",
     "api/orders", "high"),
    ("checking access to an object by id",
     "Verify the caller actually owns the id from the URL — a valid session is not permission for that specific row (IDOR).",
     "authz", "high"),
    ("binding a request body onto a model",
     "Whitelist which fields a request may set; never bind request JSON straight onto the record, or a user can set is_admin themselves (mass assignment).",
     "authz", "high"),
    ("trusting a caller-supplied identity header",
     "Derive the user from the verified session, never from a client-sent header like X-User — the client controls it.",
     "authz", "high"),
    # --- auth ---
    ("storing a user password",
     "Hash with bcrypt or argon2 and a per-user salt; never a fast unsalted digest like md5 or sha1.",
     "auth", "high"),
    ("issuing a session on login",
     "Regenerate the session id on login and on any privilege change, so a fixed pre-login session can't be replayed (session fixation).",
     "auth", "high"),
    ("handling a state-changing POST",
     "Require a CSRF token or SameSite cookies on every state-changing request; a GET must never mutate state.",
     "auth", "high"),
    ("accepting repeated login attempts",
     "Rate-limit and lock login attempts per account and per IP so credentials can't be brute-forced.",
     "auth", "med"),
    # --- JWT ---
    ("verifying a JSON Web Token",
     "Pin the expected signing algorithm and reject 'none'; don't trust the alg field carried inside the token.",
     "auth/jwt", "high"),
    ("accepting a JWT on a request",
     "Check the token's exp and nbf claims; a token that never expires is as dangerous as no auth at all.",
     "auth/jwt", "high"),
    ("validating a JWT for this service",
     "Verify the aud and iss claims match this service; never accept a valid token minted for a different audience.",
     "auth/jwt", "high"),
    # --- input validation ---
    ("parsing a user-supplied date",
     "Reject timestamps with no explicit timezone; only assume UTC after validation, never the server's local time.",
     "input/time", "med"),
    ("building a SQL query from request params",
     "Use parameterized queries; never string-format request values straight into SQL.",
     "input/sql", "high"),
    ("accepting an uploaded file",
     "Validate the file type from its actual content bytes, not the filename extension a client can spoof.",
     "input/upload", "high"),
    ("opening a path from user input",
     "Canonicalize the path and confine it to its base directory before opening; reject '..' so a client can't traverse out.",
     "input/path", "high"),
    ("rendering a value back to output",
     "Escape output for the exact sink it lands in — HTML, SQL, shell, a header — a value safe in one context injects in another.",
     "input/output", "high"),
    ("deserializing data from a request",
     "Never pickle.loads untrusted bytes; parse JSON against a schema instead.",
     "input/deser", "high"),
    # --- outbound HTTP ---
    ("fetching a user-supplied URL",
     "Validate and allowlist any URL before the server fetches it, or you have an SSRF into the internal network.",
     "http", "high"),
    ("redirecting after an action",
     "Only redirect to a relative path or an allowlisted host; an open redirect is a phishing and token-theft primitive.",
     "http", "med"),
    ("calling an external service",
     "Set a timeout on every outbound request; a hung upstream must never pin your worker forever.",
     "http", "med"),
    # --- database / concurrency / perf ---
    ("reading then writing the same row",
     "Take a row lock (SELECT … FOR UPDATE) before a read-modify-write, or two concurrent requests silently lose an update.",
     "db", "high"),
    ("querying inside a loop over results",
     "Never run a query per row (N+1); batch it with a join or a single IN-clause.",
     "db", "med"),
    ("changing the database schema",
     "Ship a forward-only migration for every schema change; never edit a migration that already ran in production.",
     "db", "med"),
    # --- caching / resources ---
    ("caching a response that depends on the caller",
     "Put the user or tenant id in the cache key, or one user is served another user's cached data.",
     "cache", "high"),
    ("opening a file or socket",
     "Close the handle in a finally block or context manager so it is released even when the body raises.",
     "resources", "low"),
    ("comparing a secret, token or signature",
     "Use a constant-time comparison, not ==, so response timing can't leak the correct value byte by byte.",
     "crypto", "med"),
    # --- payments ---
    ("retrying a failed payment charge",
     "Send an idempotency key so a retried charge can't double-bill the customer.",
     "payments", "high"),
    ("moving money between two balances",
     "Do the debit and the credit inside one database transaction so a crash can't leave the transfer half-applied.",
     "payments", "high"),
    # --- API hygiene ---
    ("paginating a list endpoint",
     "Clamp the page size on the server so a client can't request the entire table in one call.",
     "api", "med"),
    ("accepting a request body",
     "Set a maximum body size; an unbounded upload is a cheap memory-exhaustion denial of service.",
     "api", "med"),
    ("returning an error to the client",
     "Never echo raw exceptions or stack traces to the response — log them server-side and return a generic message.",
     "api", "med"),
    # --- process / ops ---
    ("running an external command",
     "Pass arguments as a list to subprocess; never shell=True with interpolated user input.",
     "shell", "high"),
    ("reading a secret in code",
     "Read secrets from the environment or a vault, never commit them; a key in git history is a leaked key.",
     "secrets", "high"),
    ("logging a request",
     "Never log secrets, tokens or full PII; logs get shipped to places with weaker access control than the database.",
     "logging", "med"),
    ("returning JSON to the browser",
     "Send correct security headers (Content-Type, X-Content-Type-Options: nosniff); don't let the browser sniff a type.",
     "api", "low"),
    # --- async / concurrency ---
    ("holding a lock across an await",
     "Never hold an async lock across an await that does I/O; release it first or you serialize the whole service.",
     "async", "med"),
    ("giving a function a default argument",
     "Never use a mutable default argument ([] or {}); it is shared across calls — default to None and create inside.",
     "async", "med"),
    ("starting a background task",
     "Await or keep a reference to every background task; a fire-and-forget coroutine swallows its exception silently.",
     "async", "med"),
    # --- observability ---
    ("writing a log line",
     "Log structured key/values with a correlation id, not string concatenation, so a request is traceable across services.",
     "observability", "med"),
    ("catching an exception",
     "Log the exception with its stack server-side before returning; a swallowed error is an invisible outage.",
     "observability", "med"),
    ("calling an external dependency",
     "Wrap external calls in a counter and a timer (RED metrics) so latency and error spikes surface before users complain.",
     "observability", "low"),
    # --- testing ---
    ("fixing a reported bug",
     "Add a regression test that fails before the fix and passes after; a fix without a test invites the same bug back.",
     "testing", "high"),
    ("testing code that reads the clock or random",
     "Inject the clock and the RNG so tests are deterministic; never assert against the real wall clock.",
     "testing", "med"),
    ("mocking an external service in a test",
     "Assert the call contract (arguments, count), not only the return value, or a wrong call passes silently.",
     "testing", "med"),
    # --- web / frontend security ---
    ("setting a session cookie",
     "Set HttpOnly, Secure and SameSite on session cookies so script can't read them and they don't leak cross-site.",
     "web", "high"),
    ("reflecting user input into a page",
     "Escape output or use safe templating; never build HTML by concatenating request data (XSS).",
     "web", "high"),
    ("configuring CORS",
     "Never reflect the request Origin into Access-Control-Allow-Origin with credentials; allowlist exact origins.",
     "web", "high"),
    # --- config / rollout ---
    ("reading required configuration",
     "Fail fast at startup with a clear message if a required config or secret is missing — don't 500 on the first request.",
     "config", "med"),
    ("adding a feature flag",
     "Default a new flag to off and roll out gradually; a default-on flag ships untested behaviour to everyone at once.",
     "config", "low"),
]

# Anti-patterns: dead-end memories (known past regressions) rendered as active ⛔ DO-NOT inhibitions.
ANTI: list[tuple[str, str, str, str]] = [
    ("making an HTTPS call work quickly",
     "Don't disable TLS certificate verification to 'make it work' — it silently removes the whole transport-security guarantee.",
     "http", "high"),
    ("handling a write that might fail",
     "Don't wrap a failing write in a bare except: pass — it reports data loss as success and hides the bug forever.",
     "reliability", "high"),
    ("filtering a list by the current user",
     "Don't fetch every row and filter in the app after the query — one missed check leaks other tenants' rows; scope it in SQL.",
     "authz", "high"),
]

# A real belief-revision: a naive rule a later refactor proved wrong, replaced by the correct one.
SUPERSEDED_OLD = ("formatting a money amount",
                  "Format money as a float rounded to two decimals for display and arithmetic.",
                  "payments", "med")
SUPERSEDED_NEW = ("representing a money amount",
                  "Store and compute money in integer minor units (cents); binary floats can't represent 0.10 and drift over sums.",
                  "payments", "high")

# Typical coding situations used for Hebbian consolidation — each co-recalls a cluster of related
# lessons, so the synapses that genuinely co-fire grow (real usage, not hand-set weights).
CONSOLIDATION_CONTEXTS = [
    "building a login and session flow with password storage and tokens",
    "writing an endpoint that returns a user's records filtered by tenant",
    "validating and parsing untrusted request input before using it",
    "charging a customer and moving money between account balances",
    "writing async handlers that call external services with locks and timeouts",
    "rendering user-supplied content into an HTML page and setting cookies",
    "adding logging, metrics and tests around a new feature",
    "paginating and caching a list endpoint safely",
]


def _add(trigger: str, lesson: str, scope: str, severity: str, *, kind: str = "guard",
         path: str | None = None) -> int:
    l = memory.add_note(f"{trigger}: {lesson}", scope=scope, severity=severity,
                        author="seed", kind=kind, check_conflicts=False, path=path)
    ledger.edit_lesson(l["id"], trigger=trigger, lesson=lesson, path=path)
    return l["id"]


def seed(path: str | None = None, *, check_conflicts: bool = False) -> list[int]:
    """Seed the 35 guard lessons verbatim (the demo deck + evaluation gold)."""
    return [_add(t, le, sc, se, path=path) for (t, le, sc, se) in SEED]


def enrich(path: str | None = None) -> dict:
    """Give the memory the *shape* of a mature one — every node/edge type — honestly.

    Adds anti-patterns, one real superseded pair, cosine 'related' links, and (best-effort) one or
    two Qwen syntheses. No confidence is faked: anti-patterns are inhibitions, the superseded node
    is greyed, syntheses start at the 0.5 prior and must earn confidence from real tests.
    """
    from harness import backfill_links

    stats = {"anti": 0, "superseded": 0, "syntheses": 0}

    # anti-patterns (⛔ DO NOT)
    for (t, le, sc, se) in ANTI:
        _add(t, le, sc, se, kind="anti_pattern", path=path)
        stats["anti"] += 1

    # a real belief-revision: seed the retired rule, then the correct one, then tombstone the old
    old_id = _add(*SUPERSEDED_OLD, path=path)
    new_id = _add(*SUPERSEDED_NEW, path=path)
    ledger.tombstone(old_id, superseded_by=new_id, path=path)
    stats["superseded"] = 1

    # 'related' constellations from real embedding cosine (denser: more/lower-threshold edges)
    backfill_links.backfill(path=path, threshold=0.52, top_k=5)

    # ExpeL crystallization — real Qwen synthesis, accept up to four, best-effort
    try:
        from backend import synthesis
        proposals = synthesis.propose_synthesis(path=path, min_group=3).get("proposals", [])
        for p in proposals[:4]:
            try:
                synthesis.accept(p, path=path)
                stats["syntheses"] += 1
            except Exception:
                pass
    except Exception:
        pass

    # Hebbian consolidation — real recalls over typical coding contexts grow the synapses that
    # actually co-fire (varied edge weights = a used, brain-like graph). Best-effort (needs Qwen).
    try:
        from backend import memory
        for ctx in CONSOLIDATION_CONTEXTS:
            memory.recall(ctx, k=5, path=path)   # RG_HEBBIAN wires the co-recalled lessons
    except Exception:
        pass

    stats["links"] = len(ledger.list_links(path=path))
    return stats


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else config.LEDGER_PATH
    ledger.init_db(target)
    made = seed(target)
    ex = enrich(target)
    print(f"seeded {len(made)} guard lessons into {target}: ids {made[0]}..{made[-1]}")
    print(f"enriched: {ex}")
