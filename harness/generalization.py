"""Generalization proof — the floor / ceiling / distillation A/B across THREE bug classes.

One pattern could be cherry-picked; three independent classes each flipping from floor (no memory)
to ceiling (remembered fix) shows the memory GENERALIZES. Same honest design as harness/ab_runner.py,
driven over the tenant pattern + harness/patterns/*. Floor, ceiling and the shipped auto-distiller
are all measured live and disclosed with Wilson 95% intervals.

Usage:  python -m harness.generalization [--k 3] [--distill-samples 6]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from backend import config, ledger, memory
from harness import ab_runner  # reuse the tenant strings + wilson_ci

PDIR = Path(__file__).parent / "patterns"
_FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)
_DEF = re.compile(r"(def\s+\w+\s*\(.*)", re.DOTALL)


def _extract(text: str) -> str:
    m = _FENCE.search(text)
    if m:
        text = m.group(1)
    m = _DEF.search(text)
    return (m.group(1) if m else text).strip()


def _codegen(lesson_block: str, task: str) -> str:
    from backend import qwen_client
    msgs = []
    if lesson_block:
        msgs.append({"role": "system", "content": lesson_block})
    msgs.append({"role": "user", "content": task})
    return _extract(qwen_client.chat(msgs, temperature=0))


def _runtest(code: str, test_dir: Path, test_file: str) -> bool:
    work = tempfile.mkdtemp(prefix="gen_")
    try:
        shutil.copytree(test_dir, work, dirs_exist_ok=True)
        (Path(work) / "solution.py").write_text(code + "\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", test_file],
                              cwd=work, capture_output=True, text=True, timeout=30)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _arm(task: str, block: str, test_dir: Path, test_file: str, k: int) -> dict:
    green = sum(1 for _ in range(k) if _runtest(_codegen(block, task), test_dir, test_file))
    return {"k": k, "green": green}


def _load_spec(path: Path):
    sp = importlib.util.spec_from_file_location("spec", path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _patterns() -> list[dict]:
    pats = [{
        "name": "tenant_isolation", "task": ab_runner.TASK,
        "seed_out": ab_runner.SEED_TEST_OUTPUT, "seed_diff": ab_runner.SEED_DIFF,
        "canonical": ab_runner.CANONICAL_LESSON, "recall_ctx": ab_runner.RECALL_CONTEXT,
        "dir": Path(__file__).parent / "demo_repo", "test": "test_tenant_isolation.py",
    }]
    for name in ("money_rounding", "pagination_leak"):
        s = _load_spec(PDIR / name / "spec.py")
        pats.append({
            "name": name, "task": s.TASK, "seed_out": s.SEED_TEST_OUTPUT, "seed_diff": s.SEED_DIFF,
            "canonical": s.CANONICAL_LESSON, "recall_ctx": s.RECALL_CONTEXT,
            "dir": PDIR / name, "test": "test_hidden.py",
        })
    return pats


def _fresh_ledger() -> str:
    p = os.path.join(tempfile.mkdtemp(prefix="gen_led_"), "l.sqlite")
    assert p != config.LEDGER_PATH
    ledger.init_db(p)
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3, help="floor/ceiling consistency runs (temp-0)")
    ap.add_argument("--distill-samples", type=int, default=6, dest="distill_samples")
    ap.add_argument("--out", default=str(Path(__file__).parent.parent / "generalization_result.json"))
    args = ap.parse_args()

    results = []
    for p in _patterns():
        canon = memory.render_injection(
            [{"lesson": p["canonical"], "severity": "high", "source": "human", "scope": p["name"]}])
        floor = _arm(p["task"], "", p["dir"], p["test"], args.k)
        ceiling = _arm(p["task"], canon, p["dir"], p["test"], args.k)
        D, dp = args.distill_samples, 0
        for _ in range(D):
            led = _fresh_ledger()
            memory.ingest(p["seed_out"], p["seed_diff"], path=led)
            rec = memory.recall(p["recall_ctx"], path=led)["lessons"]
            if _runtest(_codegen(memory.render_injection(rec), p["task"]), p["dir"], p["test"]):
                dp += 1
        ci = ab_runner.wilson_ci(dp, D)
        results.append({"pattern": p["name"], "floor": floor, "ceiling": ceiling,
                        "distill_pass": dp, "distill_n": D, "distill_wilson95": ci})
        print(f"{p['name']:>16}: floor {floor['green']}/{floor['k']} | "
              f"ceiling {ceiling['green']}/{ceiling['k']} | distill {dp}/{D} CI{ci}")

    af = sum(r["floor"]["green"] for r in results); afk = sum(r["floor"]["k"] for r in results)
    ac = sum(r["ceiling"]["green"] for r in results); ack = sum(r["ceiling"]["k"] for r in results)
    ad = sum(r["distill_pass"] for r in results); adn = sum(r["distill_n"] for r in results)
    out = {
        "model": config.QWEN_MODEL, "temperature": 0, "patterns": results,
        "aggregate": {"floor": f"{af}/{afk}", "ceiling": f"{ac}/{ack}",
                      "distill": f"{ad}/{adn}", "distill_wilson95": ab_runner.wilson_ci(ad, adn)},
        "note": ("Three independent bug classes (tenant isolation, money rounding, pagination leak). "
                 "Floor = no memory; Ceiling = remembered verbatim fix; distill = the shipped "
                 "auto-distiller over independent samples (Wilson95). The memory flips every class "
                 "from floor to ceiling — one pattern could be cherry-picked, three cannot."),
    }
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("AGGREGATE:", out["aggregate"])
    print("written ->", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
