"""LLM call (architecture §5.7). Provider is swappable — one function.

Reads .env (python-dotenv) for LLM_API_KEY / LLM_MODEL / LLM_BASE_URL.
Default endpoint is OpenAI-compatible chat completions, so ANY instructor-allowed
provider (OpenAI, Groq, Together, OpenRouter, a local vLLM/Ollama gateway, ...)
works by setting LLM_BASE_URL.
"""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

from rag_agent.paths import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
REQUEST_TIMEOUT_SEC = 120


def _api_key() -> str:
    key = os.getenv("LLM_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add an "
            "instructor-allowed OpenAI-compatible API key (or swap llm.complete "
            "for a local model, per architecture §10)."
        )
    return key


def complete(prompt: str) -> str:
    """One-shot completion. Returns the assistant text only."""
    model = os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODEL
    base_url = os.getenv("LLM_BASE_URL", "").strip() or DEFAULT_BASE_URL

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        },
        timeout=REQUEST_TIMEOUT_SEC,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"LLM request failed with HTTP {response.status_code}: "
            f"{response.text[:200]} — check LLM_API_KEY / LLM_MODEL / LLM_BASE_URL in .env"
        )
    return response.json()["choices"][0]["message"]["content"].strip()