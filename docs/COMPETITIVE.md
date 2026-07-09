# Wettbewerbs- & Gewinner-Analyse — Regress-Guard (Qwen Cloud Hackathon, Track MemoryAgent)

> Quelle: dedizierter Markt-/Wettbewerbs-Analyst (WebSearch, 29 Tool-Uses, quellenbelegt), 2026-07-10.
> Gesamt-Confidence des Reports: 62%. Burggraben-Behauptung: 65% (im Pitch **hedgen** — "kein *bekanntes* Framework", nicht "niemand").

## Kernbefund
Kein existierendes AI-Memory-Framework (Mem0, Zep/Graphiti, Letta/MemGPT, Cognee) verankert Lesson-Konfidenz in **echten Code-Execution-Outcomes** (pytest pass/fail) mit **Tombstoning**. Das nächstliegende Stück (TDAD, arXiv 2603.17973) ist test-gegründet, aber **zustandslos** pro PR — keine persistente, Bayesianisch über Sessions aktualisierte Beta-Konfidenz.

## Burggraben (die eine unbesetzte Dimension)
**Persistente, sessionübergreifende Lesson-Konfidenz, Bayesianisch aktualisiert durch echte `pytest`-Pass/Fail-Ereignisse** (nicht LLM-Meinung, nicht Recency, nicht Nutzer-Feedback), **mit automatischem Tombstoning**, wenn eine vormals bestätigte Lektion an neuem Code scheitert.

Alle vier großen Frameworks erden Vertrauen auf etwas anderes. Kritische Einschränkung: closed-source Coding-Agenten (Cursor, Devin, Windsurf, Copilot Workspace) sind nicht einsehbar; das arXiv-Cluster zu Memory-Forgetting bewegt sich schnell (mehrere Papers/Woche, Juni 2026). Confidence **65% unbesetzt**.

## Konkurrenz-Tabelle

| Tool | Grounding-Signal | Forgetting-Mechanismus | Benchmark zitiert | Bekannte Schwäche |
|---|---|---|---|---|
| **Mem0** | LLM-Judge (ADD/UPDATE/DELETE-Routing), keine Test-Verankerung | Contradiction-triggered Overwrite (LLM entscheidet), kein User-Forget-Primitiv | LoCoMo (67–92.5%), LongMemEval (94.4%), BEAM | Konfidenz = LLM-Meinung über "ist das noch wahr", nie durch reale Ausführung geprüft |
| **Zep/Graphiti** | Bitemporal (event- vs. ingestion-time) — Recency/Gültigkeit, kein Truth-Check | Edge-Invalidierung bei neuem widersprechendem Fakt (zeitlich) | DMR (94.8%), LongMemEval (+18.5% vs. Baseline) | Stark bei "neuester Fakt", blind ob eine Coding-Regel tatsächlich funktioniert |
| **Letta/MemGPT** | Keine explizite Konfidenz — Agent verwaltet Memory-Blocks per Tool-Calls | Passiv ("forgetting requires actively not calling the tools"), kein Auto-Verfall | Eigenes Leaderboard, kein publizierter LongMemEval-Wert | Kein probabilistisches Vertrauensmaß; Qualität hängt am Prompt-Engineering |
| **Cognee** | Graph + `feedback_weight`/`frequency_weight` (Nutzer-Feedback/Zugriff) | Kein Auto-Decay/TTL; expliziter `forget()`-Aufruf | HotPotQA/2WikiMultiHop/MuSiQue, BEAM (SOTA @100k) | Korrektheit per LLM-Judge (DeepEval), nicht per echtem Programmlauf |
| *(Adjacent)* **TDAD** | Test-Dependency-Map pro PR, `pytest`-basiert | — (keine persistente Memory) | SWE-bench Verified (Regression 6.08%→1.82%) | Zustandslos: kein akkumuliertes, Bayesianisch aktualisiertes Konfidenzmaß, kein Tombstoning |
| *(Forschung)* **ForgetEval** | — (Fokus Löschanfragen/GDPR) | Deletion/Supersede/Purge-Hooks | ForgetEval (1000+385 Fälle) | Belegt "production failures = forgetting failures" — **stützt unsere These indirekt** |

## Gewinner-Muster (für die 4 Jury-Achsen)
- Rubrik wörtlich: "sophisticated use of APIs" + "algorithmic or engineering innovation through novel solutions, custom components, or performance optimization" + "authentic technical or business pain point" + "scalability potential for productization".
- Fünf-Achsen-Muster über 2025er AI-Hackathons: Idee/Wert · technische Tiefe/Architektur · ≥3 Sponsor-Tools *sinnvoll* genutzt · straffe 3-Min-Demo · Autonomie/Selbstkorrektur des Agenten.
- **Domain-Pain-Point schlägt reine Tech-Demo** (ein Anwalt gewann Anthropics Hackathon gegen 500 Entwickler mit einer echten Live-Demo statt Tech-Neuheit).
- **Regress-Guard-Fit:** Alle vier Achsen bereits konkret bedient (Qwen 5-Rollen, Live-Deploy Alibaba ECS, A/B + N=50 3-Arm-Benchmark + Ablations, MCP-Drop-in). Lücke = "Technical Depth" durch **Benchmark-Skalierung**, nicht durch neue Features.

## Selbstbeweis-Tests (priorisiert Glaubwürdigkeit ÷ Aufwand)
1. **LongMemEval-N skalieren** (N=3→≥30/78) — der einzige extern zitierte Wert wird statistisch tragfähig. Aufwand niedrig (Skript da), Gewinn **sehr hoch**. → *läuft gerade*.
2. **Poison-Demotion-Kurve** — Beta-Posterior-Mean pro Fehlschlag-Trial bis unter Gate 0.62 → Tombstone. Aufwand niedrig-mittel, Gewinn **sehr hoch**. Macht die Kern-These *numerisch* statt binär.
3. **Gate-Schwellen-Sensitivitätssweep (0.3–0.9)** — entkräftet "0.62 ist gecherrypickt". Aufwand niedrig-mittel, Gewinn hoch.
4. **Kalibrierungskurve (Reliability-Diagram + Brier/ECE)** — behauptete Beta-Konfidenz vs. tatsächliche Out-of-Sample-Pass-Rate. Aufwand mittel, Gewinn hoch. *(genau der "behauptet vs. tatsächlich"-Beweis)*
5. **Multi-Session-Drift-Stresstest** — 15–20 Sessions, Lektion wird durch Refactor falsch, Demotion-Geschwindigkeit messen. Aufwand mittel-hoch.
6. **Cross-Temperatur-Distiller-Robustheit** — 10/10-Zuverlässigkeit bei Temp 0.3/0.5/1.0, gemeinsames Wilson-CI. Aufwand mittel.

Alle laufen gegen den eigenen gecachten Qwen-Harness — **kein Prod-Write, keine fremden Nutzer**.

## Quellen (Auswahl)
- https://qwencloud-hackathon.devpost.com/ (Rubrik, primär)
- https://info.devpost.com/blog/understanding-hackathon-submission-and-judging-criteria
- https://mem0.ai/research · https://mem0.ai/blog/state-of-ai-agent-memory-2026
- https://arxiv.org/abs/2501.13956 (Zep) · https://www.letta.com/blog/letta-leaderboard/
- https://www.cognee.ai/blog/deep-dives/knowledge-graph-memory-benchmarks
- https://arxiv.org/abs/2603.17973 (TDAD) · https://arxiv.org/abs/2606.15903 (ForgetEval)

## Auflage vor Pitch/README-Einbau
`skeptical-validator` gegen die Burggraben-Behauptung laufen lassen, bevor "einzigartig" formuliert wird. Aktuell 65% → im Text hedgen: **"kein bekanntes Framework"**, nicht "niemand".
