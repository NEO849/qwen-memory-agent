#!/usr/bin/env bash
# Regress-Guard — reproducible 3-arm honest benchmark.
# One line to reproduce the headline numbers (earned-confidence gating vs naive add-only memory
# vs no memory, on unseen bug variants). Every paid Qwen call is disk-cached under .bench_cache/
# so re-runs are free and a crash never re-bills. Seeds are pinned (reproducible); eval codegen
# uses temp>0 so the pass-rates carry honest Wilson CIs.
#
#   ./bench.sh                 # defaults: k=5 seeds, ground=3, temp=0.7, gate=0.62
#   ./bench.sh --k 10          # more seeds -> tighter CIs
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/python -m harness.benchmark "$@"
