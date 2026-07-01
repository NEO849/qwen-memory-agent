"""Dünner Wrapper um Qwen (Alibaba Model Studio / DashScope) im OpenAI-kompatiblen Modus.

Idee-unabhängig: das brauchen wir in JEDER Variante. `python -m backend.qwen_client`
macht einen Verbindungstest, sobald der API-Key gesetzt ist.
"""
from __future__ import annotations

import json

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


def chat_json(messages: list[dict], model: str | None = None, **kwargs) -> dict:
    """Chat-Completion, die garantiert JSON zurückgibt (Qwen role 1: lesson distillation).

    Nutzt response_format=json_object. Robust: fällt der Provider auf Text zurück, wird
    das erste balancierte JSON-Objekt aus der Antwort geparst statt hart zu werfen.
    """
    resp = _client().chat.completions.create(
        model=model or config.QWEN_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        **kwargs,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Embedde Texte über Qwen (role 2: retrieval). Gibt eine Liste 1024-dim Vektoren zurück,
    Reihenfolge wie die Eingabe. Leere Eingabe → []."""
    if not texts:
        return []
    resp = _client().embeddings.create(
        model=model or config.QWEN_EMBED_MODEL,
        input=texts,
    )
    # Nach Index sortieren — die API garantiert Reihenfolge, wir erzwingen sie defensiv.
    items = sorted(resp.data, key=lambda d: d.index)
    return [item.embedding for item in items]


if __name__ == "__main__":
    # Verbindungstest gegen Qwen — erst nach ID-Verify + API-Key + Credits sinnvoll.
    print(f"Endpoint: {config.QWEN_BASE_URL}")
    print(f"Modell:   {config.QWEN_MODEL}")
    answer = chat([{"role": "user", "content": "Antworte mit genau einem Wort: OK"}])
    print(f"Qwen sagt: {answer!r}")
