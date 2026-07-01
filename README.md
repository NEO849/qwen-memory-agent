# qwen-memory-agent

Beitrag für die **Global AI Hackathon Series with Qwen Cloud** — Track **MemoryAgent**.

> Ein KI-Agent mit einem Gedächtnis, das sich **selbst korrigiert** und **gezielt vergisst** —
> das, was die großen Assistenten (ChatGPT/Claude-Memory) sichtbar *nicht* können.

## Status

🚧 Gerüst-Phase. Die finale Produkt-Idee wird im Plan-Mode festgelegt und freigegeben,
bevor der Kern final umgesetzt wird. Siehe `docs/HACKATHON.md`.

## Stack

- **Sprache:** Python 3.12
- **Backend:** FastAPI
- **KI (Pflicht):** Qwen-Modelle über Qwen Cloud / Alibaba Model Studio (DashScope)
- **Speicher:** SQLite (+ Retrieval, Design folgt)
- **Deploy (Pflicht):** Alibaba Cloud

## Schnellstart (sobald der API-Key da ist)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # DASHSCOPE_API_KEY eintragen
python -m backend.qwen_client # Verbindungstest gegen Qwen
uvicorn backend.main:app --reload
```

## Lizenz

MIT — siehe `LICENSE`. (Öffentliches Repo + OSS-Lizenz sind Pflicht laut Hackathon-Regeln.)
