"""LLM provider abstraction — switch providers with an env var, zero code change.

LLM_PROVIDER=ollama  (default, local, free)
LLM_PROVIDER=openai  (requires OPENAI_API_KEY)
"""

import os

import requests

PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _generate_ollama(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _generate_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


_PROVIDERS = {"ollama": _generate_ollama, "openai": _generate_openai}


def generate(prompt: str) -> str:
    try:
        fn = _PROVIDERS[PROVIDER]
    except KeyError:
        raise RuntimeError(f"Unknown LLM_PROVIDER '{PROVIDER}'. Options: {list(_PROVIDERS)}")
    return fn(prompt)
