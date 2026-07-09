# Roadmap

Regress-Guard is a working v0.1.0 (see [CHANGELOG](CHANGELOG.md)). What's next, roughly in
order — honest about what's proven vs. planned.

### Near term
- **Publish to PyPI** so adoption is literally `uvx regress-guard mcp` / `pip install regress-guard`
  (packaging is in `pyproject.toml`; the console script and `doctor` already work locally).
- **Grow the benchmark** from N=50 toward N≥200 (more bug classes, more seeds) so the earned-vs-
  add-only result moves from directional (McNemar p≈0.0625) to conventionally significant. See
  [`docs/benchmark.md`](docs/benchmark.md).
- **Example repos + transcripts** showing the recall→record self-heal loop inside Claude Code
  and Cursor, re-runnable by anyone.

### When a memory gets large
- **Turn on `qwen3-rerank`** once retrieval quality actually needs it — today RRF already ranks
  the right lesson (~0.95 MRR) so reranking adds latency without lift; it's built and flag-gated,
  waiting for the scale where it pays off.
- **ANN candidate generation** to replace the O(N²) association step (cosine top-M → O(N·M)),
  with a benchmark at N=1k/10k.

### Product
- Enable **token streaming** and the **multi-step tool loop** on the hosted demo once the
  latency budget on a multi-worker deployment is confirmed.
- A hosted, per-session **sandbox** so anyone can seed a wrong lesson and watch it get tombstoned.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
