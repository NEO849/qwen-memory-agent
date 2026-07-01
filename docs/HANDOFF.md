# HANDOFF — nahtlos weitermachen (Stand 2026-07-01, abends)

> Falls die Session pausiert (Token-Limit ~3h): alles liegt auf Platte + Git.
> Diese Datei + `docs/HACKATHON.md` + `docs/IDEA_DECISION.md` + `docs/BUILD_PLAN.md` + Memory `project_qwen_hackathon_memoryagent.md` = voller Kontext.

## Wo wir stehen
- ✅ Devpost NEO849 registriert · Alibaba-Konto **verifiziert** (ID 5260881302246697, Germany)
- ✅ Konzept gewählt: **Regress-Guard** (Ideen-Arbeitskreis fertig → `IDEA_DECISION.md`, Plan → `BUILD_PLAN.md`)
- ✅ Projekt-Gerüst gebaut + committet (`0967f72`)
- ✅ GitHub Public-Repo erstellt: **https://github.com/NEO849/qwen-memory-agent** (⚠️ NOCH NICHT gepusht)
- ✅ **QWEN VERBUNDEN & GETESTET** (Key in `.env`, gitignored):
  - Endpoint: `https://Ws-sfg3agkg62ni77ky.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1` (Qwen-Cloud-Workspace, Region Singapore, Scope INTERNATIONAL)
  - Chat OK: `qwen-plus`, `qwen3.7-plus` · Embedding OK: `text-embedding-v4`/`v3` (dim 1024)
  - Key-Format `sk-ws-…` = Workspace-Key → funktioniert NUR mit dem maas-Workspace-Host, NICHT mit dashscope-intl. (Das war die Stolperfalle.)

## Kein Setup-Blocker mehr — bereit zum Bauen

## Nächste Schritte (Reihenfolge)
1. **Repo pushen:** `git remote add origin https://github.com/NEO849/qwen-memory-agent.git` → `git push -u origin master`. (Push = User-initiiert; Auth klären — VPS hat evtl. nur read-only PAT.)
2. **Bauen (Regress-Guard, siehe BUILD_PLAN.md):** Qwen-Slice zuerst isoliert (Lehren-Extraktion JSON aus rotem Test+Diff via `qwen-plus`/`qwen3.7-plus`; Retrieval via `text-embedding-v4`). Dann Ledger (SQLite) + Confidence-Updater (~50 Zeilen, frisch) + MCP-Tool (Lehre in Agent-Prompt injizieren) + A/B-Harness (Kern-Beweis) + FastAPI + minimales Frontend.
3. Deploy Alibaba ECS + Deploy-Beweis-Screencast.
4. 3-Min-Demo-Video + Architektur-Diagramm.
5. Devpost „Projekt erstellen"/Einreichen (Track MemoryAgent) vor **9. Juli 10:00 GMT-11**.

## Regeln
Kein Push/Submit ohne User-OK · Secrets nie committen (.env gitignored) · vor „fertig" härten (skeptical-validator: A/B-Kausalität wasserdicht?).

## Smoke-Test-Befehl
`cd ~/qwen_hackathon && .venv/bin/python -c "from backend import qwen_client; print(qwen_client.chat([{'role':'user','content':'sag OK'}]))"`
