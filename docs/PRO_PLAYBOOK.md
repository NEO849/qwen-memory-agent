# Regress-Guard — Pro-Playbook zum Sieg (Experten-Synthese, 2026-07-07)

Vier Elite-Jury-Rollen haben den Code unabhängig geprüft (je eine Achse: Technik 30 · Innovation 30 ·
Impact 25 · Präsentation 15). Alles hier ist **ehrlich + in ~2 Tagen machbar** — nichts Erfundenes.
Reihenfolge = Impact × Machbarkeit. ✅ = in dieser Session erledigt · 🔓 = offen/braucht User (Deploy/Video).

## 0. Der eine kritische Fund (3 von 4 Juroren, #1)
Der Kron-Beweis `0→100%` stand auf einem **`used_fallback`**: Arm B injizierte den gemerkten Fix in
kanonischer Form; der *echte* Auto-Distillations-Pfad war nie gemessen. Ein Juror sieht das in der JSON
in 10 Sekunden und es trifft genau unsere Ehrlichkeits-These.
- ✅ **Fix gebaut:** 3-Arm-A/B (`harness/ab_runner.py`) — A (kein Memory) · B (gemerkter Entwickler-Fix,
  Headline, stabil) · **B-live (echte Auto-Distillation, offengelegt)** + Wilson-95%-Konfidenzintervalle.
- ✅ **Ehrlicher Befund gemessen:** Die Auto-Distillation ist das *schwankende* Glied (mal 100 %, mal 0 %),
  nicht Recall/Confidence. Das ist jetzt **gemessen & offengelegt**, nicht versteckt — aus Schwäche wird Beleg.

## 1. Technik (30 %)
1. ✅ **3. A/B-Arm „B-live" + Wilson-CI** — der echte Pipeline-Output wird gemessen (s. #0). Höchster Hebel.
2. ✅ **Concurrency-Test** (`tests/test_concurrency.py`) — 8 Prozesse × 25 Writes auf dieselbe Lektion →
   exakt `alpha = 1 + 200`, kein Lost Update. Beweist den atomaren In-SQL-Beta-Increment als echte
   Systems-Eigenschaft (billigster hochwertiger Move).
3. ✅ **Kalibrierung + Konvergenz** (`tests/test_calibration.py`) — Beta-Confidence konvergiert gegen die
   *wahre* Pass-Rate (|Δ|<0.03) und ist kalibriert (ECE<0.06 über 4000 simulierte Lektionen). Die
   messbare Eigenschaft, die reine Vektor-Suche strukturell nicht hat.
4. 🔓 **Self-Tune mit Train/Val-Holdout** (`backend/evaluation.py::tune`) — aktuell auf demselben Gold
   gemessen, aus dem es wählt (Overfitting-Angriff). Split train/val, adoptiere nur wenn val-Recall besser.
   *Aufwand S, offen.*
5. 🔓 **Retrieval-Skalierungs-Benchmark** — Latenz vs. N (100/1k/10k) + BM25-Index-Cache. Systems-Tiefe. *M, offen.*

## 2. Innovation (30 %)
- **Geschärfte Neuheits-These (skeptiker-fest):** „Das erste Agenten-Gedächtnis, dessen Lektionen
  *falsifizierbar* sind: jede Lektion ist eine Vorhersage, deren Gewicht ein Beta-Posterior über echte
  pytest-Ausgänge ist — die Realität widerlegt oder bestätigt sie, Widerlegtes tombstoned sich selbst.
  RAG *kann nicht falsch sein*, weil es keine Behauptung aufstellt. Wir haben einen Write-Back-Loop aus
  Konsequenzen." → **so gegen „ist doch nur Vektor-Suche" antworten** (Retrieval offen als Commodity
  einräumen, Neuheit = der geschlossene Kausal-Loop).
- ✅ **Kalibrierungs-Kurve/ECE** (s. Technik #3) = die härteste Waffe gegen den Vektor-Suche-Einwand.
- ✅ **Assoziatives, gehirn-*inspiriertes* Gedächtnis** (`tests/test_associative_memory.py`): (a) **Hebbian-Synapsen**
  — gemeinsam erinnerte Lektionen verdrahten sich (Kantengewicht wächst mit Co-Recall, gedeckelt);
  (b) **Spreading-Activation-Recall** (opt-in) — erinnert assoziativ über die stärksten Synapsen
  Nachbarn, die reine Suche verpasst. Ehrlich als *associative memory / Hebbian wiring / spreading
  activation* benannt (NICHT Bewusstsein/AGI); berührt **nie** die Confidence (bleibt test-verdient).
- 🔓 **Poisoned-Lesson-Selbstheilung als 30-Sek-Live-Demo:** vergiftete Lektion lehren → 3 rote Läufe →
  Confidence fällt → Auto-Tombstone → grün. Verknüpft Sanitizer + Bayes-Demotion + Tombstone zu einem
  Atemzug. *S, offen (Choreografie existierender Mechanismen).*
- 🔓 **Per-Lektion Beta-Verlauf-Drilldown** (Klick auf Globus-Knoten → Posterior-Zeitreihe). *S–M, offen.*

## 3. Impact (25 %)
- **Nutzer/Schmerz:** Agent-Operator/Platform-Team, dessen langlebiger Coding-Agent über Sessions einen
  bereits gefixten Bug (hier: Cross-Tenant-Leck = Security-Incident/DSGVO) wieder einbaut.
- 🔓 **#1 Echte MCP-Session mit FREMDEM Agenten** (Claude Code/Qwen Code, 3-Zeilen-`.mcp.json` → deployte
  ECS-Memory): Session 1 baut Bug → Test rot → Fix → `record()`. Session 2 (frischer Kontext) → `recall()`
  → Bug kommt NICHT zurück. 60–90-s-Terminal-Screencast. **Der einzige Beweis „Werkzeug, kein Demo", den
  ein Dev-Tools-Juror glaubt.** *M, braucht User-Hände fürs Recording.*
- ✅ **2.–3. reales Bug-Muster im A/B** (`harness/generalization.py`) — GENERALISIERUNG über **3 Bug-Klassen**
  gemessen: Memory kippt die 2 Klassen, die das Basismodell falsch macht (tenant isolation, pagination
  leak) von **0/3 → 3/3**; bei money_rounding schreibt Qwen den Code schon selbst korrekt (floor 3/3) →
  Memory fügt **keinen** Schein-Lift hinzu und schadet nicht (3/3). Zwei unabhängige 0→100-Flips töten
  Cherry-Pick, das dritte zeigt: Gedächtnis ist harmlos wenn nicht gebraucht. Auto-Distiller 18/18
  (Wilson95 82–100%). money_rounding **nie** als Memory-Gewinn verkaufen.
- ✅ **Statistische Zahl + CI** — `+100 Punkte Pass-Rate, Wilson-95%-CI` liegt jetzt vor (systemeigen, reproduzierbar).

## 4. Präsentation (15 %)
- ✅ **Globus dichter & vollständiger** (dein Wunsch): Seed 15 → **66 Knoten**, 30 → **196 Kanten**, jetzt
  *alle* Kanten-Typen sichtbar (`related` 179 · `synthesizes` 16 · `supersedes` 1) + 3 Anti-Pattern-Knoten
  (dunkelrot) + 1 vergessener Knoten (grau) + echte Qwen-Synthese-Meta-Lektionen. Orphans 29 %→**~3 %**.
  Kantenstärke aus Embedding-Cosinus initialisiert, Hebbian-Co-Recall verstärkt *zusätzlich* die co-feuernden Synapsen. Jede Lektion = echte Coding-Regel.
- ✅ **Live-URL öffnet auf dem 🏆 Proof + Auto-Play** — HTML landet auf der Proof-View, JS spielt das
  Rennen einmal ab (Playwright-verifiziert: 0/5→5/5, kein Konsolenfehler). Chat 1 Klick entfernt.
- 🔓 **Erste 5 Sekunden polieren:** Proof-Pille startet mit echtem Wert statt `loading…`; Intro auf einen
  Satz; `proofHero` sichtbar. *S, offen.*
- 🔓 **Globus-Feinschliff:** Rest-Orphans als bewusster Amber-„candidate"-Ring + Legenden-Zeile
  „Größe = Belege (α+β)" + Kamera-Fit beim Laden + etwas schnellerer Spin. *S, offen.*
- **Video-Story-Kurve:** vor dem Fix 2–3 s **den Schmerz zeigen** (roter Bug taucht in „frischer Session"
  wieder auf), dann Erlösung. Rest des Skripts ist juryreif.

## Was JETZT dein OK braucht (Reihenfolge)
1. **Redeploy** mit dem angereicherten Globus (66 Knoten) + ehrlichem A/B + assoziativem Gedächtnis — 1 reproduzierbarer Befehl.
2. Danach frei wählbar: Präsentations-Quick-Wins (Proof-Landing, Globus-Feinschliff), 2. Bug-Muster,
   echte MCP-Fremd-Session fürs Video.
3. Zuletzt (deine Hände): 🎬 Video · 🌐 Repo public · ✅ Devpost submit.
