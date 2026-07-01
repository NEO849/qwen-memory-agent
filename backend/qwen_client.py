"""Dünner Wrapper um Qwen (Alibaba Model Studio / DashScope) im OpenAI-kompatiblen Modus.

Idee-unabhängig: das brauchen wir in JEDER Variante. `python -m backend.qwen_client`
macht einen Verbindungstest, sobald der API-Key gesetzt ist.
"""
from __future__ import annotations

from openai import OpenAI

from . import config


def _client() -> OpenAI:
    config.assert_configured()
    return OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.QWEN_BASE_URL)


def chat(messages: list[dict], model: str | None = None, **kwargs) -> str:
    """Eine Chat-Completion an Qwen. `messages` = OpenAI-Format [{role, content}, ...]."""
    resp = _client().chat.completions.create(
        model=model or config.QWEN_MODEL,
        messages=messages,
        **kwargs,
    )
    return resp.choices[0].message.content or ""


if __name__ == "__main__":
    # Verbindungstest gegen Qwen — erst nach ID-Verify + API-Key + Credits sinnvoll.
    print(f"Endpoint: {config.QWEN_BASE_URL}")
    print(f"Modell:   {config.QWEN_MODEL}")
    answer = chat([{"role": "user", "content": "Antworte mit genau einem Wort: OK"}])
    print(f"Qwen sagt: {answer!r}")
