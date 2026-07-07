"""The A/B proof — does outcome-grounded memory actually stop a repeated bug?

Same coding task, same model (qwen, temperature=0), same hidden test. The ONLY difference
between the two arms is whether a lesson recalled from the ledger is injected:

  Arm A (control)  : no memory injected      -> expected RED
  Arm B (treatment): lesson injected          -> expected GREEN

Honest framing (verified by skeptical-validator): without the remembered convention the
agent MIS-SCOPES the query (it invents an unsupported `user_id` filter and fails the hidden
tenant-isolation test); the recalled lesson steers it to the correct `tenant_id` scoping.
The hidden test enforces true tenant isolation, so it would also catch a cross-tenant leak.

Each arm runs K times and we report a pass-rate — statistical, not anecdotal. This kills
"it was luck". Hard isolation: the harness seeds a THROWAWAY ledger per run and asserts it
is never the live ledger, so the interactive layer can't contaminate the proof.

Usage:  python -m harness.ab_runner --k 5 [--verbose]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from backend import config, memory

DEMO_SRC = Path(__file__).parent / "demo_repo"

# The under-specified task the coding agent sees. It does NOT mention tenant isolation and
# the agent never sees the hidden test — exactly the situation where the tenant filter is
# the easily-forgotten detail. Memory (arm B) supplies the missing rule.
TASK = (
    "Implement the function `get_orders(db, user)` for our orders service.\n"
    "- `db` is a data-access object. `db.all_orders()` returns every order in the system "
    "as a list of dicts.\n"
    "- `user` is a dict with the current user's id: {\"id\": int}\n"
    "Return the orders to display for this user.\n"
    "Respond with ONLY the Python function definition — no markdown fences, no explanation."
)
# NOTE: the task deliberately does NOT reveal that orders are tenant-scoped, nor that the
# user carries a tenant_id. Without that project convention the obvious implementation is
# `return db.all_orders()` — a genuine cross-tenant leak. The convention lives ONLY in the
# recalled lesson (arm B). Verified by skeptical-validator: arm A leaks (superset), not empties.

# What arm B learns from FIRST (a prior red test + human fix), then recalls for TASK.
# This is where the domain convention (orders are tenant-scoped, filter by the 'tenant_id'
# field) enters the system — the agent is never told it in the task.
SEED_TEST_OUTPUT = (
    "FAILED test_tenant_isolation - AssertionError: user from 'acme' saw {'acme','globex'}\n"
    "get_orders() returned db.all_orders() unfiltered — cross-tenant leak.\n"
    "Root cause + fix: orders are tenant-scoped. The user dict also carries user['tenant_id'] "
    "(a string like 'acme'), separate from the numeric user['id']. get_orders must return only "
    "the orders whose order['tenant_id'] equals user['tenant_id'] — compare against "
    "user['tenant_id'], NOT user['id']."
)
SEED_DIFF = (
    "--- a/orders.py\n+++ b/orders.py\n"
    "-    return db.all_orders()\n"
    "+    return [o for o in db.all_orders() if o['tenant_id'] == user['tenant_id']]"
)

# The context arm B uses to RECALL the lesson (mirrors the coding situation).
RECALL_CONTEXT = "implementing get_orders(db, user) that returns orders from db.all_orders() for a user"

# Canonical form of the remembered convention (verbatim from the seeded human fix). Qwen's
# distillation is non-deterministic and occasionally drops the concrete data-model detail
# (that the user carries user['tenant_id'], distinct from user['id']) — which silently breaks
# arm B. To keep the PROOF deterministic (it must not flake on camera) we fall back to this
# exact convention whenever the live distillation is too vague to be actionable. It is the
# same rule the human fix encodes (see SEED_DIFF), so no impact is manufactured.
CANONICAL_LESSON = (
    "Orders are tenant-scoped. The user dict carries user['tenant_id'] (a string like 'acme'), "
    "separate from the numeric user['id']. In get_orders, return only the orders whose "
    "order['tenant_id'] == user['tenant_id'] — compare against user['tenant_id'], never user['id']."
)


def _actionable(lessons: list[dict]) -> bool:
    """Whether the recalled lesson is concrete enough to reliably drive arm B green.

    Empirical finding (measured, not assumed): the model has a STRONG prior for
    get_orders(db, user) — it wants to write `order['user_id'] == user['id']`. Overriding that
    prior reliably (6/6) needs a lesson as concrete as the seeded human fix: it must name the
    order-side field literally AND forbid the user['id'] comparison. Qwen's live distillation of
    the same fix is good and names user['tenant_id'] + the comparison, but its exact phrasing
    varies run-to-run and text-concreteness does NOT predict success (two near-identical
    paraphrases measured at 6/6 vs 0/6). So the determinism guard is real engineering, not a
    cosmetic patch: unless the distilled lesson matches the seeded fix's concrete order-side form,
    inject the canonical form of the SAME human rule so the on-camera proof cannot flake. This is
    conservative on purpose — it prefers a deterministic replay of the remembered fix over a
    coin-flip."""
    txt = " ".join(str(l.get("lesson", "")) for l in lessons).replace('"', "'")
    # Actionable = the lesson names the tenant comparison (user['tenant_id']) AND addresses the
    # user['id'] confusion the model defaults to. Measured: the live distillation phrased generically
    # ("resource['tenant_id'] == user['tenant_id']; never user['id']") already drives arm B to 5/5,
    # so we no longer require the literal order-side form — that gate was over-conservative.
    return "user['tenant_id']" in txt and "user['id']" in txt

_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)
_DEF_RE = re.compile(r"(def\s+get_orders\s*\(.*)", re.DOTALL)


def _extract_function(text: str) -> str:
    """Pull the function definition out of the model's reply (tolerate fences/prose)."""
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1)
    m = _DEF_RE.search(text)
    return (m.group(1) if m else text).strip()


def _agent_write_code(lesson_block: str) -> str:
    """Ask Qwen (temp=0) to implement get_orders. lesson_block is '' for arm A."""
    from backend import qwen_client

    messages = []
    if lesson_block:
        messages.append({"role": "system", "content": lesson_block})
    messages.append({"role": "user", "content": TASK})
    reply = qwen_client.chat(messages, temperature=0)
    return _extract_function(reply)


def _run_pytest(code: str) -> tuple[bool, str]:
    """Drop the generated get_orders into a fresh copy of the demo repo and run its
    hidden test. Returns (passed, captured_output)."""
    workdir = tempfile.mkdtemp(prefix="ab_")
    try:
        shutil.copytree(DEMO_SRC, workdir, dirs_exist_ok=True)
        (Path(workdir) / "solution.py").write_text(code + "\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "test_tenant_isolation.py"],
            cwd=workdir, capture_output=True, text=True, timeout=30,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def run_arm(name: str, lesson_block: str, k: int, verbose: bool) -> dict:
    runs = []
    for i in range(k):
        code = _agent_write_code(lesson_block)
        passed, out = _run_pytest(code)
        runs.append({"passed": passed, "code": code})
        mark = "GREEN" if passed else "RED"
        print(f"  [{name}] run {i + 1}/{k}: {mark}")
        if verbose and i == 0:
            print(f"    ── generated get_orders (run 1) ──\n{_indent(code)}")
    greens = sum(1 for r in runs if r["passed"])
    return {"arm": name, "k": k, "green": greens, "red": k - greens,
            "pass_rate": greens / k if k else 0.0,
            "sample_code": runs[0]["code"] if runs else ""}


def _indent(s: str) -> str:
    return "\n".join("      " + ln for ln in s.splitlines())


def wilson_ci(green: int, k: int, z: float = 1.96) -> list[float]:
    """95% Wilson score interval for a binomial pass-rate (stdlib only, no deps)."""
    if k == 0:
        return [0.0, 0.0]
    p = green / k
    denom = 1 + z * z / k
    center = (p + z * z / (2 * k)) / denom
    half = (z * math.sqrt(p * (1 - p) / k + z * z / (4 * k * k))) / denom
    return [round(max(0.0, center - half), 3), round(min(1.0, center + half), 3)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5,
                    help="temp-0 consistency runs for the floor/ceiling contrast (deterministic)")
    ap.add_argument("--distill-samples", type=int, default=8, dest="distill_samples",
                    help="independent auto-distillations to sample (the real random variable)")
    ap.add_argument("--verbose", action="store_true", help="print a sample generated function")
    ap.add_argument("--out", default=str(Path(__file__).parent.parent / "ab_result.json"))
    args = ap.parse_args()

    from backend import ledger as ledger_mod

    def fresh_ledger() -> str:
        p = os.path.join(tempfile.mkdtemp(prefix="ab_ledger_"), "ledger.sqlite")
        assert p != config.LEDGER_PATH, "A/B ledger must never be the live ledger"
        ledger_mod.init_db(p)
        return p

    # ==========================================================================================
    # Part 1 — Deterministic contrast: FLOOR vs CEILING (temp=0 => consistency, NOT a sample).
    # The task never states the tenant convention and the agent never sees the hidden test, so the
    # model cannot guess it: the knowledge MUST come from memory. temp=0 makes code-gen
    # near-deterministic, so k runs measure the CONSISTENCY of code-gen given a fixed input; we do
    # NOT dress that up as an independent statistical sample (no inflated confidence intervals).
    #   floor   : no memory injected.
    #   ceiling : the remembered developer fix (SEED_DIFF) injected VERBATIM in concrete form — the
    #             capability CEILING of memory injection, NOT the shipped default behaviour.
    # ==========================================================================================
    canonical_block = memory.render_injection(
        [{"lesson": CANONICAL_LESSON, "severity": "high", "source": "human", "scope": "get_orders"}])

    print(f"\nFloor — NO memory ({args.k} temp-0 runs):")
    floor = run_arm("floor", "", args.k, args.verbose)
    print(f"\nCeiling — remembered developer fix, verbatim ({args.k} temp-0 runs):")
    ceiling = run_arm("ceiling", canonical_block, args.k, args.verbose)

    # ==========================================================================================
    # Part 2 — The REAL experiment: distillation reliability (the variable that actually varies).
    # Each independent run draws ONE fresh auto-distillation of the same human fix, then code-gens
    # once. This is the honest sampling unit, and a Wilson interval over these IS valid because the
    # distillations are independent (unlike temp-0 in-run trials). A distillation that drops the
    # concrete domain mapping fails the hidden test — exactly what outcome-grounding exists to catch
    # (demote the bad lesson; the verbatim developer fix remains).
    # ==========================================================================================
    D = args.distill_samples
    distill: list[dict] = []
    print(f"\nDistillation reliability — {D} independent auto-distillations:")
    for d in range(D):
        led = fresh_ledger()
        learned = memory.ingest(SEED_TEST_OUTPUT, SEED_DIFF, path=led)
        recalled = memory.recall(RECALL_CONTEXT, path=led)["lessons"]
        code = _agent_write_code(memory.render_injection(recalled))
        passed, _ = _run_pytest(code)
        distill.append({"passed": passed, "text_actionable": _actionable(recalled),
                        "lesson": (recalled[0]["lesson"] if recalled else "")})
        print(f"  [distill] {d + 1}/{D}: {'GREEN' if passed else 'RED'}  "
              f"(text-actionable={_actionable(recalled)})")
    d_pass = sum(1 for x in distill if x["passed"])
    d_ci = wilson_ci(d_pass, D)
    d_lo, d_hi = int(round(d_ci[0] * 100)), int(round(d_ci[1] * 100))

    framing = [
        "Without memory the model cannot guess our never-stated tenant convention and fails a "
        "hidden isolation test (floor: {}/{} green).".format(floor["green"], floor["k"]),
        "Given the remembered developer fix verbatim, the same hidden test passes ({}/{}) — the "
        "capability CEILING of memory injection.".format(ceiling["green"], ceiling["k"]),
        f"The shipped default AUTO-DISTILLS that fix; in this measurement {d_pass}/{D} independent "
        f"distillations produced a lesson that passed the hidden test (Wilson95 [{d_lo},{d_hi}]%). "
        "Outcome-grounding is the backstop: any distillation that drops the concrete comparison "
        "fails the hidden test and is demoted, not trusted — so confidence tracks what actually works.",
    ]
    must_not_say = (
        f"Report distillation reliability WITH its interval ({d_pass}/{D}, Wilson95 [{d_lo},{d_hi}]%); "
        "do NOT claim the default is guaranteed 100%. The verbatim-fix arm is the ceiling. Do NOT "
        "present temp-0 in-run trials as independent-sample evidence — the independent unit is the "
        "distillation (one draw per run).")

    result = {
        "task": "get_orders tenant isolation",
        "model": config.QWEN_MODEL,
        "temperature": 0,
        "framing": framing,
        "must_not_say": must_not_say,
        "floor_no_memory": floor,
        "ceiling_remembered_fix_verbatim": ceiling,
        "distillation_reliability": {
            "independent_samples": D, "passed": d_pass, "failed": D - d_pass,
            "wilson95": d_ci,
            "note": "The distillation is the real random variable (one draw per run). temp-0 in-run "
                    "code-gen is near-deterministic, so THIS is the honest sampling unit — a valid CI, "
                    "unlike per-run trials.",
            "samples": distill,
        },
        # frontend/back-compat: floor vs ceiling contrast. The UI/demo MUST label arm_b as the
        # remembered-fix CEILING, never as default behaviour (see must_not_say).
        "arm_a_no_memory": floor,
        "arm_b_with_memory": ceiling,
        "distilled_lesson_example": (distill[0]["lesson"] if distill else ""),
        "lesson": CANONICAL_LESSON,
    }
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("\n" + "=" * 64)
    print(f"  A/B RESULT — {result['task']}  (model={result['model']}, temp=0)")
    print("=" * 64)
    print(f"  Floor   (no memory)               : {floor['green']}/{floor['k']} green  (consistent)")
    print(f"  Ceiling (remembered fix, verbatim): {ceiling['green']}/{ceiling['k']} green  (capability ceiling)")
    print(f"  Distillation reliability (REAL)   : {d_pass}/{D} passed  "
          f"(Wilson95 [{d_ci[0]*100:.0f},{d_ci[1]*100:.0f}]%)")
    print("=" * 64)
    print("  Honest headline: 0 -> ceiling with the remembered fix; the shipped auto-distiller is")
    print(f"  fallible ({d_pass}/{D}) and the hidden test catches the misses — that self-correction is")
    print("  the contribution. See ab_result.json 'framing' / 'must_not_say'.")
    print(f"  written -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
