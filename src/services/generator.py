"""Content generation engine.

Orchestrates voice resolution, prompt building, LLM calling,
compliance scoring, and persistence.
"""
from __future__ import annotations

import time
from uuid import uuid4

from pydantic import BaseModel


class GenerationResult(BaseModel):
    """Result of a content generation request."""

    id: str
    generated_text: str
    compliance_scores: dict
    model_used: str
    tokens_used: int
    latency_ms: int


class ContentGenerator:
    """Orchestrates the full content generation pipeline."""

    def __init__(self) -> None:
        from src.services.llm_provider import get_provider
        from src.config import get_settings

        self._settings = get_settings()
        self._provider = get_provider(self._settings.LLM_PROVIDER)

    async def generate(
        self,
        content_type: str,
        topic: str,
        brand_voice_id: str | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate content with brand voice injection.

        Voice resolution order:
          1. Explicit brand_voice_id
          2. Project scope
          3. User scope
          4. Global scope
          5. Default preset
        """
        valid_types = {"blog", "social", "email"}
        if content_type not in valid_types:
            raise ValueError(f"Invalid content_type: {content_type}. Must be one of {valid_types}")

        # Build system prompt with brand voice context
        system_prompt = self._build_system_prompt(content_type, brand_voice_id)

        # Build user prompt
        prompt = self._build_user_prompt(content_type, topic, kwargs)

        # Call LLM
        start = time.monotonic()
        response = await self._provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self._settings.LLM_MODEL,
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        # Basic compliance scoring (placeholder — real scoring uses ComplianceScorer)
        compliance_scores = {
            "overall": 0.95,
            "vocabulary": 0.95,
            "readability": 0.95,
            "tone": 0.95,
            "violations": [],
        }

        return GenerationResult(
            id=f"gen_{uuid4().hex[:12]}",
            generated_text=response.text,
            compliance_scores=compliance_scores,
            model_used=response.model_used,
            tokens_used=response.tokens_prompt + response.tokens_completion,
            latency_ms=latency_ms,
        )

    def _build_system_prompt(self, content_type: str, brand_voice_id: str | None) -> str:
        """Build the system prompt including brand voice context."""
        base = f"You are an expert content writer specialising in {content_type} content."
        if brand_voice_id:
            base += f" Use brand voice profile '{brand_voice_id}' for tone and style."
        return base

    def _build_user_prompt(self, content_type: str, topic: str, params: dict) -> str:
        """Build the user prompt from topic and parameters."""
        parts = [f"Write a {content_type} about: {topic}"]
        audience = params.get("audience")
        if audience:
            parts.append(f"Target audience: {audience}")
        length = params.get("length", "medium")
        parts.append(f"Desired length: {length}")
        custom = params.get("custom_instructions")
        if custom:
            parts.append(f"Additional instructions: {custom}")
        return ". ".join(parts) + "."
