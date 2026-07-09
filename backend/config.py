"""Zentrale Konfiguration — liest Secrets/Endpoints aus der Umgebung (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
QWEN_BASE_URL = os.environ.get(
    "QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")

# Embedding (Qwen role 2: retrieval). text-embedding-v4 → 1024-dim vectors, verified working.
QWEN_EMBED_MODEL = os.environ.get("QWEN_EMBED_MODEL", "text-embedding-v4")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))

# Live ledger location. Injectable so the A/B harness can point at a throwaway DB
# (hard isolation boundary — the interactive layer must never touch a harness run).
LEDGER_PATH = os.environ.get("LEDGER_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ledger.sqlite"
))

# Self-tuned retrieval fusion weights live next to the ledger (written by evaluation.tune()).
RETRIEVAL_CONFIG = os.path.join(os.path.dirname(LEDGER_PATH), "retrieval_config.json")

# Optional behaviours, default OFF so the A/B proof + existing tests are unaffected.
RG_DEDUP = os.environ.get("RG_DEDUP", "0") == "1"            # merge near-duplicate lessons on teach
RG_DECAY_ENABLED = os.environ.get("RG_DECAY_ENABLED", "0") == "1"   # time-decay confidence at recall
RG_DEDUP_THRESHOLD = float(os.environ.get("RG_DEDUP_THRESHOLD", "0.92"))
RG_DECAY_HALFLIFE_DAYS = float(os.environ.get("RG_DECAY_HALFLIFE_DAYS", "30"))

# Associative memory (brain-like), safe + additive — they grow/traverse the synapse graph but
# NEVER touch a lesson's confidence (that stays earned from real tests).
RG_HEBBIAN = os.environ.get("RG_HEBBIAN", "1") == "1"        # co-recalled lessons wire together
RG_HEBBIAN_DELTA = float(os.environ.get("RG_HEBBIAN_DELTA", "0.10"))  # synapse growth per co-recall
RG_HEBBIAN_TOPN = int(os.environ.get("RG_HEBBIAN_TOPN", "3"))       # top-N co-recalled to wire
RG_SPREAD = os.environ.get("RG_SPREAD", "0") == "1"          # spreading-activation recall (opt-in)
RG_SPREAD_K = int(os.environ.get("RG_SPREAD_K", "2"))               # extra associative neighbours

# --- Final-Sprint Qwen-Tiefe: neue Stufen hinter Flags, Default OFF (staging-first, ein-Befehl-Kill).
# Jede Stufe MUSS bei Flag-OFF exakt auf das heutige Verhalten degradieren (Baseline = v-baseline-2026-07-09).
RG_RERANK = os.environ.get("RERANK_ENABLED", "0") == "1"     # qwen3-rerank als Cross-Encoder-Endstufe von RECALL
RG_RERANK_MODEL = os.environ.get("RERANK_MODEL", "qwen3-rerank")
RG_RERANK_TOPN = int(os.environ.get("RERANK_TOPN", "5"))            # rerank-Kandidaten -> top_n zurueck
RG_RERANK_BUDGET_MS = int(os.environ.get("RERANK_BUDGET_MS", "400"))  # p95-Latenzbudget-Gate (Doku/Guard)
RG_STREAMING = os.environ.get("STREAMING_ENABLED", "0") == "1"   # Token-Streaming (SSE) fuer Chat/REVISE
RG_TOOL_LOOP = os.environ.get("TOOL_LOOP_ENABLED", "0") == "1"   # bounded Multi-Step-Tool-Loop im Chat
RG_TOOL_LOOP_MAX = int(os.environ.get("TOOL_LOOP_MAX", "3"))        # harte Obergrenze der Tool-Runden


def assert_configured() -> None:
    """Früh und klar scheitern, wenn der Key fehlt — statt kryptischer 401 später."""
    if not DASHSCOPE_API_KEY:
        raise RuntimeError(
            "DASHSCOPE_API_KEY fehlt. Lege .env aus .env.example an und trage den "
            "Key aus Alibaba Model Studio ein."
        )
