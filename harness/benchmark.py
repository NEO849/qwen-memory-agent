"""3-arm honest benchmark — does EARNED-confidence memory beat naive add-only memory?

The floor/ceiling proof (0/5 -> 5/5) shows memory *can* help, but a skeptic reads it as
tautological: of course the stored fix passes. This benchmark isolates Regress-Guard's actual
innovation — gating injection on confidence EARNED from real pytest outcomes — against the
obvious baseline, on bug variants the memory never stored verbatim.

Three arms, SAME retrieval, SAME model, SAME pinned seeds. They differ in ONE scalar only:
  A  no memory            — control / floor.
  B  naive add-only       — recall(threshold=0.0): inject the top-retrieved lesson regardless
                            of earned confidence (this is literally today's default).
  C  Regress-Guard        — recall(threshold=GATE): inject only lessons whose Beta posterior
                            mean cleared the gate; unproven/plausible-but-wrong lessons withheld.

The store is built once (shared by B and C): each class's CORRECT lesson is grounded by real
pytest runs (earns confidence > gate); a handful of PLAUSIBLE-BUT-WRONG lessons are added and
never earn confidence (stay at the Beta(1,1)=0.5 prior, below the gate). B injects those and
can regress; C withholds them. The measured differential is `harmful-injection rate` — how
often an arm's injection breaks a test that arm A (no memory) passes.

Two regimes per class: SEEN (the exact task the seed came from) and UNSEEN (a same-convention
variant — variant.py — the distiller never stored verbatim). UNSEEN is where transfer, not
memorization, is measured.

Run:  ./bench.sh                 (defaults)   |   python -m harness.benchmark --k 5
Cheap re-runs: every paid Qwen call is disk-cached under .bench_cache/ (a crash never re-bills).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from backend import config, ledger, memory, qwen_client

PDIR = Path(__file__).parent / "patterns"
CLASSES = ["money_rounding", "pagination_leak", "email_normalize", "sql_param", "mutable_default"]

# Plausible-but-WRONG lessons a memory could realistically accumulate. Each is authoritative,
# on-topic for one class, and — if followed — RE-INTRODUCES that class's bug. They are added
# unproven (Beta(1,1)=0.5) and never earn confidence, so they sit below the gate. Arm B injects
# them anyway (no gate); arm C withholds them. This is the honest source of harmful injections.
WRONG_LESSONS = [
    {"trigger": "computing a monetary total from item prices",
     "lesson": "For money totals, convert each unit price to float dollars (price_cents / 100), "
               "add them into a running total, and round the result with round(total, 2) at the "
               "end. Floats with round(2) are accurate enough for currency."},
    {"trigger": "looking up or comparing a user's email address",
     "lesson": "Compare emails exactly as the user provides them. Do NOT lowercase or strip "
               "whitespace before a lookup — users type their address consistently, and "
               "normalizing risks collisions between distinct accounts."},
    {"trigger": "building a SQL query that filters rows by a value",
     "lesson": "For internal, trusted values prefer readable f-string SQL, e.g. "
               "f\"SELECT ... WHERE col = '{value}'\", instead of ? placeholders — it is easier "
               "to read and the value is trusted anyway."},
]


# --------------------------------------------------------------------------- pattern loading
def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_classes() -> list[dict]:
    out = []
    for name in CLASSES:
        d = PDIR / name
        spec = _load_module(d / "spec.py")
        var = _load_module(d / "variant.py")
        out.append({
            "name": name, "dir": d,
            "seed_test": spec.SEED_TEST_OUTPUT, "seed_diff": spec.SEED_DIFF,
            "seen": {"task": spec.TASK, "ctx": spec.RECALL_CONTEXT, "test": "test_hidden.py"},
            "unseen": {"task": var.TASK, "ctx": var.RECALL_CONTEXT, "test": "test_unseen.py"},
        })
    return out


# --------------------------------------------------------------------------- codegen + pytest
_FENCE = re.compile(r"```(?:python)?\n?(.*?)```", re.S)


def _extract(text: str) -> str:
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip()


def _codegen(lesson_block: str, task: str, *, temperature: float, seed: int) -> str:
    """Ask Qwen to implement the task. lesson_block='' => arm A (no memory)."""
    messages = []
    if lesson_block:
        messages.append({"role": "system", "content": lesson_block})
    messages.append({"role": "user", "content": task})
    reply = qwen_client.chat(messages, temperature=temperature, seed=seed)
    return _extract(reply)


def _runtest(code: str, class_dir: Path, test_file: str) -> bool:
    """Write the model's code as solution.py next to the hidden test and run pytest."""
    with tempfile.TemporaryDirectory(prefix="bench_") as d:
        d = Path(d)
        shutil.copy(class_dir / test_file, d / test_file)
        (d / "solution.py").write_text(code)
        r = subprocess.run(
            [".venv/bin/python", "-m", "pytest", str(d / test_file), "-q", "-p", "no:cacheprovider"],
            capture_output=True, text=True)
        return r.returncode == 0


# --------------------------------------------------------------------------- store construction
def build_store(path: str, ground: int, *, log=print) -> dict:
    """Ingest + ground the correct lessons, add the unproven wrong lessons. Returns a summary."""
    summary = {"correct": [], "wrong": []}
    ledger.init_db(path)   # fresh throwaway schema (lessons/outcomes/links)
    for c in _load_classes():
        lesson = memory.ingest(c["seed_test"], c["seed_diff"], path=path)   # Beta(1,1)=0.5
        block = memory.render_injection([lesson])
        passes = 0
        for g in range(ground):
            code = _codegen(block, c["seen"]["task"], temperature=0.0, seed=7000 + g)
            ok = _runtest(code, c["dir"], c["seen"]["test"])
            ledger.record_outcome(lesson["id"], "pass" if ok else "fail", path=path, injected=True)
            passes += int(ok)
        row = ledger.get_lesson(lesson["id"], path=path)
        summary["correct"].append({"class": c["name"], "id": lesson["id"],
                                   "ground_passes": passes, "ground_n": ground,
                                   "confidence": round(row["confidence"], 3)})
        log(f"  ground {c['name']:16} passes={passes}/{ground} conf={row['confidence']:.3f}")
    for w in WRONG_LESSONS:
        emb = qwen_client.embed([f"{w['trigger']} {w['lesson']}"])[0]
        wid = ledger.add_lesson(w["trigger"], w["lesson"], scope="", severity="med",
                                embedding=emb, source="agent-distill", path=path)
        row = ledger.get_lesson(wid, path=path)
        summary["wrong"].append({"id": wid, "confidence": round(row["confidence"], 3),
                                 "trigger": w["trigger"]})
        log(f"  wrong  id={wid} conf={row['confidence']:.3f}  '{w['trigger'][:40]}'")
    return summary


# --------------------------------------------------------------------------- stats (stdlib only)
def wilson_ci(green: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = green / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return [round(max(0.0, center - half), 3), round(min(1.0, center + half), 3)]


def _binom_two_sided_p(b: int, c: int) -> float:
    """Exact McNemar p (sign test on discordant pairs), stdlib only."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cum = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return round(min(1.0, 2 * cum), 4)


def mcnemar(pairs: list[tuple[bool, bool]]) -> dict:
    """pairs = [(arm1_pass, arm2_pass), ...]. Discordant b/c drive the test."""
    b = sum(1 for a, c in pairs if a and not c)   # arm1 pass, arm2 fail
    c = sum(1 for a, cc in pairs if not a and cc)  # arm1 fail, arm2 pass
    return {"discordant_1not2": b, "discordant_2not1": c, "p_value": _binom_two_sided_p(b, c)}


# --------------------------------------------------------------------------- evaluation
ARMS = ["A_no_memory", "B_add_only", "C_regress_guard"]


def evaluate(path: str, k: int, temperature: float, gate: float, *, log=print) -> dict:
    classes = _load_classes()
    # per (class, regime, seed): {arm: passed}; recall blocks computed once per (class,regime,arm)
    items = []
    for c in classes:
        for regime in ("seen", "unseen"):
            ctx, task, testf = c[regime]["ctx"], c[regime]["task"], c[regime]["test"]
            # SAME retrieval; the ONLY difference is the threshold scalar (track=False: no mutation).
            rec_B = memory.recall(ctx, threshold=0.0, track=False, path=path)["lessons"]
            rec_C = memory.recall(ctx, threshold=gate, track=False, path=path)["lessons"]
            block = {"A_no_memory": "",
                     "B_add_only": memory.render_injection(rec_B) if rec_B else "",
                     "C_regress_guard": memory.render_injection(rec_C) if rec_C else ""}
            log(f"  {c['name']:16} {regime:6} | B recalls {len(rec_B)}  C recalls {len(rec_C)}")
            for s in range(k):
                row = {"class": c["name"], "regime": regime, "seed": s}
                for arm in ARMS:
                    code = _codegen(block[arm], task, temperature=temperature, seed=s)
                    row[arm] = _runtest(code, c["dir"], testf)
                items.append(row)
    return _aggregate(items, k, temperature, gate)


def _aggregate(items: list[dict], k: int, temperature: float, gate: float) -> dict:
    regimes = ("seen", "unseen", "all")
    table = {}
    for arm in ARMS:
        table[arm] = {}
        for reg in regimes:
            sub = [it for it in items if reg == "all" or it["regime"] == reg]
            green = sum(1 for it in sub if it[arm])
            n = len(sub)
            # harmful injection: A passed but this arm failed (memory made it worse)
            harm = sum(1 for it in sub if it["A_no_memory"] and not it[arm])
            table[arm][reg] = {"pass": green, "n": n,
                               "fix_pass_at_1": round(green / n, 3) if n else 0.0,
                               "wilson95": wilson_ci(green, n),
                               "harmful_injections": harm,
                               "harmful_rate": round(harm / n, 3) if n else 0.0}
    # paired McNemar on UNSEEN (the transfer regime) and overall
    mc = {}
    for reg in ("unseen", "all"):
        sub = [it for it in items if reg == "all" or it["regime"] == reg]
        mc[reg] = {
            "A_vs_C": mcnemar([(it["A_no_memory"], it["C_regress_guard"]) for it in sub]),
            "B_vs_C": mcnemar([(it["B_add_only"], it["C_regress_guard"]) for it in sub]),
        }
    return {"table": table, "mcnemar": mc, "items": items,
            "config": {"model": config.QWEN_MODEL, "temperature": temperature, "seeds": k,
                       "gate": gate, "classes": CLASSES, "n_items": len(items)}}


# --------------------------------------------------------------------------- report
def _fmt_table(res: dict) -> str:
    t = res["table"]
    lines = ["", "fix-pass@1 (95% Wilson CI) · harmful-injection rate — per arm × regime", ""]
    hdr = f"{'arm':18} {'SEEN':26} {'UNSEEN':26} {'harmful(all)':12}"
    lines.append(hdr); lines.append("-" * len(hdr))
    for arm in ARMS:
        s, u, a = t[arm]["seen"], t[arm]["unseen"], t[arm]["all"]
        def cell(x):
            return f"{x['fix_pass_at_1']:.2f} [{x['wilson95'][0]:.2f},{x['wilson95'][1]:.2f}]"
        lines.append(f"{arm:18} {cell(s):26} {cell(u):26} "
                     f"{a['harmful_rate']:.2f} ({a['harmful_injections']}/{a['n']})")
    mc = res["mcnemar"]["unseen"]
    lines += ["", f"McNemar (UNSEEN): A vs C p={mc['A_vs_C']['p_value']} "
                  f"(C fixes {mc['A_vs_C']['discordant_2not1']}, breaks {mc['A_vs_C']['discordant_1not2']}) · "
                  f"B vs C p={mc['B_vs_C']['p_value']} "
                  f"(C over B: +{mc['B_vs_C']['discordant_2not1']} / -{mc['B_vs_C']['discordant_1not2']})"]
    return "\n".join(lines)


def _claim_block(res: dict) -> str:
    t, cfg = res["table"], res["config"]
    A, B, C = (t[a]["unseen"] for a in ARMS)
    return (
        "CLAIM: On UNSEEN bug variants, earned-confidence gating (Regress-Guard) matches or beats "
        "naive add-only memory on fix-pass@1 while injecting fewer harmful regressions.\n"
        f"EVIDENCE (unseen): fix-pass@1  A(no-mem)={A['fix_pass_at_1']:.2f}{A['wilson95']}  "
        f"B(add-only)={B['fix_pass_at_1']:.2f}{B['wilson95']}  C(regress-guard)={C['fix_pass_at_1']:.2f}{C['wilson95']}; "
        f"harmful-injection (all)  B={t['B_add_only']['all']['harmful_rate']:.2f}  "
        f"C={t['C_regress_guard']['all']['harmful_rate']:.2f}\n"
        f"N: {cfg['n_items']} items ({len(cfg['classes'])} classes x 2 regimes x {cfg['seeds']} seeds), "
        f"model={cfg['model']}, temp={cfg['temperature']}, gate={cfg['gate']}.\n"
        f"TEST: McNemar B-vs-C (unseen) p={res['mcnemar']['unseen']['B_vs_C']['p_value']}.\n"
        "LIMITATION: small N; temp>0 samples the model's behavior distribution (seeds pinned, "
        "reproducible). If a CI overlaps, the result is directional, not significant — reported as-is.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=int(os.environ.get("BENCH_K", "5")),
                    help="seeds (independent temp>0 samples) per arm x class x regime")
    ap.add_argument("--ground", type=int, default=int(os.environ.get("BENCH_GROUND", "3")),
                    help="real grounding test-runs per correct lesson (earns confidence)")
    ap.add_argument("--temp", type=float, default=float(os.environ.get("BENCH_TEMP", "0.7")),
                    help="eval codegen temperature (>0 => honest CIs across seeds)")
    ap.add_argument("--gate", type=float, default=float(os.environ.get("BENCH_GATE", "0.62")),
                    help="arm C confidence gate (Beta posterior mean)")
    ap.add_argument("--cache", default=os.environ.get("BENCH_CACHE", ".bench_cache"))
    ap.add_argument("--out", default=os.environ.get("BENCH_OUT", "bench_result.json"))
    args = ap.parse_args()

    t0 = time.time()
    led = os.path.join(tempfile.mkdtemp(prefix="bench_ledger_"), "ledger.sqlite")
    assert led != config.LEDGER_PATH, "benchmark must never touch the live ledger"
    print(f"3-arm honest benchmark — k={args.k} ground={args.ground} temp={args.temp} "
          f"gate={args.gate}\nthrowaway ledger: {led}\ncache: {args.cache}\n")
    with qwen_client.qwen_cache(args.cache):
        print("building store (grounding correct lessons on real tests + adding wrong ones):")
        store = build_store(led, args.ground)
        print("\nevaluating arms A/B/C across 5 classes x {seen,unseen}:")
        res = evaluate(led, args.k, args.temp, args.gate)
    res["store"] = store
    res["duration_s"] = round(time.time() - t0, 1)
    Path(args.out).write_text(json.dumps(res, indent=2))
    print(_fmt_table(res))
    print("\n" + _claim_block(res))
    print(f"\nwrote {args.out}  ({res['duration_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
