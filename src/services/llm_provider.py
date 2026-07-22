"""LLM provider abstraction layer.

Defines the ``LLMProvider`` ABC and concrete implementations
(OpenAI, Anthropic, etc.). Uses factory pattern for provider selection.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardised LLM response."""

    text: str
    model_used: str
    tokens_prompt: int
    tokens_completion: int
    latency_ms: int


class LLMProvider(ABC):
    """Abstract base for LLM integrations."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a prompt to the LLM and return the response."""
        ...


class OpenAIProvider(LLMProvider):
    """OpenAI / OpenAI-compatible LLM provider."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client = None

    def _get_client(self):
        """Lazy-initialize the OpenAI async client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required for OpenAIProvider. "
                    "Install with: pip install openai"
                ) from exc
            kwargs: dict = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Call the OpenAI API and return a standardised response."""
        client = self._get_client()
        chosen_model = model or "gpt-4o"

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.monotonic()
        response = await client.chat.completions.create(
            model=chosen_model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        if not response.choices:
            raise ValueError("LLM returned empty response (no choices)")
        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            text=choice.message.content or "",
            model_used=response.model or chosen_model,
            tokens_prompt=usage.prompt_tokens if usage else 0,
            tokens_completion=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )


def get_provider(provider_name: str = "openai") -> LLMProvider:
    """Factory: return the appropriate LLMProvider implementation."""
    from src.config import get_settings

    settings = get_settings()

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    raise ValueError(f"Unknown LLM provider: {provider_name}")
