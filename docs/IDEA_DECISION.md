# Ideen-Entscheidung (Arbeitskreis-Ergebnis, 2026-07-01)

Voll-Output: `/tmp/claude-0/-root/78f07c37-8d47-4707-a8dc-f2f1d6fb64b2/tasks/wz6usbe0y.output`
12 Konzepte generiert, Jury-bewertet, adversarial gehärtet. **Entscheidung steht im Plan-Mode aus.**

## 🥇 Sieger (Score 83.5): Regress-Guard — Fehler-Gedächtnis für Coding-Agents
Ein Gedächtnis, das verhindert, dass KI-Coding-Agenten über Sessions **denselben gefixten Fehler wieder einbauen**. Wird ein Test rot und der Mensch korrigiert, destilliert Qwen die Lehre in ein Ledger; in neuer Session wird die Lehre injiziert → Agent macht den Fehler NICHT wieder. **Confidence hängt an echtem Test-Outcome (pass/fail), nicht an LLM-Meinung** — genau das können ChatGPT/Claude-Memory NICHT.
- **Wow (unfälschbar):** rot→grün pytest live im Video, echtes Testlog im Bild.
- **Fit:** Python/Automatisierung/strikte Konventionen (Michael dogfooded authentisch).
- **Risiko:** RISKY = Scope-Risiko (sauberes A/B nötig: Lauf 1 frischer Kontext OHNE Lehre = rot, Lauf 2 frischer Kontext MIT Lehre = grün).

## 🥈 Runner-up (82.5/81.5): Palimpsest / Aletheia — Belief-Revision-Gedächtnis
Persönliches Fakten-Gedächtnis, das Widersprüche im Write-Path erkennt, den veralteten Fakt sichtbar **tombstoned** (deprecated + Audit-Trail statt Hard-Delete) und beweisbar nie wieder ausgibt (z. B. Stundensatz 95€→80€). **GO statt RISKY** = sicherer/einfacher, gleiche wiederverwendbare Engine. Die „eine-Achse-ändern"-Alternative.

## Gemeinsame Basis (beide)
markmem-Engine wiederverwenden (vector_store + reranker + Fusion-Retrieval), Embedding-Slot bge-m3 → **Qwen text-embedding-v4**, qwen-plus/max via dashscope-intl (schon verdrahtet in `backend/qwen_client.py`). FastAPI + SQLite, Deploy Alibaba ECS. Neuer ~50-Zeilen Confidence-Updater (Beta/Bayes aus echtem Outcome) — `confidence_loop.py` NICHT wiederverwenden (macht keine Auto-Updates).

## MVP-Scope (Sieger)
EIN Ingest-Pfad (pytest-Ergebnis + Diff), EIN Agent (Claude Code via 1 MCP-Tool), EIN Demo-Repo, EIN Fehler-Muster (fehlender tenant_id-Filter). Qwen-Schicht als dünnste Slice zuerst isoliert bauen. Airtight A/B-Harness = Kern-Deliverable. Pflicht-Artefakte: Architektur-Diagramm, LICENSE (da), Public-Repo, ~3-Min-Demo, Deploy-Beweis-Screencast.

## Demo-Drehbuch (3 Min, grob)
0:00 Problem (Agenten wiederholen Fehler) · 0:15 Lauf 1: Test ROT → Mensch fixt → Qwen destilliert Lehre → Ledger · 0:45 Kontext killen (neue Session) · 1:00 Lauf 2: Lehre injiziert → Agent fixt beim 1. Versuch → GRÜN → Confidence 0.5→0.8 · 1:35 A/B-Callout (einziger Unterschied = injizierte Tokens) · 2:00 Stretch: Lehre wird OBSOLETE nach Refactor · 2:35 Schluss: Qwens 3 Rollen + „deployed auf Alibaba" + GitHub-Link.

## Day-1-Risiken
1. Alibaba ID-Verify (✅ inzwischen erledigt). 2. Modell-Verfügbarkeit dashscope-intl (qwen-plus/max + text-embedding-v4) → Tag 1 smoke-testen. 3. Reuse schmaler als Pitch (markmem hat 0 qwen-Refs → Qwen-Wiring ist net-new).

## OFFEN: Michael wählt Richtung → dann voller Bau-Plan im Plan-Mode.
