#!/usr/bin/env bash
# Regress-Guard — Baseline-Verhaltensvertrag (smoke test).
# Prueft die Live-Box (oder :8080 staging) read-only + optional einen Chat-Roundtrip.
# Nutzung:  ./smoke.sh [BASE_URL] [--chat]
#   ./smoke.sh                         -> http://47.84.227.215   (prod, ohne Chat)
#   ./smoke.sh http://127.0.0.1:8080   -> staging-Build vor dem :80-Swap
#   ./smoke.sh http://47.84.227.215 --chat  -> inkl. 1 Chat-Roundtrip (paid Qwen-Call)
set -uo pipefail
BASE="${1:-http://47.84.227.215}"
[ "${1:-}" = "--chat" ] && BASE="http://47.84.227.215"
CHAT=0; for a in "$@"; do [ "$a" = "--chat" ] && CHAT=1; done

fail(){ echo "  ✗ $1"; FAILED=1; }
ok(){ echo "  ✓ $1"; }
FAILED=0
echo "== smoke gegen $BASE =="

# 1) /health == 200
code=$(curl -s -m8 -o /tmp/rg_health.json -w '%{http_code}' "$BASE/health" || true)
[ "$code" = "200" ] && ok "/health 200" || fail "/health code=$code"
grep -q '"status"' /tmp/rg_health.json 2>/dev/null && ok "/health JSON ok ($(tr -d '\n' </tmp/rg_health.json | head -c 120))" || fail "/health kein JSON"

# 2) /metrics erreichbar
code=$(curl -s -m8 -o /tmp/rg_metrics.json -w '%{http_code}' "$BASE/metrics" || true)
[ "$code" = "200" ] && ok "/metrics 200 ($(tr -d '\n' </tmp/rg_metrics.json | head -c 120))" || fail "/metrics code=$code"

# 3) /graph liefert Knoten
code=$(curl -s -m8 -o /tmp/rg_graph.json -w '%{http_code}' "$BASE/graph" || true)
n=$(grep -o '"id"' /tmp/rg_graph.json 2>/dev/null | wc -l | tr -d ' ')
[ "$code" = "200" ] && [ "${n:-0}" -gt 0 ] && ok "/graph 200 (~$n Knoten-Refs)" || fail "/graph code=$code nodes=$n"

# 4) /recall liefert eine Lesson (Retrieval-Pfad)
code=$(curl -s -m15 -o /tmp/rg_recall.json -w '%{http_code}' "$BASE/recall?q=how+do+I+safely+paginate+a+python+api" || true)
[ "$code" = "200" ] && ok "/recall 200 ($(tr -d '\n' </tmp/rg_recall.json | head -c 100))" || fail "/recall code=$code"

# 5) /events SSE oeffnet (erste Bytes)
timeout 5 curl -s -m5 -N "$BASE/events" >/tmp/rg_sse.txt 2>/dev/null || true
[ -s /tmp/rg_sse.txt ] && ok "/events SSE liefert Daten" || echo "  ~ /events SSE leer (evtl. keine Live-Events — nicht kritisch)"

# 6) optional: 1 Chat-Roundtrip (paid)
if [ "$CHAT" = "1" ]; then
  code=$(curl -s -m45 -o /tmp/rg_chat.json -w '%{http_code}' -X POST "$BASE/chat" \
    -H 'Content-Type: application/json' -d '{"message":"How do I safely paginate a Python API?"}' || true)
  [ "$code" = "200" ] && [ -s /tmp/rg_chat.json ] && ok "/chat 200 ($(tr -d '\n' </tmp/rg_chat.json | head -c 90))" || fail "/chat code=$code"
fi

echo "== $([ $FAILED -eq 0 ] && echo 'ALLE GRUEN ✓' || echo 'FEHLER ✗') =="
exit $FAILED
