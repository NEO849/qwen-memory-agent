# Deploy to Alibaba Cloud ECS

Regress-Guard is a single Python process (FastAPI + SQLite). No database server, no build step.

## Prerequisites
- An Alibaba Cloud ECS instance (Ubuntu 22.04+), security group open on the app port (e.g. 8000).
- Python 3.11+.
- Your Qwen Cloud API key + workspace base URL.

## Steps

```bash
# 1. get the code
git clone https://github.com/NEO849/qwen-memory-agent.git
cd qwen-memory-agent

# 2. venv + deps
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 3. secrets  (NEVER commit .env)
cp .env.example .env
#    edit .env: DASHSCOPE_API_KEY=...   QWEN_BASE_URL=<Qwen Cloud workspace host>
chmod 600 .env                 # tighten perms on a shared VM
#    optional: export REGRESS_GUARD_TOKEN=<secret> to gate the paid endpoints

# 4. smoke test Qwen from the VM
python -m backend.qwen_client

# 5. run  (‑‑workers 1 is REQUIRED: the SSE fan-out is in-process)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Open `http://<ecs-public-ip>:8000`.

## Run as a service (survives logout / reboot)

`/etc/systemd/system/regress-guard.service`:

```ini
[Unit]
Description=Regress-Guard
After=network.target

[Service]
WorkingDirectory=/root/qwen-memory-agent
EnvironmentFile=/root/qwen-memory-agent/.env
ExecStart=/root/qwen-memory-agent/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
# harden the LLM-generated-code harness away from the service: it is never invoked here.

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now regress-guard
systemctl status regress-guard          # deploy proof for the video
curl http://127.0.0.1:8000/health       # {"status":"ok",...}
```

## Deploy proof (for the submission)
- `systemctl status regress-guard` (active/running) on screen, **or**
- `curl http://<ecs-public-ip>:8000/ab` returning the A/B result from the deployed instance,
- plus the ECS console showing the instance region. The video must show Qwen being called from the
  deployed backend (the `/chat` or agent loop producing a live answer).

## Notes
- The live ledger persists at `data/ledger.sqlite` (gitignored). Back it up if you want the demo
  state to survive a redeploy.
- Put nginx/HTTPS in front only if you want a domain; not required for the demo.
- Do **not** expose `harness/ab_runner.py` over HTTP — it executes model-generated code and is
  offline-only by design.
