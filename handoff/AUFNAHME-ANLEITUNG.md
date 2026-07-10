# 🎬 Aufnahme-Anleitung — Video-Clips + Screenshots (Mac-Session)

> **Ziel:** In *einer* Sitzung im Mac-Browser (Chrome/Safari) alles aufnehmen, was ich fürs Video
> schneide **und** die aktuellen README/Devpost-Bilder brauche. Der Globus rendert im echten Browser
> mit GPU viel schöner als bei mir headless — deshalb machst *du* diese Aufnahmen.
>
> **Sprache im Video: ENGLISCH.** Die gesprochenen Sätze stehen in `docs/DEMO_SCRIPT_v3.md` (EN =
> sprechen, 🇩🇪 = nur zum Üben). Diese Anleitung sagt dir, **was du auf dem Bildschirm zeigst** — den
> Ton lege *ich* drüber (VO liegt fertig in `handoff/video/audio/voice_2/`).

---

## 0) Einmal vorbereiten (5 Minuten, wichtig!)
1. Seite öffnen: **regressguard.duckdns.org** — Chrome/Safari, Fenster groß (mind. 1500 px breit).
2. **Hart neu laden** (⌘⇧R) → sie landet auf **🏆 Proof** und der Globus lädt rechts.
3. Damit der gespeicherte Proof sauber `0/5 → 5/5` zeigt, lass mich vorher **einmal** den A/B-Lauf
   frisch machen (sag mir kurz Bescheid, ich mach das per Befehl — dauert 1 Min).
4. Rechts oben im „living memory"-Panel **einmal „Measure"** klicken → echte Zahlen erscheinen.
5. **Bildschirmaufnahme:** `⌘⇧5` → „Ausgewählten Bereich aufnehmen" → nur das Browser-Fenster.
   Screenshots: `⌘⇧4` → Bereich ziehen (landet auf dem Schreibtisch).

---

## 📹 TEIL A — die 8 Video-Clips
> Jeder Clip: **8–15 Sekunden**, ruhige Mausbewegung, keine Hektik. Keine Sorge um perfekt — ich
> schneide, beschleunige Wartezeiten und lege den Ton drüber. Nummeriere die Dateien `01`…`08`.

| # | Was du zeigst | Tab / Aktion |
|---|---|---|
| **01 · Hook** | Proof mit **0/5 vs 5/5** schon sichtbar, kurz auf die 5/5 halten | **🏆 Proof** |
| **02 · Problem** | Zur Chat-Ansicht wechseln, Globus rechts sichtbar | **💬 Chat** |
| **03 · Qwen ruft selbst** | Eine Coding-Frage tippen (z. B. *"how do I paginate safely?"*), abschicken → der Streifen **„🔧 Qwen called recall(…) → answered using N lessons"** erscheint, Globus-Knoten pulsieren | **💬 Chat** |
| **04 · Money-Shot** | Auf eine **grüne, verdiente** Karte im Deck zeigen (Confidence ~0.86), dann auf eine **graue, getombstonte** (vergessene) | Deck links / Globus |
| **05 · Beweis** | **🏆 Proof** „**Replay the proof**" klicken → 0/5→5/5 läuft ab. *(Optional mutiger: ⚔️ Duel → „Run 5 live".)* | **🏆 Proof / ⚔️ Duel** |
| **06 · 🕐 Zeitreise (NEU!)** | Am Globus den **Zeit-Slider unten** langsam nach links ziehen → Wissensbasis **schrumpft** (Mai), dann zurück nach rechts → **wächst auf 66** (jetzt). Label „order & tombstones real" kurz sichtbar | Globus rechts |
| **07 · MCP-Terminal** | *(mache ich für dich)* — ich nehme `python -m harness.mcp_vignette` als Terminal-Clip auf und gebe ihn dir; du musst hier nichts tun | — |
| **08 · Close** | Zurück auf **🏆 Proof**, `0/5 → 5/5` als letztes Bild ruhig halten | **🏆 Proof** |

**Clip 06 ist der neue Star** — der Zeitslider ist die Innovation, die Zep/Graphiti sonst nur teuer
verkaufen. Zieh ihn ruhig 2–3× hin und her, damit man das Wachsen/Vergessen klar sieht.

---

## 📸 TEIL B — die Screenshots (für README + Devpost)
> `⌘⇧4`, Bereich ziehen. Schick sie mir, **ich baue sie an die richtigen Stellen** in README/Devpost
> ein und lege sie in `docs/media/`. Fenster **mind. 1500 px breit** für die 3-Spalten-Ansicht.

| Datei-Idee | Ansicht | Ersetzt |
|---|---|---|
| `proof-globe` | **🏆 Proof**, volle 3-Spalten-Ansicht (Deck · 0/5→5/5 · Globus+Slider) | `docs/media/proof-globe.png` |
| `living-memory` | **💬 Chat**, 3 Spalten (Deck · Chat · Globus) | `docs/media/living-memory.png` |
| `globe` | Globus **Vollbild** — Slider einmal nach **links** gezogen (zeigt Zeitreise) | `docs/media/globe.png` |
| `function-calling` | **💬 Chat** mit dem „🔧 Qwen called recall(…)"-Streifen sichtbar | `docs/media/function-calling.png` |

> Tipp: Für `globe` den Globus einmal mit der Maus so drehen, dass die farbigen Knoten schön
> verteilt in der Mitte sind — dann ⌘⇧4.

---

## Danach
Schick mir **die 8 Clips + 4 Screenshots** (oder leg sie in `handoff/video/incoming/`). Dann:
1. Ich **schneide das Video** (<3:00, 1080p, Ton drüber) → `out/regress-guard-final.mp4`.
2. Ich **baue die Screenshots** in README + Devpost ein und pushe.
3. Du lädst das Video auf **YouTube** (Public, „not made for kids") → schickst mir den Link.
4. **Devpost-Submit** (Video-Link + „I agree") — nur mit deinem OK.

Das ist der letzte Schritt zum Sieg. 🚀
