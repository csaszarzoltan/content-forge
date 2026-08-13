"""Per-platform content adaptation for the content-creation pipeline.

P0-3 implementation per analysis-brief.md (t_ef548473): given a source asset
(text or Generation id) and a target platform, produce a platform-optimized
variant via the existing LLMProvider. The adapter is a thin transform — it
inherits the brand voice profile from the source and adjusts tone, length,
CTA, and hashtag strategy per platform; it never re-generates from scratch.

Design:
  * ``PLATFORM_PROMPTS`` — per-platform system prompt templates.
  * ``PLATFORM_CONSTRAINTS_MAP`` — platform id → constraint hints fed to the
    LLM (char limit, tone guidance) so the model can hit the limits.
  * ``PlatformAdapter.adapt()`` — main entry; idempotent per
    (source_text, platform) within a single adapter instance (cached).
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import BaseModel, Field

# ── Per-platform prompt templates (P0-3) ────────────────────────────────────

PLATFORM_PROMPTS: dict[str, str] = {
    "linkedin": (
        "You are adapting a source asset into a LinkedIn post. Keep it professional, "
        "insight-led, and under 3000 characters. Open with a hook, use short paragraphs, "
        "include 2-4 relevant hashtags, and end with a soft CTA."
    ),
    "twitter": (
        "You are adapting a source asset into an X/Twitter post. Be concise and "
        "conversational; keep it under 280 characters including hashtags. One clear "
        "idea, punchy wording, 1-2 hashtags max."
    ),
    "email": (
        "You are adapting a source asset into a marketing email. Produce a subject "
        "line plus a short body (under 2000 characters) with a clear CTA. "
        "Format as 'Subject: <line>\\n\\n<body>'."
    ),
    "blog": (
        "You are adapting a source asset into a long-form blog post. Preserve depth "
        "and narrative; use headings and paragraphs. Target 800-1500 words; "
        "end with a CTA."
    ),
}

PLATFORM_CONSTRAINTS_MAP: dict[str, dict[str, Any]] = {
    "linkedin": {"max_chars": 3000, "tone": "professional", "hashtags": "2-4"},
    "twitter": {"max_chars": 280, "tone": "casual", "hashtags": "1-2"},
    "email": {"max_chars": 2000, "tone": "direct", "hashtags": "0"},
    "blog": {"max_chars": 12000, "tone": "authoritative", "hashtags": "0"},
}


class PlatformVariant(BaseModel):
    """A single platform-optimized variant of a source asset."""

    platform: str
    content: str
    char_count: int = 0
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    adapted_from: str = ""
    model_used: str = ""
    tokens_used: int = 0
    latency_ms: int = 0


class _LLMProtocol(ABC):
    """Minimal structural contract for the LLM provider (duck-typed)."""

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any):
        ...


class PlatformAdapter:
    """Adapt a source asset into platform-specific variants via the LLM.

    Constructor takes the LLM provider and an optional constraint registry.
    ``adapt()`` is idempotent per (source_text, platform): the second call for
    the same source+platform returns the cached variant without re-generating.
    """

    def __init__(self, llm_provider: Any, registry: Any | None = None) -> None:
        self._llm = llm_provider
        self._registry = registry
        self._cache: dict[tuple[str, str], PlatformVariant] = {}

    async def adapt(
        self,
        source_text: str,
        platform: str,
        brand_voice: dict | None = None,
    ) -> PlatformVariant:
        """Adapt ``source_text`` for ``platform`` and return a PlatformVariant.

        Idempotency: if this adapter already produced a variant for the same
        (source_text, platform), the cached result is returned untouched.
        """
        cache_key = (source_text, platform)
        if cache_key in self._cache:
            return self._cache[cache_key]

        system_prompt = PLATFORM_PROMPTS.get(platform)
        if system_prompt is None:
            raise ValueError(f"unsupported_platform:{platform}")

        hints = PLATFORM_CONSTRAINTS_MAP.get(platform, {})
        voice_block = ""
        if brand_voice:
            voice_block = f"\nBrand voice profile: {brand_voice}"

        user_prompt = (
            f"Adapt the following source asset for {platform}.\n"
            f"Constraint hints: {hints}\n"
            f"Source asset:\n{source_text}{voice_block}"
        )

        response = await self._llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.6,
        )

        variant = PlatformVariant(
            platform=platform,
            content=response.text.strip(),
            char_count=len(response.text.strip()),
            adapted_from=source_text,
            model_used=getattr(response, "model_used", ""),
            tokens_used=getattr(response, "tokens_prompt", 0) + getattr(response, "tokens_completion", 0),
            latency_ms=getattr(response, "latency_ms", 0),
        )
        self._cache[cache_key] = variant
        return variant
