"""Regress-Guard API — FastAPI over the memory service.

Run:  uvicorn backend.main:app --workers 1   (single worker: SSE fan-out is in-process)

Endpoints:
  GET  /health
  GET  /ledger?since=          list lessons (+ etag; 304 when unchanged)
  GET  /recall?q=&k=           lessons that would be injected for a context
  POST /ingest                 learn a lesson from a red test + fix diff (Qwen DISTILL)
  POST /outcome                feed a real pass/fail -> Beta confidence update
  POST /notes                  human 'by the way' note -> lesson
  PATCH /lessons/{id}          inline-correct a lesson
  POST /lessons/{id}/{pin|unpin|demote|tombstone}
  GET  /ab                     last A/B proof result (ab_result.json)
  POST /chat                   main Q&A: recall -> inject -> Qwen answer
  GET  /events                 SSE stream of ledger_changed events
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, events, ledger, memory, qwen_client

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
AB_RESULT = ROOT / "ab_result.json"

app = FastAPI(title="regress-guard", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    ledger.init_db(config.LEDGER_PATH)


# ------------------------------------------------------------------ models ----
class IngestIn(BaseModel):
    test_output: str
    diff: str


class OutcomeIn(BaseModel):
    lesson_id: int
    result: str            # pass | fail
    run_id: str | None = None
    injected: bool = True


class NoteIn(BaseModel):
    text: str
    distill: bool = False
    scope: str = ""
    severity: str = "med"
    pinned: bool = False
    author: str | None = None


class EditIn(BaseModel):
    trigger: str | None = None
    lesson: str | None = None
    scope: str | None = None
    severity: str | None = None


class ChatIn(BaseModel):
    message: str
    k: int = 4


# -------------------------------------------------------------------- reads ---
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "etag": events.current_etag()}


@app.get("/ledger")
def get_ledger(status: str = "all", since: int | None = None) -> Response:
    etag = events.current_etag()
    if since is not None and since == etag:
        return Response(status_code=304)
    lessons = ledger.list_lessons(status=status, path=config.LEDGER_PATH)
    return Response(content=json.dumps({"etag": etag, "lessons": lessons}),
                    media_type="application/json")


@app.get("/recall")
def get_recall(q: str, k: int = 5) -> dict:
    return memory.recall(q, k=k, path=config.LEDGER_PATH)


@app.get("/ab")
def get_ab() -> dict:
    if AB_RESULT.exists():
        return json.loads(AB_RESULT.read_text(encoding="utf-8"))
    return {"available": False}


# ------------------------------------------------------------------- writes ---
@app.post("/ingest")
def post_ingest(body: IngestIn) -> dict:
    lesson = memory.ingest(body.test_output, body.diff, path=config.LEDGER_PATH)
    events.bump(lesson_id=lesson["id"], action="ingest")
    return lesson


@app.post("/outcome")
def post_outcome(body: OutcomeIn) -> dict:
    if body.result not in ("pass", "fail"):
        raise HTTPException(400, "result must be 'pass' or 'fail'")
    lesson = memory.record_outcome(body.lesson_id, body.result, run_id=body.run_id,
                                   injected=body.injected, path=config.LEDGER_PATH)
    events.bump(lesson_id=body.lesson_id, action="outcome")
    return lesson


@app.post("/notes")
def post_note(body: NoteIn) -> dict:
    lesson = memory.add_note(body.text, distill=body.distill, scope=body.scope,
                             severity=body.severity, pinned=body.pinned,
                             author=body.author, path=config.LEDGER_PATH)
    events.bump(lesson_id=lesson["id"], action="note")
    return lesson


@app.patch("/lessons/{lesson_id}")
def patch_lesson(lesson_id: int, body: EditIn) -> dict:
    lesson = ledger.edit_lesson(lesson_id, path=config.LEDGER_PATH, **body.model_dump())
    events.bump(lesson_id=lesson_id, action="edit")
    return lesson


@app.post("/lessons/{lesson_id}/pin")
def pin(lesson_id: int) -> dict:
    lesson = ledger.set_pin(lesson_id, True, path=config.LEDGER_PATH)
    events.bump(lesson_id=lesson_id, action="pin")
    return lesson


@app.post("/lessons/{lesson_id}/unpin")
def unpin(lesson_id: int) -> dict:
    lesson = ledger.set_pin(lesson_id, False, path=config.LEDGER_PATH)
    events.bump(lesson_id=lesson_id, action="unpin")
    return lesson


@app.post("/lessons/{lesson_id}/demote")
def demote(lesson_id: int) -> dict:
    lesson = ledger.demote(lesson_id, path=config.LEDGER_PATH)
    events.bump(lesson_id=lesson_id, action="demote")
    return lesson


@app.post("/lessons/{lesson_id}/tombstone")
def tombstone(lesson_id: int) -> dict:
    lesson = ledger.tombstone(lesson_id, path=config.LEDGER_PATH)
    events.bump(lesson_id=lesson_id, action="tombstone")
    return lesson


# --------------------------------------------------------------------- chat ---
@app.post("/chat")
def chat(body: ChatIn) -> dict:
    """Main Q&A: recall relevant lessons, inject them, let Qwen answer. Returns the reply
    plus the ids of the lessons that were recalled (for the deck cross-highlight)."""
    rec = memory.recall(body.message, k=body.k, path=config.LEDGER_PATH)
    injection = memory.render_injection(rec["lessons"])
    messages = []
    if injection:
        messages.append({"role": "system", "content": injection})
    messages.append({"role": "user", "content": body.message})
    reply = qwen_client.chat(messages, temperature=0.3)
    return {"reply": reply, "recalled": [l["id"] for l in rec["lessons"]],
            "injected": bool(injection)}


# -------------------------------------------------------------------- events --
@app.get("/events")
async def sse() -> StreamingResponse:
    return StreamingResponse(events.stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------------- static ---
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
