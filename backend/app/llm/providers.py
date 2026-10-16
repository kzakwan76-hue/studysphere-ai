"""AI providers. Each one turns (system prompt, user prompt) into reply text, or raises ProviderError."""

from typing import Any

import httpx

from app.config import Settings
from app.llm.base import LLMProvider, ProviderError


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout: float, client: Any = None) -> None:
        if client is None:
            try:
                import anthropic  # optional: only needed when this provider is used
            except ImportError as error:
                raise ProviderError("The 'anthropic' package is not installed. Run: pip install anthropic") from error
            client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self._client = client
        self._model = model

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as error:  # network, authentication, rate limit, ...: all handled the same way
            raise ProviderError(f"Anthropic request failed: {type(error).__name__}") from error
        text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text").strip()
        if not text:
            raise ProviderError("The model returned an empty reply.")
        return text


class OllamaProvider:
    """A free model running on your own computer (https://ollama.com)."""

    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)
        self._model = model

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
        }
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            text = response.json()["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise ProviderError(f"Ollama request failed: {type(error).__name__}") from error
        if not text:
            raise ProviderError("The model returned an empty reply.")
        return text


def build_provider(settings: Settings) -> LLMProvider | None:
    """The configured provider, or None when LLM_PROVIDER=none."""
    if settings.llm_provider == "none":
        return None
    if settings.llm_provider == "anthropic":
        key = settings.anthropic_api_key.get_secret_value()
        if not key:
            raise ProviderError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.")
        return AnthropicProvider(key, settings.anthropic_model, settings.llm_timeout_seconds)
    return OllamaProvider(settings.ollama_base_url, settings.ollama_model, settings.llm_timeout_seconds)