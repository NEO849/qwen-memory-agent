# 🎬 Video-Produktion — verbindliche Schritt-für-Schritt-Anleitung (Mac)

> **Die goldene Regel:** Du nimmst nur **stumme Bildschirm-Clips** auf. Den **Ton fasst du NICHT an** —
> die fertigen englischen Stimmen liegen in `handoff/video/audio/voice_2/` und **ich** lege sie unter
> deine Clips. Du sprichst nichts, Mikro aus. Perfekt muss nichts sein — ich schneide, raffe
> Wartezeiten, mache Übergänge, blende Ton + End-Karte ein.

## So teilt sich die Arbeit auf
| Du (Mac) | Ich (Server) |
|---|---|
| 8 stumme Clips + 4 Screenshots aufnehmen | Ton drunterlegen, schneiden, Timing, Übergänge |
| Dateien in `handoff/video/incoming/` legen | MCP-Terminal-Clip aufnehmen (mach ich) |
| Am Ende Video auf YouTube laden | qwen-max-`/telemetry`-Einblendung in Clip 07 einbauen (mach ich) |
| | Screenshots in README/Devpost einbauen + fertiges `out/regress-guard-final.mp4` |

---

## 0) Einmal vorbereiten (3 Min)
1. Browser (Chrome/Safari) auf **regressguard.duckdns.org**, Fenster **groß** (mind. 1500 px breit).
2. **Hart neu laden** (⌘⇧R) → Seite landet auf **🏆 Proof**, rechts lädt der Globus.
3. Lesezeichen-Leiste aus, sauberes Bild. **Der gespeicherte Proof zeigt schon `0/5 → 5/5`** — nichts
   muss frisch gerechnet werden (spart Kosten). Kein „Measure"-Klick nötig.
4. **Aufnahme-Werkzeug:** `⌘⇧5` → **„Ausgewählten Bereich aufnehmen"** → nur das Browser-Fenster →
   **Optionen: Mikrofon = Keine**. Screenshots: `⌘⇧4` → Bereich ziehen (landet auf Schreibtisch).

---

## 📹 TEIL A — die 8 Clips (jeder 8–15 Sek, ruhige Maus)
> **Benenne die Dateien nach dem Namen** (nicht nur Zahl) — dann kann beim Schneiden nichts vertauscht
> werden. Ablegen in `handoff/video/incoming/`.

| Datei | Was du zeigst | Tab / Aktion |
|---|---|---|
| **`01-hook`** | Proof mit **0/5 vs 5/5** sichtbar, ruhig auf die **5/5** halten | 🏆 Proof |
| **`02-problem`** | Zur Chat-Ansicht wechseln, Globus rechts sichtbar, ruhig draufhalten | 💬 Chat |
| **`03-qwen-calls`** | Coding-Frage tippen (*„how do I paginate safely?"*) → Send → warten bis der Streifen **„🔧 Qwen called recall(…) → answered using N lessons"** erscheint + Globus-Knoten **pulsieren** | 💬 Chat |
| **`04-money`** | Im Deck links auf eine **grüne, verdiente** Karte zeigen (Confidence ~0.86), dann auf eine **graue, getombstonte** (vergessene) Karte | Deck links |
| **`05-proof`** | **„Replay the proof"** klicken → `0/5 → 5/5` + `+100%` **ganz** durchlaufen lassen. *(Mutiger optional: ⚔️ Duel → „Run 5 live")* | 🏆 Proof |
| **`06-timetravel`** ⭐ | Am Globus den **Zeit-Slider unten** langsam nach **links** ziehen → Wissensbasis **schrumpft** (Mai), dann nach **rechts** → **wächst** (heute). 2–3× hin und her. | Globus rechts |
| **`07-architecture`** | Das **Architektur-Diagramm** groß/Vollbild zeigen (`architecture/diagram.png`), ruhig draufhalten. *(Die qwen-max-Einblendung baue ICH ein — du musst kein `/telemetry` aufnehmen.)* | Diagramm-Bild |
| **`08-close`** | Zurück auf **🏆 Proof**, `0/5 → 5/5` als **letztes Bild** ruhig stehen lassen | 🏆 Proof |

> **`06-timetravel` ist der Star** — der Zeitslider ist die Innovation, die Konkurrenz (Zep/Graphiti)
> teuer verkauft. Deutlich hin/her ziehen, damit man Wachsen + Vergessen klar sieht.
>
> **Clip „MCP-Terminal" nimmst DU nicht auf — das mache ich** (`python -m harness.mcp_vignette`, Session 1
> ROT → Session 2 GRÜN). Ich füge ihn an der richtigen Stelle ein.

---

## 📸 TEIL B — 4 Screenshots (für README + Devpost)
> `⌘⇧4`, Bereich ziehen. Fenster **mind. 1500 px breit** (3-Spalten-Ansicht). Schick sie mir — **ich baue
> sie ein**.

| Datei-Name | Ansicht |
|---|---|
| `proof-globe` | 🏆 Proof, volle 3-Spalten (Deck · 0/5→5/5 · Globus+Slider) |
| `living-memory` | 💬 Chat, 3 Spalten (Deck · Chat · Globus) |
| `globe` | Globus **Vollbild**, Slider einmal nach **links** gezogen (zeigt Zeitreise) |
| `function-calling` | 💬 Chat mit sichtbarem „🔧 Qwen called recall(…)"-Streifen |

---

## So nimmst du EINEN Clip auf (Mac-Tasten)
1. Browser-Fenster **Vollbild**: **⌃ Control + ⌘ Command + F**.
2. **⌘⇧5** → „Ausgewählten Bereich aufnehmen" → Fenster wählen → **Mikrofon: Keine** → **Aufnehmen**.
3. Den Beat spielen (Klick/Warten laut Tabelle), Maus ruhig. **Animation ganz zu Ende laufen lassen.**
4. Stopp: **⌘ + ⌃ + Esc** (oder ⏹ oben in der Menüleiste).
5. Datei vom Schreibtisch nach `handoff/video/incoming/` legen, benennen wie in der Tabelle
   (`01-hook.mov`, `02-problem.mov`, …).

**Tipp:** Nimm jeden Clip ruhig **2–3 Sek länger** auf (Puffer vorn/hinten) — ich schneide passgenau.
Nicht getroffen? Einfach nochmal — ich nehme den besten.

---

## Danach — der Rest läuft über mich
1. Sag **„Clips liegen bereit"**. → Ich baue das Video: Ton-Sync · Wartezeiten raffen · Atempausen ·
   qwen-max-Einblendung (Clip 07) · MCP-Terminal · **keine Untertitel** (bewusst) · Loudnorm · End-Karte
   → **`out/regress-guard-final.mp4`** (<3:00, 1080p) + kurzer QC-Report.
2. Ich baue die **Screenshots** in README + Devpost ein und pushe.
3. **Du lädst das Video auf YouTube** (Sichtbarkeit: *Öffentlich*, „nicht für Kinder gemacht") → schickst
   mir den Link.
4. **Devpost-Submit** (Video-Link einbetten + „I agree" + Submit) — **nur mit deinem OK**, und erst wenn
   Repo public ist (ist es).

Das ist der letzte Schritt zum Sieg. 🚀
