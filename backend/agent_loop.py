"""Controllable coding-agent loop — the interactive 'playground' the human can steer live.

A single asyncio task runs a step-wise loop over one coding goal:
    (drain injected notes -> lessons) -> recall -> act (Qwen writes code) -> test -> repeat

The human steers it out-of-band, alias-style, WHILE it runs:
    pause / resume   — gate the loop at the next step boundary
    stop             — cancel the in-flight step and end the loop
    inject(text)     — drop a 'by the way' note; by default it INTERRUPTS the current step,
                       so the very next iteration recalls the new note and redoes the task
                       with it (the "I told it, it fixed itself" beat)

Honesty: injection takes effect at the next step boundary (or immediately via interrupt +
re-plan) — there is no mid-token splicing. Blocking Qwen/pytest calls run in a thread so
pause/stop/SSE stay responsive; cancelling a step abandons its in-flight result and re-plans.

Runs on the LIVE ledger so the deck + console + agent share one memory. The deterministic
A/B proof (harness/ab_runner.py) is a SEPARATE, isolated surface and is never touched here.
"""
from __future__ import annotations

import asyncio

from . import config, events, memory

# Reuse the exact demo task + code-gen + test from the A/B harness (one source of truth).
from harness import ab_runner

GOAL_CONTEXT = ab_runner.RECALL_CONTEXT
_BEAT_SLICES = 8          # ~2.4s pause between attempts, in interruptible 0.3s slices


class AgentSession:
    def __init__(self) -> None:
        self.status = "idle"                 # idle | running | paused
        self.step = 0
        self.last: dict | None = None
        self.task: asyncio.Task | None = None
        self.resume = asyncio.Event(); self.resume.set()
        self.inject_q: asyncio.Queue[str] = asyncio.Queue()
        self._cur: asyncio.Task | None = None
        self._stopping = False

    # ------------------------------------------------------------------ state
    def state(self) -> dict:
        return {"status": self.status, "step": self.step, "last": self.last}

    def _emit(self, **kw) -> None:
        events.publish({"type": "agent_step", "status": self.status, "step": self.step, **kw})

    # ---------------------------------------------------------------- control
    async def start(self, goal: str | None = None) -> dict:
        if self.task and not self.task.done():
            return self.state()
        self._stopping = False; self.resume.set(); self.step = 0; self.last = None
        self.status = "running"          # reflect immediately for the caller
        self.task = asyncio.create_task(self._run(goal or GOAL_CONTEXT))
        return self.state()

    async def pause(self) -> dict:
        if self.status == "running":
            self.resume.clear(); self.status = "paused"; self._emit(phase="paused")
        return self.state()

    async def resume_(self) -> dict:
        if self.status == "paused":
            self.status = "running"; self.resume.set(); self._emit(phase="resumed")
        return self.state()

    async def stop(self) -> dict:
        self._stopping = True; self.resume.set()
        if self._cur and not self._cur.done():
            self._cur.cancel()
        return self.state()

    async def inject(self, text: str, interrupt: bool = True) -> dict:
        await self.inject_q.put(text)
        self._emit(phase="inject-queued", text=text)
        if interrupt and self._cur and not self._cur.done():
            self._cur.cancel()   # abandon the in-flight attempt -> next iteration re-plans
        return self.state()

    # ------------------------------------------------------------------- loop
    async def _run(self, goal: str) -> None:
        self.status = "running"; self._emit(phase="started", goal=goal)
        while True:
            await self.resume.wait()
            if self._stopping:
                break

            # 1) drain any 'by the way' notes into the live ledger (deck reacts via bump)
            notes = []
            while not self.inject_q.empty():
                notes.append(self.inject_q.get_nowait())
            for text in notes:
                lesson = await asyncio.to_thread(memory.add_note, text, path=config.LEDGER_PATH)
                events.bump(lesson_id=lesson["id"], action="note")
                self._emit(phase="note", lesson_id=lesson["id"], text=text)

            # 2) recall the lessons to inject for this task
            rec = await asyncio.to_thread(memory.recall, goal, path=config.LEDGER_PATH)
            inject = memory.render_injection(rec["lessons"])
            recalled = [l["id"] for l in rec["lessons"]]
            self._emit(phase="recall", recalled=recalled, inject=inject)

            # 3) act — Qwen writes the code (cancellable so inject/stop stay responsive)
            self._cur = asyncio.ensure_future(
                asyncio.to_thread(ab_runner._agent_write_code, inject))
            try:
                code = await self._cur
            except asyncio.CancelledError:
                self._cur = None
                if self._stopping:
                    break
                self._emit(phase="interrupted")
                continue
            self._cur = None

            # 4) test — the hidden ground truth judges it
            passed, _out = await asyncio.to_thread(ab_runner._run_pytest, code)
            self.step += 1
            self.last = {"code": code, "passed": passed, "recalled": recalled, "step": self.step}
            self._emit(phase="result", code=code, passed=passed, recalled=recalled)

            # brief, interruptible beat before the next attempt
            for _ in range(_BEAT_SLICES):
                if self._stopping or not self.resume.is_set():
                    break
                await asyncio.sleep(0.3)

        self.status = "idle"; self._stopping = False; self._cur = None
        self._emit(phase="stopped")


session = AgentSession()
