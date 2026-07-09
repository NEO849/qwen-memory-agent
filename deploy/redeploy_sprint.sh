#!/usr/bin/env bash
# Redeploy des Gewinner-Sprints auf ECS + Live-Verify.
# SICHER: .env/data/venv/git ausgeschlossen → Prod-Secrets + Ledger unberührt.
# Sprint-Flags werden idempotent (keine Secrets) in die ECS-.env angehängt.
set -uo pipefail
cd /root/qwen_hackathon
ECS="root@47.84.227.215"
KEY="$HOME/.ssh/ecs_deploy"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

echo "=== 1) Code -> ECS (.env/data/venv/git ausgeschlossen) ==="
tar czf - --exclude=.venv --exclude=.git --exclude=.env --exclude=data \
    --exclude='*.sqlite*' --exclude='redteam/report*' . \
  | $SSH "$ECS" 'tar xzf - -C /root/qwen_hackathon' && echo "   transfer ok"

echo "=== 2) Sprint-Flags in ECS-.env sicherstellen (idempotent, keine Secrets) ==="
$SSH "$ECS" 'cd /root/qwen_hackathon && for kv in RG_STRUCTURED_OUTPUT=1 RG_MODEL_ROUTING=1 RG_VECTORIZED=1 RG_REASONING_ENABLED=1; do k=${kv%%=*}; grep -q "^$k=" .env 2>/dev/null || echo "$kv" >> .env; done && echo "aktive RG-Flags:" && grep -E "^RG_" .env'

echo "=== 3) numpy auf ECS (fuer RG_VECTORIZED; Fehlschlag unkritisch → Scalar-Fallback) ==="
$SSH "$ECS" '/root/.venv/bin/pip install -q "numpy>=1.26" 2>&1 | tail -1; /root/.venv/bin/python -c "import numpy;print(\"numpy\",numpy.__version__)" 2>&1 | tail -1'

echo "=== 4) Service neu starten ==="
$SSH "$ECS" 'systemctl restart regress-guard && sleep 2 && systemctl is-active regress-guard'

echo "=== 5) Health (bis zu 20s) ==="
code=""
for i in $(seq 1 20); do
    code=$(curl -s -m5 -o /dev/null -w '%{http_code}' http://47.84.227.215/health || true)
    [ "$code" = "200" ] && { echo "   health=200 ✓"; break; }
    sleep 1
done
[ "$code" = "200" ] || { echo "   FEHLER: health=$code"; exit 1; }

echo "=== 6) Live-Verify: /health · /reasoning · /telemetry (Modell pro Rolle) ==="
echo -n "health:    "; curl -s -m10 http://47.84.227.215/health; echo
echo -n "reasoning: "; curl -s -m10 http://47.84.227.215/reasoning | head -c 90; echo
echo -n "telemetry: "; curl -s -m10 http://47.84.227.215/telemetry | head -c 200; echo

echo "=== 7) LIVE poisoned-memory-Beweis (SAFE erwartet) ==="
BASE=http://47.84.227.215 ./redteam/poisoned_memory_probe.sh 2>&1 | tail -8

echo ""; echo "FERTIG — Live: http://47.84.227.215"
