# Bau-Plan — Regress-Guard (zur Freigabe)

**Ziel:** Regress-Guard MVP bauen, auf Alibaba deployen, 3-Min-Demo drehen, vor **9. Juli 10:00 GMT-11** auf Devpost einreichen.

## Was Regress-Guard ist
Ein Gedächtnis-Dienst, der verhindert, dass ein KI-Coding-Agent über Sessions denselben gefixten Fehler wiederholt. Roter Test + menschliche Korrektur → Qwen destilliert eine „Lehre" → Ledger. Neue Session: passende Lehre wird in den Agent-Prompt injiziert → Fehler bleibt aus. Confidence steigt/fällt an echtem Test-Outcome (pass/fail).

## Architektur (Pflicht-Diagramm baut darauf auf)
```
[Coding-Agent (Claude Code)] ──MCP-Tool──►  [Regress-Guard API (FastAPI)]
        ▲ injizierte Lehre                         │
        │                                          ├─► Qwen: Lehren-Extraktion (JSON)
[pytest rot + Korrektur-Diff] ──Event──►           ├─► Qwen text-embedding-v3 (Retrieval)
                                                    ├─► Ledger (SQLite): Lehren + Confidence
                                                    └─► Confidence-Updater (Beta/Bayes, pass/fail)
                          Deploy: Alibaba Cloud ECS
```

## Bau-Reihenfolge (8 Tage)
- **Tag 1:** API-Key in `.env` → Smoke-Test `python -m backend.qwen_client` (qwen-plus/max + text-embedding-v3 auf dashscope-intl bestätigen). GitHub Public-Repo + Push. Qwen-Slice isoliert: Lehren-Extraktion (rot+Diff → JSON {trigger, lesson, scope, severity}).
- **Tag 2–3:** Ledger (SQLite) + Retrieval (Fusion BM25 + Qwen-Embedding, aus markmem übernommen) + Confidence-Updater (~50 Zeilen, frisch). MCP-Tool, das die Lehre in den Agent-Prompt injiziert.
- **Tag 3–4:** **A/B-Harness (Kern-Beweis):** Demo-Repo + EIN Fehlermuster (fehlender `tenant_id`-Filter). Lauf 1 (frisch, keine Lehre)=rot, Lauf 2 (frisch, Lehre)=grün.
- **Tag 5:** FastAPI-Endpunkte fertig + minimales Frontend (2 JSON-Tabellen: Ledger vorher/nachher, 1 Confidence-Karte). UI auf 1,5 Tage gedeckelt.
- **Tag 6:** Deploy auf Alibaba ECS + Deploy-Beweis-Screencast.
- **Tag 7:** 3-Min-Demo-Video + Architektur-Diagramm finalisieren.
- **Tag 8:** Puffer, Feinschliff, Devpost-Einreichung.

## Bewusst NICHT (Scope-Schutz)
Multi-Editor/Multi-Agent, mehrere Fehlermuster, pytest-Plugin UND git-Hook, aufwändige UI-Animationen, Prod-Härtung über „läuft auf ECS" hinaus. Stretch (Lehre wird OBSOLETE nach Refactor) fällt zuerst, wenn Zeit knapp.

## Sofort-Schritte (sobald API-Key da)
1. Key → `~/qwen_hackathon/.env` → Smoke-Test.
2. GitHub Public-Repo `NEO849/qwen-memory-agent` → Push (User-initiiert).
3. Qwen-Slice bauen (isoliert testbar).

## Deliverables (Pflicht)
Öffentliches Repo (MIT ✓) · Architektur-Diagramm · ~3-Min-Demo-Video (öffentlich) · Alibaba-Deploy-Beweis · Devpost-Einreichung mit Track MemoryAgent.

## Rollen/Arbeitskreis beim Bauen
Claude = Lead + baut. Bei harten Teilstücken Subagenten: whitebox-source-auditor (markmem-Reuse sauber übernehmen), skeptical-validator (A/B-Kausalität wirklich wasserdicht?), api-security/security-and-hardening (bevor öffentlich). Härten vor „fertig".
