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
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, evaluation, events, ledger, memory, qwen_client, reviser

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
AB_RESULT = ROOT / "ab_result.json"

MAX_BODY = 64 * 1024                              # reject bodies larger than 64 KB
DEMO_TOKEN = os.environ.get("REGRESS_GUARD_TOKEN", "")   # if set, gate paid-LLM writes
GATED = ("/chat", "/recall", "/notes", "/ingest", "/revise")

app = FastAPI(title="regress-guard", version="1.0.0")


@app.middleware("http")
async def _guard(request: Request, call_next):
    # 1) body-size cap — cheap cost-DoS protection on the paid Qwen path
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_BODY:
        return JSONResponse({"detail": "payload too large"}, status_code=413)
    # 2) optional shared-secret gate on paid endpoints (enabled only if env token set)
    if DEMO_TOKEN and request.url.path in GATED:
        if request.headers.get("x-demo-token") != DEMO_TOKEN:
            return JSONResponse({"detail": "forbidden"}, status_code=403)
    return await call_next(request)


@app.exception_handler(KeyError)
async def _key_error(_request: Request, exc: KeyError) -> JSONResponse:
    return JSONResponse({"detail": "not found"}, status_code=404)


@app.on_event("startup")
def _startup() -> None:
    ledger.init_db(config.LEDGER_PATH)


# ------------------------------------------------------------------ models ----
class IngestIn(BaseModel):
    test_output: str = Field(max_length=20000)
    diff: str = Field(max_length=20000)


class OutcomeIn(BaseModel):
    lesson_id: int
    result: Literal["pass", "fail"]
    run_id: str | None = Field(default=None, max_length=128)
    injected: bool = True


class NoteIn(BaseModel):
    text: str = Field(max_length=8000)
    distill: bool = False
    scope: str = Field(default="", max_length=500)
    severity: Literal["low", "med", "high"] = "med"
    pinned: bool = False
    author: str | None = Field(default=None, max_length=128)


class EditIn(BaseModel):
    trigger: str | None = Field(default=None, max_length=2000)
    lesson: str | None = Field(default=None, max_length=4000)
    scope: str | None = Field(default=None, max_length=500)
    severity: Literal["low", "med", "high"] | None = None


class ChatIn(BaseModel):
    message: str = Field(max_length=8000)
    k: int = Field(default=4, ge=1, le=20)


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
    # attach REAL recorded pass/fail (from the outcomes table) so the card shows grounded counts,
    # not the Beta prior pseudo-counts — consistent with the memory-quality panel.
    counts = ledger.outcome_counts(path=config.LEDGER_PATH)
    for l in lessons:
        c = counts.get(l["id"], {})
        l["real_pass"], l["real_fail"] = c.get("pass", 0), c.get("fail", 0)
    return Response(content=json.dumps({"etag": etag, "lessons": lessons}),
                    media_type="application/json")


@app.get("/recall")
def get_recall(q: str = Query(max_length=8000), k: int = Query(5, ge=1, le=20)) -> dict:
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


class ReviseIn(BaseModel):
    change: str = Field(max_length=8000)


@app.post("/revise")
def post_revise(body: ReviseIn) -> dict:
    """Qwen role 3: judge active lessons against a described change; tombstone obsolete ones."""
    results = reviser.revise(body.change, path=config.LEDGER_PATH)
    if any(r["action"] == "tombstoned" for r in results):
        events.bump(action="revise")
    return {"results": results}


# ------------------------------------------------- self-eval / self-tune ---
@app.get("/metrics")
def get_metrics() -> dict:
    """Cheap memory-health snapshot (no LLM): grounding + calibration + active weights."""
    return evaluation.metrics(path=config.LEDGER_PATH)


@app.post("/evaluate")
def post_evaluate(sample: int = Query(8, ge=2, le=30)) -> dict:
    """Measure retrieval quality on keyword-free paraphrase queries (vector on vs off)."""
    return evaluation.evaluate(path=config.LEDGER_PATH, sample=sample)


@app.post("/tune")
def post_tune(sample: int = Query(8, ge=2, le=30)) -> dict:
    """Grid-search RRF fusion weights against Recall@1; persist only if it beats baseline."""
    result = evaluation.tune(path=config.LEDGER_PATH, sample=sample)
    if result.get("tuned"):
        events.bump(action="tune")   # weights changed → deck's next recall uses them
    return result


# --------------------------------------------------------------------- chat ---
@app.post("/chat")
def chat(body: ChatIn) -> dict:
    """Main Q&A: recall relevant lessons, inject them, let Qwen answer. Returns the reply
    plus the ids of the lessons that were recalled (for the deck cross-highlight)."""
    rec = memory.recall(body.message, k=body.k, path=config.LEDGER_PATH)
    injection = memory.render_injection(rec["lessons"])
    persona = (
        "You are Regress-Guard's coding assistant. Answer software-engineering questions "
        "concisely and apply the remembered coding lessons below when relevant. "
        "You cannot spawn agents, run tools, or perform actions — you only give coding advice. "
        "If a request is not a coding question, say so in one sentence and offer a coding angle."
    )
    system = persona + ("\n\n" + injection if injection else "")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": body.message}]
    reply = qwen_client.chat(messages, temperature=0.3)
    return {"reply": reply, "recalled": [l["id"] for l in rec["lessons"]],
            "injected": bool(injection)}


# --------------------------------------------------------------- agent loop ---
class InjectIn(BaseModel):
    text: str
    interrupt: bool = True


@app.get("/agent/status")
def agent_status() -> dict:
    from .agent_loop import session
    return session.state()


@app.post("/agent/start")
async def agent_start() -> dict:
    from .agent_loop import session
    return await session.start()


@app.post("/agent/pause")
async def agent_pause() -> dict:
    from .agent_loop import session
    return await session.pause()


@app.post("/agent/resume")
async def agent_resume() -> dict:
    from .agent_loop import session
    return await session.resume_()


@app.post("/agent/stop")
async def agent_stop() -> dict:
    from .agent_loop import session
    return await session.stop()


@app.post("/agent/inject")
async def agent_inject(body: InjectIn) -> dict:
    from .agent_loop import session
    return await session.inject(body.text, interrupt=body.interrupt)


# -------------------------------------------------------------------- events --
@app.get("/events")
async def sse() -> StreamingResponse:
    return StreamingResponse(events.stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------------- static ---
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
