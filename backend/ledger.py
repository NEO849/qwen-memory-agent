"""SQLite ledger — the memory store of Regress-Guard.

Holds distilled lessons + their Beta(alpha, beta) confidence and an append-only
outcome audit. Design notes (concurrency = the "professor" part):

  * journal_mode=WAL + busy_timeout  → readers never block the writer and vice versa;
    each reader sees a consistent snapshot of the last committed state.
  * every write runs as  BEGIN IMMEDIATE ... COMMIT  → SQLite serializes writers,
    giving a total order over (human console, agent record, confidence update).
  * confidence updates are atomic in-SQL increments (UPDATE ... SET alpha = alpha + ?)
    → no Python read-modify-write, so concurrent outcomes can't lose an update.
  * recall reads the whole candidate set in ONE SELECT (the snapshot); scoring then
    runs purely in memory. The snapshot read is the recall's linearization point.

LEDGER_PATH is a parameter (not a global) so the A/B harness can point at a throwaway
DB — the hard isolation boundary between the interactive layer and the causal proof.
"""
from __future__ import annotations

import sqlite3
from array import array
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from . import config

SEVERITIES = ("low", "med", "high")
SOURCES = ("agent-distill", "human", "human-distill", "import")
KINDS = ("guard", "anti_pattern")   # guard = "do this"; anti_pattern = "never do this again" (dead-end memory)
SCHEMA_VERSION = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pack(vec: list[float] | None) -> bytes | None:
    return array("f", vec).tobytes() if vec else None


def _unpack(blob: bytes | None) -> list[float] | None:
    if not blob:
        return None
    a = array("f")
    a.frombytes(blob)
    return list(a)


@contextmanager
def _connect(path: str | None = None) -> Iterator[sqlite3.Connection]:
    p = str(path or config.LEDGER_PATH)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


DDL = """
CREATE TABLE IF NOT EXISTS lessons (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger      TEXT NOT NULL,
    lesson       TEXT NOT NULL,
    scope        TEXT NOT NULL DEFAULT '',
    severity     TEXT NOT NULL DEFAULT 'med',
    embedding    BLOB,
    alpha        REAL NOT NULL DEFAULT 1.0,
    beta         REAL NOT NULL DEFAULT 1.0,
    status       TEXT NOT NULL DEFAULT 'active',   -- active | obsolete
    superseded_by INTEGER,
    source       TEXT NOT NULL DEFAULT 'agent-distill',
    pinned       INTEGER NOT NULL DEFAULT 0,
    author       TEXT,
    note_raw     TEXT,
    rev          INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outcomes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id),
    run_id     TEXT,
    injected   INTEGER NOT NULL DEFAULT 0,
    result     TEXT NOT NULL,                      -- pass | fail
    ts         TEXT NOT NULL
);
"""


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent, in-place upgrade of an existing ledger (init_db is CREATE-IF-NOT-EXISTS
    only, so new columns/tables would never reach a DB that predates them). Each ALTER is
    guarded by introspection → re-running is a no-op; ADD COLUMN with a DEFAULT is atomic,
    non-locking and preserves every existing row's data."""
    cols = _columns(conn, "lessons")
    if "kind" not in cols:
        conn.execute("ALTER TABLE lessons ADD COLUMN kind TEXT NOT NULL DEFAULT 'guard'")
    if "recall_count" not in cols:
        conn.execute("ALTER TABLE lessons ADD COLUMN recall_count INTEGER NOT NULL DEFAULT 0")
    if "last_recalled_at" not in cols:
        conn.execute("ALTER TABLE lessons ADD COLUMN last_recalled_at TEXT")
    if "merge_count" not in cols:   # dedup salience — NOT confidence (confidence stays test-grounded)
        conn.execute("ALTER TABLE lessons ADD COLUMN merge_count INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS links (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id    INTEGER NOT NULL REFERENCES lessons(id),
            to_id      INTEGER NOT NULL REFERENCES lessons(id),
            type       TEXT NOT NULL DEFAULT 'related',   -- related | supersedes | synthesizes
            weight     REAL NOT NULL DEFAULT 1.0,
            created_at TEXT NOT NULL
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_links_from ON links(from_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_links_to   ON links(to_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS link_rejections (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id    INTEGER, to_id INTEGER, similarity REAL, reason TEXT, ts TEXT
        )""")


def init_db(path: str | None = None) -> None:
    """Create the schema if absent, run idempotent migrations, and stamp the schema version."""
    with _connect(path) as conn:
        conn.executescript(DDL)
        _migrate(conn)
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        conn.commit()


# --------------------------------------------------------------------------- rows

def _row_to_dict(row: sqlite3.Row, *, with_embedding: bool = False) -> dict:
    d = dict(row)
    alpha, beta = d["alpha"], d["beta"]
    d["confidence"] = alpha / (alpha + beta) if (alpha + beta) else 0.0
    d["pinned"] = bool(d["pinned"])
    emb = d.pop("embedding", None)
    if with_embedding:
        d["embedding"] = _unpack(emb)
    return d


# --------------------------------------------------------------------------- writes

def add_lesson(trigger: str, lesson: str, *, scope: str = "", severity: str = "med",
               embedding: list[float] | None = None, source: str = "agent-distill",
               author: str | None = None, note_raw: str | None = None,
               pinned: bool = False, kind: str = "guard", path: str | None = None) -> int:
    """Insert a lesson. Human-authored lessons get a stronger alpha prior (start more
    trusted) but still drift on real outcomes. kind='anti_pattern' marks a dead-end memory
    (a known past regression) that is rendered as an active inhibition, not guidance."""
    if source not in SOURCES:
        source = "import"
    if severity not in SEVERITIES:
        severity = "med"
    if kind not in KINDS:
        kind = "guard"
    alpha, beta = (3.0, 1.0) if source.startswith("human") else (1.0, 1.0)
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            """INSERT INTO lessons
               (trigger, lesson, scope, severity, embedding, alpha, beta, status,
                source, pinned, author, note_raw, kind, rev, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?, 'active', ?,?,?,?,?, 1, ?,?)""",
            (trigger, lesson, scope, severity, _pack(embedding), alpha, beta,
             source, int(pinned), author, note_raw, kind, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def record_outcome(lesson_id: int, result: str, *, run_id: str | None = None,
                   injected: bool = True, path: str | None = None) -> dict:
    """Append an outcome and atomically update the lesson's Beta(alpha, beta).
    pass -> alpha += 1, fail -> beta += 1. Returns the updated lesson."""
    if result not in ("pass", "fail"):
        raise ValueError("result must be 'pass' or 'fail'")
    col = "alpha" if result == "pass" else "beta"
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO outcomes (lesson_id, run_id, injected, result, ts) VALUES (?,?,?,?,?)",
            (lesson_id, run_id, int(injected), result, now),
        )
        conn.execute(
            f"UPDATE lessons SET {col} = {col} + 1.0, updated_at = ? WHERE id = ?",
            (now, lesson_id),
        )
        conn.commit()
    return get_lesson(lesson_id, path=path)


def demote(lesson_id: int, *, amount: float = 1.0, path: str | None = None) -> dict:
    """Human 'this is bad' — push confidence down by bumping beta (no hard delete)."""
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE lessons SET beta = beta + ?, updated_at = ? WHERE id = ?",
                     (float(amount), now, lesson_id))
        conn.commit()
    return get_lesson(lesson_id, path=path)


def set_pin(lesson_id: int, pinned: bool, *, path: str | None = None) -> dict:
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE lessons SET pinned = ?, updated_at = ? WHERE id = ?",
                     (int(pinned), now, lesson_id))
        conn.commit()
    return get_lesson(lesson_id, path=path)


def tombstone(lesson_id: int, *, superseded_by: int | None = None,
              path: str | None = None) -> dict:
    """Mark a lesson obsolete (belief revision) — soft, auditable, never DROP."""
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE lessons SET status='obsolete', superseded_by=?, updated_at=? WHERE id=?",
            (superseded_by, now, lesson_id),
        )
        conn.commit()
    return get_lesson(lesson_id, path=path)


_EDITABLE = {"trigger", "lesson", "scope", "severity"}


def edit_lesson(lesson_id: int, *, path: str | None = None, **fields) -> dict:
    """Inline-correct a card. Bumps rev. Only whitelisted fields."""
    updates = {k: v for k, v in fields.items() if k in _EDITABLE and v is not None}
    if not updates:
        return get_lesson(lesson_id, path=path)
    now = _now()
    sets = ", ".join(f"{k} = ?" for k in updates)
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            f"UPDATE lessons SET {sets}, rev = rev + 1, updated_at = ? WHERE id = ?",
            (*updates.values(), now, lesson_id),
        )
        conn.commit()
    return get_lesson(lesson_id, path=path)


def set_embedding(lesson_id: int, embedding: list[float], *, path: str | None = None) -> None:
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE lessons SET embedding = ? WHERE id = ?",
                     (_pack(embedding), lesson_id))
        conn.commit()


# ----------------------------------------------------------------- links (A-MEM)

def add_link(from_id: int, to_id: int, *, type: str = "related", weight: float = 1.0,
             path: str | None = None) -> None:
    """Persist a relationship between two lessons. 'related' is undirected (stored in canonical
    (min,max) order and deduped); 'supersedes'/'synthesizes' keep their direction. Idempotent."""
    if from_id == to_id:
        return
    if type == "related" and from_id > to_id:
        from_id, to_id = to_id, from_id
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        dup = conn.execute("SELECT 1 FROM links WHERE from_id=? AND to_id=? AND type=?",
                           (from_id, to_id, type)).fetchone()
        if not dup:
            conn.execute("INSERT INTO links (from_id, to_id, type, weight, created_at) VALUES (?,?,?,?,?)",
                         (from_id, to_id, type, float(weight), now))
        conn.commit()


def list_links(*, path: str | None = None) -> list[dict]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT from_id, to_id, type, weight FROM links").fetchall()
    return [dict(r) for r in rows]


def add_link_rejection(from_id: int, to_id: int, similarity: float, reason: str,
                       *, path: str | None = None) -> None:
    """Negative signal — a candidate pair the LLM judged NOT contradictory (so we don't re-flag it)."""
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO link_rejections (from_id, to_id, similarity, reason, ts) VALUES (?,?,?,?,?)",
                     (from_id, to_id, float(similarity), str(reason)[:300], now))
        conn.commit()


def bump_recall(ids: list[int], *, path: str | None = None) -> None:
    """Record that these lessons were recalled — usage salience. Deliberately does NOT touch
    updated_at (so deck ordering, aging thresholds and the recall snapshot marker stay stable)."""
    ids = [int(i) for i in (ids or [])]
    if not ids:
        return
    now = _now()
    ph = ",".join("?" * len(ids))
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            f"UPDATE lessons SET recall_count = recall_count + 1, last_recalled_at = ? WHERE id IN ({ph})",
            (now, *ids))
        conn.commit()


def reinforce_merge(lesson_id: int, *, path: str | None = None) -> dict:
    """A near-duplicate lesson was taught again — record SALIENCE (merge_count), deliberately NOT
    alpha/confidence: confidence must stay earned from real tests, never bumped by re-teaching.
    Refreshes updated_at so the reinforced card resurfaces."""
    now = _now()
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE lessons SET merge_count = merge_count + 1, updated_at = ? WHERE id = ?",
                     (now, lesson_id))
        conn.commit()
    return get_lesson(lesson_id, path=path)


# --------------------------------------------------------------------------- reads

def get_lesson(lesson_id: int, *, with_embedding: bool = False,
               path: str | None = None) -> dict:
    with _connect(path) as conn:
        row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if row is None:
        raise KeyError(f"lesson {lesson_id} not found")
    return _row_to_dict(row, with_embedding=with_embedding)


def list_lessons(*, status: str = "all", with_embedding: bool = False,
                 path: str | None = None) -> list[dict]:
    """Snapshot read — ONE SELECT. status in {all, active, obsolete}."""
    q = "SELECT * FROM lessons"
    args: tuple = ()
    if status in ("active", "obsolete"):
        q += " WHERE status = ?"
        args = (status,)
    q += " ORDER BY pinned DESC, id ASC"
    with _connect(path) as conn:
        rows = conn.execute(q, args).fetchall()
    return [_row_to_dict(r, with_embedding=with_embedding) for r in rows]


def outcomes_for(lesson_id: int, *, path: str | None = None) -> list[dict]:
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM outcomes WHERE lesson_id = ? ORDER BY id ASC", (lesson_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def outcome_counts(*, path: str | None = None) -> dict[int, dict]:
    """Real recorded outcomes per lesson (from the outcomes table, NOT the Beta prior).
    Returns {lesson_id: {"pass": n, "fail": m}} — the honest grounding signal for metrics()."""
    out: dict[int, dict] = {}
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT lesson_id, result, COUNT(*) AS c FROM outcomes GROUP BY lesson_id, result"
        ).fetchall()
    for r in rows:
        out.setdefault(r["lesson_id"], {"pass": 0, "fail": 0})[r["result"]] = r["c"]
    return out


if __name__ == "__main__":
    import tempfile, os
    tmp = os.path.join(tempfile.mkdtemp(), "smoke.sqlite")
    init_db(tmp)
    lid = add_lesson("multi-tenant query without tenant filter",
                     "Always filter tenant-scoped queries by tenant_id.",
                     scope="symbol: get_orders", severity="high", path=tmp)
    print("added lesson", lid, "conf=", round(get_lesson(lid, path=tmp)["confidence"], 3))
    record_outcome(lid, "pass", run_id="r1", path=tmp)
    print("after 1 pass  conf=", round(get_lesson(lid, path=tmp)["confidence"], 3))
    record_outcome(lid, "fail", run_id="r2", path=tmp)
    print("after 1 fail  conf=", round(get_lesson(lid, path=tmp)["confidence"], 3))
    tombstone(lid, path=tmp)
    print("status now:", get_lesson(lid, path=tmp)["status"])
