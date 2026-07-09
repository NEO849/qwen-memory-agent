#!/usr/bin/env bash
# Ein-Befehl Staging-Check der Welle-1 Qwen-Tiefe (1 bezahlter DISTILL-Call).
# Start:  ! bash /root/qwen_hackathon/deploy/check_reasoning.sh
cd /root/qwen_hackathon || { echo "Projektordner nicht gefunden"; exit 1; }
export RG_REASONING_ENABLED=1 RG_STRUCTURED_OUTPUT=1 RG_MODEL_ROUTING=1
exec .venv/bin/python -m deploy.verify_wave1_staging
