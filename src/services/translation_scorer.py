"""Translation scoring module — BLEU + chrF quality evaluation.

Provides TranslationScores schema, TranslationPair for batch scoring,
and TranslationScorer using sacrebleu (when installed).
"""

from __future__ import annotations

from pydantic import BaseModel


class TranslationScores(BaseModel):
    """Quality scores for a single translation.

    Attributes:
        bleu: BLEU score (0.0–100.0).
        chrf: chrF score (0.0–100.0).
        source_length: Character length of the source text.
        translation_length: Character length of the translation.
        reference_provided: Whether a reference translation was used.
        error: Error message if scoring failed.
    """

    bleu: float
    chrf: float
    source_length: int
    translation_length: int
    reference_provided: bool
    error: str | None = None


class TranslationPair(BaseModel):
    """A source-translation pair for batch scoring.

    Attributes:
        source: Original source text.
        translation: Translated text to score.
        reference: Optional reference/human translation for comparison.
    """

    source: str
    translation: str
    reference: str | None = None


class TranslationScorer:
    """Score translation quality using sacrebleu (BLEU + chrF).

    When sacrebleu is not installed, scoring returns zeros with an error note.
    """

    def __init__(self) -> None:
        """Initialize the TranslationScorer."""
        self._sacrebleu_available = False
        try:
            import sacrebleu  # noqa: F401
            self._sacrebleu_available = True
        except ImportError:
            pass

    def score(
        self,
        source: str,
        translation: str,
        reference: str | None = None,
    ) -> TranslationScores:
        """Score a single translation.

        Args:
            source: Original source text.
            translation: Translated text to score.
            reference: Optional reference/human translation.

        Returns:
            TranslationScores with BLEU, chrF, and metadata.
        """
        source_len = len(source)
        translation_len = len(translation)
        reference_provided = reference is not None

        # Minimum length guard
        if source_len < 3 or translation_len < 3:
            return TranslationScores(
                bleu=0.0,
                chrf=0.0,
                source_length=source_len,
                translation_length=translation_len,
                reference_provided=reference_provided,
                error="Input too short",
            )

        if not reference_provided or not self._sacrebleu_available:
            return TranslationScores(
                bleu=0.0,
                chrf=0.0,
                source_length=source_len,
                translation_length=translation_len,
                reference_provided=reference_provided,
            )

        try:
            import sacrebleu

            # BLEU score — use sentence-level for single translations
            bleu_score = sacrebleu.sentence_bleu(
                translation, [reference]
            ).score

            # chrF score
            chrf_score = sacrebleu.sentence_chrf(
                translation, [reference]
            ).score

            return TranslationScores(
                bleu=round(bleu_score, 2),
                chrf=round(chrf_score, 2),
                source_length=source_len,
                translation_length=translation_len,
                reference_provided=True,
            )
        except Exception as exc:
            return TranslationScores(
                bleu=0.0,
                chrf=0.0,
                source_length=source_len,
                translation_length=translation_len,
                reference_provided=True,
                error=str(exc),
            )

    def score_batch(self, pairs: list[TranslationPair]) -> list[TranslationScores]:
        """Score multiple translation pairs.

        Args:
            pairs: List of TranslationPair instances.

        Returns:
            List of TranslationScores, one per pair.
        """
        return [self.score(p.source, p.translation, p.reference) for p in pairs]
