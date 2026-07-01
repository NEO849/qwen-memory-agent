"""Zentrale Konfiguration — liest Secrets/Endpoints aus der Umgebung (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
QWEN_BASE_URL = os.environ.get(
    "QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")


def assert_configured() -> None:
    """Früh und klar scheitern, wenn der Key fehlt — statt kryptischer 401 später."""
    if not DASHSCOPE_API_KEY:
        raise RuntimeError(
            "DASHSCOPE_API_KEY fehlt. Lege .env aus .env.example an und trage den "
            "Key aus Alibaba Model Studio ein."
        )
