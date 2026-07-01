"""FastAPI-Einstieg. Gerüst — die Memory-Logik (der Gewinn-Kern) kommt nach dem Idee-Lock.

Start:  uvicorn backend.main:app --reload
"""
from fastapi import FastAPI
from pydantic import BaseModel

from . import qwen_client

app = FastAPI(title="qwen-memory-agent", version="0.0.1")


class ChatIn(BaseModel):
    message: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
def chat(body: ChatIn) -> dict:
    """Platzhalter: leitet aktuell direkt an Qwen weiter, OHNE Gedächtnis.
    Der selbst-korrigierende Memory-Layer wird hier eingehängt (nach Plan-Mode)."""
    reply = qwen_client.chat([{"role": "user", "content": body.message}])
    return {"reply": reply}
