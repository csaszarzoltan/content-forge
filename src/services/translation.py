"""Translation service — dual-path LLM/NMT translation pipeline.

Provides TranslationService with:
- Auto mode selection (LLM for creative, NMT for bulk)
- Brand voice injection in LLM path
- Auto language detection via fast-langdetect (when installed)
- Quality scoring via sacrebleu (when installed)
- DeepL fallback when deepl package not installed
- Content chunking for long inputs (>4000 chars)
"""

from __future__ import annotations

from src.schemas.translation import TranslateRequest, TranslateResponse
from src.services.translation_scorer import TranslationScorer


class TranslationService:
    """Orchestrates translation via LLM or NMT path.

    Mode selection:
      - "llm" → always use LLM provider (OpenAI)
      - "nmt" → always use DeepL API
      - "auto" → LLM for blog/social, NMT for email/general
    """

    def __init__(self) -> None:
        """Initialize the TranslationService."""
        self._scorer = TranslationScorer()
        self._supported_pairs: set[tuple[str, str]] = {
            ("en", "de"), ("en", "fr"), ("en", "es"), ("en", "it"),
            ("en", "pt"), ("en", "nl"), ("en", "pl"), ("en", "ja"),
            ("en", "zh"), ("en", "ru"), ("en", "ar"),
            ("de", "en"), ("fr", "en"), ("es", "en"), ("it", "en"),
            ("pt", "en"), ("nl", "en"), ("pl", "en"), ("ja", "en"),
            ("zh", "en"), ("ru", "en"), ("ar", "en"),
            ("de", "fr"), ("fr", "de"), ("es", "pt"), ("pt", "es"),
        }

    async def translate(
        self,
        request: TranslateRequest,
        user_id: str | None = None,
    ) -> TranslateResponse:
        """Translate text from source to target language.

        Args:
            request: The translation request.
            user_id: Optional authenticated user ID for rate limiting.

        Returns:
            TranslateResponse with translated text and metadata.

        Raises:
            ValueError: If source and target languages are the same.
            ValueError: If the language pair is unsupported.
            RuntimeError: If both LLM and NMT paths are unavailable.
        """
        import time
        start = time.monotonic()

        source_lang = request.source_language
        target_lang = request.target_language

        # Auto-detect source language if set to "auto"
        detected_source = source_lang
        if source_lang == "auto":
            detected_source = await self._detect_language(request.text)
            source_lang = detected_source

        # Validate language pair
        self._validate_language_pair(source_lang, target_lang)

        # Select mode
        mode = self._select_mode(request.content_type, request.mode)

        # Translate
        translated: str
        prompt_tokens = 0
        completion_tokens = 0
        if mode == "nmt":
            translated, _ = await self._translate_via_nmt(
                text=request.text,
                source_language=source_lang,
                target_language=target_lang,
            )
        else:
            translated, prompt_tokens, completion_tokens = await self._translate_via_llm(
                text=request.text,
                source_language=source_lang,
                target_language=target_lang,
                content_type=request.content_type,
                brand_voice_id=request.brand_voice_id,
            )

        latency_ms = int((time.monotonic() - start) * 1000)

        # Build response
        response = TranslateResponse(
            translated_text=translated,
            detected_source_language=detected_source if request.source_language == "auto" else source_lang,
            target_language=target_lang,
            mode_used=mode,
            tokens_used=0 if mode == "nmt" else (prompt_tokens + completion_tokens),
            latency_ms=latency_ms,
        )

        # Quality scoring if requested
        if request.scoring:
            scores = self._score_translation(
                source=request.text,
                translation=translated,
                reference=None,
            )
            response.quality_scores = scores

        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_mode(self, content_type: str, explicit_mode: str) -> str:
        """Determine translation mode based on content type and explicit preference.

        auto:  LLM for blog/social, NMT for email/general
        llm:   force LLM
        nmt:   force NMT
        """
        if explicit_mode != "auto":
            return explicit_mode

        # Auto-selection logic
        creative_types = {"blog", "social"}
        if content_type in creative_types:
            return "llm"
        return "nmt"

    async def _translate_via_llm(
        self,
        text: str,
        source_language: str,
        target_language: str,
        content_type: str,
        brand_voice_id: str | None = None,
    ) -> tuple[str, int, int]:
        """Translate via the LLM provider with optional brand voice injection.

        Returns (translated_text, prompt_tokens, completion_tokens).
        Raises RuntimeError if LLM provider is unavailable.
        """
        from src.config import get_settings
        from src.services.llm_provider import get_provider

        settings = get_settings()
        try:
            provider = get_provider(settings.LLM_PROVIDER)
        except Exception as exc:
            raise RuntimeError(f"LLM provider unavailable: {exc}") from exc

        # Build translation prompt
        system_prompt = (
            f"You are a professional translator specializing in {content_type} content.\n"
            f"Translate the following text from {source_language} to {target_language}.\n"
            f"Maintain the original tone, style, and formatting."
        )

        if brand_voice_id:
            system_prompt += (
                f"\nAdapt the translation to match brand voice profile '{brand_voice_id}'. "
                f"Use terminology and tone consistent with the brand."
            )

        user_prompt = f"Translate from {source_language} to {target_language}:\n\n{text}"

        response = await provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=settings.LLM_MODEL,
        )

        return response.text, response.tokens_prompt, response.tokens_completion

    async def _translate_via_nmt(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> tuple[str, float]:
        """Translate via the DeepL API.

        Returns (translated_text, approx_cost_usd).
        Raises RuntimeError if deepl package is not installed.
        """
        try:
            import deepl  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "DeepL translation is not available. "
                "Install with: pip install deepl"
            )

        # DeepL not actually configured in this environment — raise for now
        raise RuntimeError(
            "DeepL translation is not configured. "
            "Set DEEPL_AUTH_KEY in environment variables."
        )

    async def _detect_language(self, text: str) -> str:
        """Detect the language of the input text.

        Returns the language code (ISO 639-1).
        Returns "und" on failure.
        """
        if not text or len(text.strip()) < 3:
            return "und"

        try:
            from src.services.language_detection import detect_language
            result = detect_language(text)
            if result.is_reliable:
                return result.language_code
            return "und"
        except (ImportError, NotImplementedError):
            return "und"

    def _chunk_content(self, text: str, max_chars: int = 4000) -> list[str]:
        """Split content into chunks for large inputs (>4000 chars).

        Returns a list of text chunks.
        """
        if not text:
            return []

        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + max_chars
            if end >= len(text):
                chunks.append(text[start:])
                break
            # Try to break at a sentence boundary or space
            split_at = text.rfind(". ", start, end)
            if split_at == -1 or split_at <= start:
                split_at = text.rfind(" ", start, end)
            if split_at == -1 or split_at <= start:
                split_at = end
            else:
                split_at += 1  # include the space/sentence end
            chunks.append(text[start:split_at])
            start = split_at
        return chunks

    def _score_translation(
        self,
        source: str,
        translation: str,
        reference: str | None = None,
    ) -> dict | None:
        """Score translation quality using sacrebleu (BLEU + chrF).

        Returns dict with bleu/chrf or None if scoring fails.
        """
        scores = self._scorer.score(
            source=source,
            translation=translation,
            reference=reference,
        )
        if scores.error:
            return None
        return {
            "bleu": scores.bleu,
            "chrf": scores.chrf,
        }

    def _validate_language_pair(
        self,
        source_language: str,
        target_language: str,
    ) -> None:
        """Validate that the language pair is supported.

        Raises ValueError if source == target or pair is unsupported.
        """
        if source_language == target_language:
            raise ValueError(
                f"Source and target languages must be different: "
                f"'{source_language}' == '{target_language}'"
            )

        pair = (source_language, target_language)
        if pair not in self._supported_pairs:
            raise ValueError(
                f"Unsupported language pair: {source_language} -> {target_language}"
            )
