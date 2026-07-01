# Architektur

> Platzhalter — wird nach dem Idee-Lock (Plan-Mode) mit dem finalen Diagramm gefüllt.
> Das Diagramm (Qwen ↔ Backend ↔ DB ↔ Frontend) ist Pflicht-Bestandteil der Einreichung.

Grobskizze (vorläufig):

```
[Frontend: Chat-UI]
        │  HTTP
        ▼
[Backend: FastAPI]  ──►  [Memory-Layer: SQLite + Retrieval]
        │                        ▲
        │  OpenAI-kompatibel     │ (Erinnerungen: schreiben, suchen, korrigieren, vergessen)
        ▼                        │
[Qwen Cloud / Model Studio] ─────┘
```
