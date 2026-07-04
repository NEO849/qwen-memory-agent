#!/usr/bin/env bash
# Redeploy der gehärteten master auf ECS + Live-Verifikation.
# User-initiiert via !-Prefix ausführen (Outward-SSH). Ledger (data/) bleibt erhalten.
set -uo pipefail
cd /root/qwen_hackathon
ECS="root@47.84.227.215"
KEY="$HOME/.ssh/ecs_deploy"

echo "=== 1) Code -> ECS (data/ + venv + git ausgeschlossen) ==="
tar czf - --exclude=.venv --exclude=.git --exclude=data --exclude='*.sqlite*' --exclude='redteam/report*' . \
  | ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$ECS" 'tar xzf - -C /root/qwen_hackathon'
echo "   transfer rc=$?"

echo "=== 2) Service neu starten ==="
ssh -i "$KEY" "$ECS" 'systemctl restart regress-guard && sleep 2 && systemctl is-active regress-guard'

echo "=== 3) Health-Check ==="
for i in $(seq 1 20); do
    code=$(curl -s -m5 -o /dev/null -w '%{http_code}' http://47.84.227.215/health || true)
    [ "$code" = "200" ] && { echo "   health=200 ✓"; break; }
    sleep 1
done
[ "${code:-}" = "200" ] || { echo "   FEHLER: Server nicht healthy (code=$code)"; exit 1; }

echo "=== 4) Normaler Chat (Sanity, recallt Lesson) ==="
curl -s -m40 -X POST http://47.84.227.215/chat -H 'Content-Type: application/json' \
  -d '{"message":"How do I safely paginate a Python API?"}' | head -c 160; echo

echo "=== 5) LIVE poisoned-memory-Beweis (erwartet SAFE; Test-Lesson wird sofort tombstoned) ==="
BASE=http://47.84.227.215 ./redteam/poisoned_memory_probe.sh 2>&1 | tail -12

echo ""
echo "FERTIG. Live: http://47.84.227.215 — gehärteter Stand."
