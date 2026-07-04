#!/usr/bin/env bash
# run_redteam.sh — startet Regress-Guard lokal (Test-Port 8011) und faehrt den
# promptfoo-Red-Team gegen den eigenen /chat-Endpoint. Provider = Qwen (DashScope).
# Alles lokal + eigener Key = kein AUP-/Fremd-Risiko. Haertungs-Gate vor Deploy.
set -euo pipefail

REPO="/root/qwen_hackathon"
PORT="${PORT:-8011}"
cd "$REPO"

command -v promptfoo >/dev/null 2>&1 || { echo "FEHLER: promptfoo nicht im PATH (npm i -g promptfoo)"; exit 2; }
[[ -f .env ]] || { echo "FEHLER: $REPO/.env fehlt (DASHSCOPE_API_KEY/QWEN_BASE_URL)"; exit 2; }

# .env laden (DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL)
set -a; . ./.env; set +a

# Qwen als OpenAI-kompatiblen Provider fuer promptfoo (Attack-Gen + Grading)
export OPENAI_API_KEY="${DASHSCOPE_API_KEY:?DASHSCOPE_API_KEY nicht gesetzt}"
export OPENAI_BASE_URL="${QWEN_BASE_URL:?QWEN_BASE_URL nicht gesetzt}"
# Attack-Generierung LOKAL ueber den Qwen-Provider (kein Cloud-Dienst, kein Email-Gate, reproduzierbar)
export PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true
export PROMPTFOO_DISABLE_TELEMETRY=1
export PROMPTFOO_DISABLE_UPDATE=1

# App lokal starten, falls Test-Port frei
STARTED=0
if ! curl -s -m3 -o /dev/null "http://127.0.0.1:$PORT/health" 2>/dev/null; then
    echo "[redteam] starte Regress-Guard lokal auf :$PORT ..."
    [[ -x .venv/bin/uvicorn ]] || { echo "FEHLER: .venv/bin/uvicorn fehlt"; exit 2; }
    .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" \
        > /tmp/regress_guard_$PORT.log 2>&1 &
    APP_PID=$!
    STARTED=1
    for i in $(seq 1 30); do
        curl -s -m2 -o /dev/null "http://127.0.0.1:$PORT/health" && break
        sleep 0.5
    done
fi
curl -s -m3 -o /dev/null "http://127.0.0.1:$PORT/health" || { echo "FEHLER: App nicht erreichbar auf :$PORT (siehe /tmp/regress_guard_$PORT.log)"; exit 3; }
echo "[redteam] App live auf :$PORT"

cleanup() { [[ "$STARTED" == "1" ]] && kill "${APP_PID:-0}" 2>/dev/null || true; }
trap cleanup EXIT

# Config nutzt Port 8011 fest; falls abweichend, on-the-fly patchen
CFG="redteam/promptfooconfig.yaml"
if [[ "$PORT" != "8011" ]]; then
    CFG="/tmp/promptfoo_$PORT.yaml"
    sed "s/:8011/:$PORT/" redteam/promptfooconfig.yaml > "$CFG"
fi

echo "[redteam] promptfoo redteam run (Provider=Qwen, numTests klein) ..."
promptfoo redteam run -c "$CFG" --output redteam/report.json --no-cache 2>&1 | tail -40
echo ""
echo "[redteam] Report: $REPO/redteam/report.json"
echo "[redteam] HTML-Ansicht:  promptfoo redteam report -o redteam/report.json"
echo "[redteam] → Fuer echten Lauf numTests in promptfooconfig.yaml erhoehen (mehr Qwen-Calls = mehr Kosten)."
