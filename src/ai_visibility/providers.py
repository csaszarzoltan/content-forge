"""AI engine provider abstraction (analysis brief §5 M4).

One ABC over all four engines (mirrors ``connectors/base.py`` + the
``llm_provider.py`` factory style). Each provider returns a normalized
``EngineVisibilityResult`` for one (query, target_url) check. Providers
degrade gracefully:

- unconfigured credentials → ``validate_credentials()`` returns ``False`` and
  ``check_visibility`` returns a graceful *not mentioned* result (never
  crashes the poller);
- HTTP/parse failures on a configured provider raise ``ProviderError`` —
  credentials are never leaked and non-``ProviderError`` exceptions never
  escape.

Two construction paths exist on :class:`ProviderRegistry`:

- ``ProviderRegistry(settings)`` — registers all four engines (canonical
  order), each degrading gracefully when its key is absent;
- ``ProviderRegistry.from_settings(settings, llm_provider=None)`` — registers
  only engines whose API key is present (connectors precedent); ``llm_provider``
  lets tests inject a fake LLM for the prompt-based engines.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from src.ai_visibility.models import AI_ENGINES
from src.config import Settings

# Re-exported for convenience (brief §5 M4 notes the registry consumes settings).
__all__ = [
    "AIEngineProvider",
    "ChatGPTProvider",
    "EngineVisibilityResult",
    "GeminiProvider",
    "GoogleAIOverviewsProvider",
    "PerplexityProvider",
    "ProviderError",
    "ProviderRegistry",
]


class ProviderError(RuntimeError):
    """Raised by providers on HTTP/parse failures (never leak credentials)."""


class EngineVisibilityResult(BaseModel):
    """Normalized outcome of one (query, target_url) visibility check."""

    engine: str
    query: str
    mentioned: bool
    cited: bool
    cited_url: str | None = None
    snippet: str = ""
    sentiment: Literal["positive", "neutral", "negative", "unknown"] = "unknown"
    raw_payload: dict = Field(default_factory=dict)


class AIEngineProvider(ABC):
    """Abstract contract every AI engine provider must implement."""

    @property
    @abstractmethod
    def engine(self) -> str:
        """Return the engine identifier (one of AI_ENGINES)."""

    @abstractmethod
    async def check_visibility(
        self, query: str, target_url: str
    ) -> EngineVisibilityResult:
        """Check whether ``target_url`` is cited/mentioned in an answer to
        ``query``, with sentiment. Raises ProviderError on failure."""

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Return True when the provider is configured and usable."""


class _HTTPProviderMixin:
    """Shared helpers for HTTP-backed providers (Perplexity, Gemini)."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _graceful(self, query: str) -> EngineVisibilityResult:
        """Graceful 'could not check' result for an unconfigured provider."""
        return EngineVisibilityResult(
            engine=self.engine,
            query=query,
            mentioned=False,
            cited=False,
            cited_url=None,
            snippet="",
            sentiment="unknown",
            raw_payload={"configured": False},
        )


class ChatGPTProvider(AIEngineProvider):
    """LLM-prompt-based provider for ChatGPT (engine == ``chatgpt``).

    There is no stable public ChatGPT search/citation API, so this engine is
    driven by a structured LLM prompt (brief Cluster B3): given query Q and
    target URL U, ask whether U is cited, the brand mentioned without a link,
    or absent — plus sentiment. The prompt template is deterministic and the
    answer is parsed with stdlib ``json``.
    """

    PROMPT_TEMPLATE = (
        "You are a search-answer auditor. Query: {query}\n"
        "Target URL: {target_url}\n"
        "In one JSON object with keys \"mentioned\" (bool), \"cited\" (bool), "
        "\"sentiment\" (one of positive|neutral|negative|unknown), respond "
        "whether the target URL is cited in a ChatGPT answer to the query, "
        "whether the brand is mentioned without a link, and the sentiment. "
        "No other text."
    )

    def __init__(self, api_key: str = "", llm_provider: Any | None = None) -> None:
        self._api_key = api_key
        self._llm_provider = llm_provider

    @property
    def engine(self) -> str:
        return "chatgpt"

    async def check_visibility(
        self, query: str, target_url: str
    ) -> EngineVisibilityResult:
        if not self._api_key or self._llm_provider is None:
            return EngineVisibilityResult(
                engine=self.engine,
                query=query,
                mentioned=False,
                cited=False,
                cited_url=None,
                snippet="",
                sentiment="unknown",
                raw_payload={"configured": False},
            )
        try:
            prompt = self.PROMPT_TEMPLATE.format(query=query, target_url=target_url)
            response = await self._llm_provider.generate(prompt)
            payload = json.loads(response.text.strip())
            mentioned = bool(payload.get("mentioned", False))
            cited = bool(payload.get("cited", False))
            sentiment = payload.get("sentiment", "unknown")
            if sentiment not in ("positive", "neutral", "negative", "unknown"):
                sentiment = "unknown"
            return EngineVisibilityResult(
                engine=self.engine,
                query=query,
                mentioned=mentioned,
                cited=cited,
                cited_url=target_url if cited else None,
                snippet=response.text[:2000],
                sentiment=sentiment,
                raw_payload={"model": response.model_used},
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize to ProviderError
            raise ProviderError(f"ChatGPT visibility check failed: {exc}") from exc

    async def validate_credentials(self) -> bool:
        return bool(self._api_key) and self._llm_provider is not None


class PerplexityProvider(AIEngineProvider, _HTTPProviderMixin):
    """Real HTTP API provider for Perplexity (engine == ``perplexity``).

    Uses the Perplexity chat completions API; citation-bearing answers are
    mapped to ``mentioned``/``cited`` by looking for the target URL in the
    answer text and the ``citations`` array.
    """

    ENDPOINT = "https://api.perplexity.ai/chat/completions"
    MODEL = "sonar"

    def __init__(self, api_key: str = "") -> None:
        _HTTPProviderMixin.__init__(self, api_key)

    @property
    def engine(self) -> str:
        return "perplexity"

    async def check_visibility(
        self, query: str, target_url: str
    ) -> EngineVisibilityResult:
        if not self._api_key:
            return self._graceful(query)
        try:
            body = {
                "model": self.MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Answer: {query}. Does the answer mention or cite "
                            f"{target_url}? Reply with the answer only."
                        ),
                    }
                ],
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.ENDPOINT, headers=self._headers(), json=body
                )
                resp.raise_for_status()
                data = resp.json()
            text = data["choices"][0]["message"]["content"] or ""
            citations = data.get("citations", [])
            cited_urls = [c for c in citations if isinstance(c, str)]
            cited = target_url in text or target_url in cited_urls
            return EngineVisibilityResult(
                engine=self.engine,
                query=query,
                mentioned=bool(text.strip()),
                cited=cited,
                cited_url=target_url if cited else None,
                snippet=text[:2000],
                sentiment="unknown",
                raw_payload={"citations": cited_urls[:20]},
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize to ProviderError
            raise ProviderError(f"Perplexity visibility check failed: {exc}") from exc

    async def validate_credentials(self) -> bool:
        return bool(self._api_key)


class GeminiProvider(AIEngineProvider, _HTTPProviderMixin):
    """Real HTTP API provider for Gemini (engine == ``gemini``).

    Uses the Gemini ``generateContent`` API; grounded responses carry citation
    URLs that map directly to ``cited``.
    """

    ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent"
    )
    MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str = "") -> None:
        _HTTPProviderMixin.__init__(self, api_key)

    @property
    def engine(self) -> str:
        return "gemini"

    async def check_visibility(
        self, query: str, target_url: str
    ) -> EngineVisibilityResult:
        if not self._api_key:
            return self._graceful(query)
        try:
            body = {
                "contents": [{"parts": [{"text": query}]}],
                "groundingConfig": {"sources": [{"type": "WEB"}]},
            }
            params = {"key": self._api_key}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.ENDPOINT, params=params, json=body
                )
                resp.raise_for_status()
                data = resp.json()
            candidate = data["candidates"][0]
            text = "".join(
                p.get("text", "") for p in candidate["content"]["parts"]
            )
            grounding = candidate.get("groundingMetadata", {})
            cited_urls = [
                chunk.get("uri", "")
                for chunk in grounding.get("groundingChunks", [])
                if chunk.get("uri")
            ]
            cited = target_url in text or target_url in cited_urls
            return EngineVisibilityResult(
                engine=self.engine,
                query=query,
                mentioned=bool(text.strip()),
                cited=cited,
                cited_url=target_url if cited else None,
                snippet=text[:2000],
                sentiment="unknown",
                raw_payload={"cited_urls": cited_urls[:20]},
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize to ProviderError
            raise ProviderError(f"Gemini visibility check failed: {exc}") from exc

    async def validate_credentials(self) -> bool:
        return bool(self._api_key)


class GoogleAIOverviewsProvider(AIEngineProvider):
    """LLM-prompt-based provider for Google AI Overviews
    (engine == ``google_ai_overviews``).

    Google AI Overviews has no stable public API, so — like ChatGPT — this
    engine uses a deterministic structured LLM prompt (brief Cluster B3).
    """

    PROMPT_TEMPLATE = (
        "You are a search-answer auditor. Query: {query}\n"
        "Target URL: {target_url}\n"
        "In one JSON object with keys \"mentioned\" (bool), \"cited\" (bool), "
        "\"sentiment\" (one of positive|neutral|negative|unknown), respond "
        "whether a Google AI Overview for the query cites the target URL, "
        "mentions the brand without a link, or neither. No other text."
    )

    def __init__(self, api_key: str = "", llm_provider: Any | None = None) -> None:
        self._api_key = api_key
        self._llm_provider = llm_provider

    @property
    def engine(self) -> str:
        return "google_ai_overviews"

    async def check_visibility(
        self, query: str, target_url: str
    ) -> EngineVisibilityResult:
        if not self._api_key or self._llm_provider is None:
            return EngineVisibilityResult(
                engine=self.engine,
                query=query,
                mentioned=False,
                cited=False,
                cited_url=None,
                snippet="",
                sentiment="unknown",
                raw_payload={"configured": False},
            )
        try:
            prompt = self.PROMPT_TEMPLATE.format(query=query, target_url=target_url)
            response = await self._llm_provider.generate(prompt)
            payload = json.loads(response.text.strip())
            mentioned = bool(payload.get("mentioned", False))
            cited = bool(payload.get("cited", False))
            sentiment = payload.get("sentiment", "unknown")
            if sentiment not in ("positive", "neutral", "negative", "unknown"):
                sentiment = "unknown"
            return EngineVisibilityResult(
                engine=self.engine,
                query=query,
                mentioned=mentioned,
                cited=cited,
                cited_url=target_url if cited else None,
                snippet=response.text[:2000],
                sentiment=sentiment,
                raw_payload={"model": response.model_used},
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize to ProviderError
            raise ProviderError(
                f"Google AI Overviews visibility check failed: {exc}"
            ) from exc

    async def validate_credentials(self) -> bool:
        return bool(self._api_key) and self._llm_provider is not None


class ProviderRegistry:
    """Registry of AI engine providers.

    ``ProviderRegistry(settings)`` registers all four engines (canonical
    order); ``from_settings`` registers only engines whose API key is present
    (connectors precedent). ``available_engines`` always lists all four in
    canonical order.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._providers: dict[str, AIEngineProvider] = {}
        # Direct construction: register all four engines so the poller can
        # always attempt every engine; each provider degrades gracefully when
        # its key is absent.
        self.register(ChatGPTProvider(api_key=settings.CHATGPT_SEARCH_API_KEY))
        self.register(PerplexityProvider(api_key=settings.PERPLEXITY_API_KEY))
        self.register(GeminiProvider(api_key=settings.GEMINI_API_KEY))
        self.register(
            GoogleAIOverviewsProvider(api_key=settings.GOOGLE_AI_SEARCH_API_KEY)
        )

    def register(self, provider: AIEngineProvider) -> None:
        """Register a provider instance (raises for unknown engine)."""
        if provider.engine not in AI_ENGINES:
            raise ValueError(f"Unknown AI engine: {provider.engine!r}")
        self._providers[provider.engine] = provider

    def get(self, engine: str) -> AIEngineProvider:
        """Return the registered provider; KeyError if unregistered."""
        return self._providers[engine]

    def available_engines(self) -> list[str]:
        """All four engines in canonical order (regardless of registration)."""
        return list(AI_ENGINES)

    def configured_engines(self) -> list[str]:
        """Only the engines with a registered provider (canonical order)."""
        return [engine for engine in AI_ENGINES if engine in self._providers]

    @classmethod
    def from_settings(
        cls, settings: Settings, llm_provider: Any | None = None
    ) -> "ProviderRegistry":
        """Build a registry from settings; register only configured engines.

        ``llm_provider`` is forwarded to the prompt-based engines (ChatGPT,
        Google AI Overviews) so tests can inject a fake LLM.
        """
        registry = cls.__new__(cls)
        registry._settings = settings
        registry._providers = {}
        if settings.PERPLEXITY_API_KEY:
            registry.register(PerplexityProvider(api_key=settings.PERPLEXITY_API_KEY))
        if settings.GEMINI_API_KEY:
            registry.register(GeminiProvider(api_key=settings.GEMINI_API_KEY))
        if settings.CHATGPT_SEARCH_API_KEY:
            registry.register(
                ChatGPTProvider(
                    api_key=settings.CHATGPT_SEARCH_API_KEY, llm_provider=llm_provider
                )
            )
        if settings.GOOGLE_AI_SEARCH_API_KEY:
            registry.register(
                GoogleAIOverviewsProvider(
                    api_key=settings.GOOGLE_AI_SEARCH_API_KEY,
                    llm_provider=llm_provider,
                )
            )
        return registry
