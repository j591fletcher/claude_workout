"""Unit tests for the swappable LLM client: backend selection and the
Ollama-unreachable -> LLMUnavailable translation. No live network/model calls."""

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from app.llm import AnthropicClient, LLMUnavailable, OllamaClient, get_llm_client


def _settings(**over):
    base = dict(llm_backend="ollama", ollama_base_url="", ollama_model="qwen2.5:14b",
                anthropic_api_key="", anthropic_model="claude-opus-4-8", max_tokens=4096)
    base.update(over)
    return SimpleNamespace(**base)


class TestGetLlmClient:
    def test_ollama_selected_by_default(self):
        client = get_llm_client(_settings(ollama_base_url="http://100.85.238.56:11434"))
        assert isinstance(client, OllamaClient)

    def test_ollama_with_no_url_returns_none(self):
        assert get_llm_client(_settings(ollama_base_url="")) is None

    def test_anthropic_selected_with_key(self):
        client = get_llm_client(_settings(llm_backend="anthropic", anthropic_api_key="sk-x"))
        assert isinstance(client, AnthropicClient)

    def test_anthropic_with_no_key_returns_none(self):
        assert get_llm_client(_settings(llm_backend="anthropic", anthropic_api_key="")) is None

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError):
            get_llm_client(_settings(llm_backend="bogus"))


class TestOllamaClient:
    def test_unreachable_host_raises_llm_unavailable(self):
        client = OllamaClient("http://127.0.0.1:1", "qwen2.5:14b", timeout=1.0)
        with pytest.raises(LLMUnavailable):
            client.complete("system prompt", "hello")

    def test_successful_response_returns_message_content(self):
        client = OllamaClient("http://fake-host:11434", "qwen2.5:14b")

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"message": {"role": "assistant", "content": "coached answer"}}

        with patch("app.llm.httpx.post", return_value=FakeResponse()) as mock_post:
            answer = client.complete("system prompt", "hello")
        assert answer == "coached answer"
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["messages"] == [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hello"},
        ]
        assert kwargs["json"]["stream"] is False

    def test_http_error_status_raises_llm_unavailable(self):
        client = OllamaClient("http://fake-host:11434", "qwen2.5:14b")

        class FakeResponse:
            def raise_for_status(self):
                raise httpx.HTTPStatusError("500", request=None, response=None)

        with patch("app.llm.httpx.post", return_value=FakeResponse()):
            with pytest.raises(LLMUnavailable):
                client.complete("system", "hello")
