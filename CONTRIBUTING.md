# Contributing to Regress-Guard

Thanks for looking! Regress-Guard is a memory for AI coding agents whose confidence is earned
from real test outcomes. Contributions that keep that honesty bar are very welcome.

## Setup
```bash
git clone https://github.com/NEO849/qwen-memory-agent && cd qwen-memory-agent
python -m venv .venv && . .venv/bin/activate
pip install -e . && pip install pytest
regress-guard doctor            # sanity: deps, hosted cloud, MCP tool
pytest -q                       # the suite runs offline (live-marked tests are skipped)
```
A `DASHSCOPE_API_KEY` in `.env` is only needed to run the backend or the benchmark yourself; the
hosted MCP path needs no key.

## Ways to help (good first issues)
- **Add a bug-class pattern** to the benchmark — this is the most valuable and the easiest to
  review. Copy a folder under `harness/patterns/<name>/` (`spec.py`, `variant.py`,
  `floor_solution.py`, `ceiling_solution.py`, `test_hidden.py`, `test_unseen.py`), then add the
  name to `CLASSES` in `harness/benchmark.py`. Rule: the *naive* answer must be wrong and the
  fix must be a convention that only memory supplies. Verify `floor`=RED / `ceiling`=GREEN first.
- Improve poisoned-memory defenses (`tests/test_injection_defense.py`).
- Frontend polish on the deck / globe / receipts strip.

## House rules
- **Honesty first.** Never claim an effect the numbers don't show; report negative results (we
  do — see the rerank ablation in `docs/benchmark.md`). Add a test with every behavior change.
- Keep the happy path of `backend/qwen_client.py` byte-identical; new Qwen stages go behind an
  env flag (see the `RG_*` flags in `backend/config.py`), defaulting off.
- Run `pytest -q` green before opening a PR; note what you verified.
