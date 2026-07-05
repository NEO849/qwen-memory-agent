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


def assert_configured() -> None:
    """Früh und klar scheitern, wenn der Key fehlt — statt kryptischer 401 später."""
    if not DASHSCOPE_API_KEY:
        raise RuntimeError(
            "DASHSCOPE_API_KEY fehlt. Lege .env aus .env.example an und trage den "
            "Key aus Alibaba Model Studio ein."
        )
