"""Swappable LLM client, mirroring app/retriever/embed.py's Embedder pattern.

Two backends, selected by LLM_BACKEND in .env:
- "ollama" (default): local model on the user's GPU, reached over Tailscale.
  Free, but the host may be offline — callers must handle LLMUnavailable.
- "anthropic": hosted Claude, billed separately from a Claude Pro subscription.
"""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """The configured LLM backend could not be reached or failed to respond."""


class LLMClient(Protocol):
    def complete(self, system: str, message: str) -> str: ...


class AnthropicClient:
    def __init__(self, api_key: str, model: str, max_tokens: int = 4096):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, message: str) -> str:
        import anthropic

        try:
            response = self._client.messages.create(
                model=self._model, max_tokens=self._max_tokens,
                system=system, messages=[{"role": "user", "content": message}],
            )
        except anthropic.APIError as e:
            raise LLMUnavailable(f"Anthropic call failed: {e}") from e
        return "".join(b.text for b in response.content if b.type == "text")


class OllamaClient:
    """Talks to Ollama's native /api/chat endpoint (not the OpenAI-compat one)."""

    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def complete(self, system: str, message: str) -> str:
        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMUnavailable(
                f"Ollama at {self._base_url} unreachable (is the GPU host on and "
                f"exposed over Tailscale?): {e}"
            ) from e
        return resp.json()["message"]["content"]


def get_llm_client(settings) -> LLMClient | None:
    """Returns None when the configured backend has no usable connection info
    (no API key, no Ollama URL) — the caller should fall back to retrieved
    data only, same as the missing-embedder-model case never arises."""
    if settings.llm_backend == "ollama":
        if not settings.ollama_base_url:
            return None
        return OllamaClient(settings.ollama_base_url, settings.ollama_model)
    if settings.llm_backend == "anthropic":
        if not settings.anthropic_api_key:
            return None
        return AnthropicClient(settings.anthropic_api_key, settings.anthropic_model,
                               settings.max_tokens)
    raise ValueError(f"unknown llm_backend: {settings.llm_backend!r}")
