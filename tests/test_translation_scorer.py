"""Interface and behavioral tests for translation quality scoring pipeline (T6).

Interface tests  — verify imports, class signatures (should PASS once stubs exist).
Behavioral tests — verify NotImplementedError for unimplemented stubs.

Covers:
  - TranslationScores schema
  - TranslationScorer class
  - BLEU and chrF scoring
  - Batch scoring
  - Edge case handling (empty, too short, identical)
"""

from __future__ import annotations

import inspect

import pytest

# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.services.translation_scorer import (
    TranslationPair,
    TranslationScorer,
    TranslationScores,
)

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestTranslationScoresInterface:
    """Verify the TranslationScores schema interface."""

    def test_translation_scores_importable(self):
        assert TranslationScores is not None

    def test_translation_scores_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(TranslationScores, BaseModel)

    def test_translation_scores_fields(self):
        sig = inspect.signature(TranslationScores)
        assert "bleu" in sig.parameters
        assert "chrf" in sig.parameters
        assert "source_length" in sig.parameters
        assert "translation_length" in sig.parameters
        assert "reference_provided" in sig.parameters

    def test_translation_scores_error_field(self):
        """TranslationScores should have optional error field."""
        sig = inspect.signature(TranslationScores)
        assert "error" in sig.parameters

    def test_translation_scores_bleu_type(self):
        ann = inspect.signature(TranslationScores).parameters["bleu"].annotation
        ann_str = str(ann)
        assert "float" in ann_str

    def test_translation_scores_chrf_type(self):
        ann = inspect.signature(TranslationScores).parameters["chrf"].annotation
        ann_str = str(ann)
        assert "float" in ann_str

    def test_translation_scores_source_length_type(self):
        ann = inspect.signature(TranslationScores).parameters["source_length"].annotation
        ann_str = str(ann)
        assert "int" in ann_str

    def test_translation_scores_reference_provided_type(self):
        ann = inspect.signature(TranslationScores).parameters["reference_provided"].annotation
        ann_str = str(ann)
        assert "bool" in ann_str


class TestTranslationPairInterface:
    """Verify the TranslationPair schema interface."""

    def test_translation_pair_importable(self):
        assert TranslationPair is not None

    def test_translation_pair_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(TranslationPair, BaseModel)

    def test_translation_pair_fields(self):
        sig = inspect.signature(TranslationPair)
        assert "source" in sig.parameters
        assert "translation" in sig.parameters

    def test_translation_pair_reference_field(self):
        """reference should be optional."""
        sig = inspect.signature(TranslationPair)
        assert "reference" in sig.parameters
        param = sig.parameters["reference"]
        assert param.default is None or param.default is not inspect.Parameter.empty


class TestTranslationScorerInterface:
    """Verify the TranslationScorer class interface."""

    def test_translation_scorer_importable(self):
        assert TranslationScorer is not None

    def test_translation_scorer_is_class(self):
        assert inspect.isclass(TranslationScorer)

    def test_translation_scorer_init_signature(self):
        sig = inspect.signature(TranslationScorer.__init__)
        params = list(sig.parameters.keys())
        assert "self" in params

    def test_translation_scorer_has_score(self):
        assert hasattr(TranslationScorer, "score")
        assert callable(TranslationScorer.score)

    def test_translation_scorer_score_signature(self):
        sig = inspect.signature(TranslationScorer.score)
        assert "source" in sig.parameters or "source" in str(sig)
        assert "translation" in sig.parameters or "translation" in str(sig)

    def test_translation_scorer_score_return_type(self):
        ann = inspect.signature(TranslationScorer.score).return_annotation
        ann_str = str(ann)
        assert "TranslationScores" in ann_str

    def test_translation_scorer_score_is_async_or_sync(self):
        """score() should be callable (sync is fine for sacrebleu)."""
        assert callable(TranslationScorer.score)

    def test_translation_scorer_has_score_batch(self):
        assert hasattr(TranslationScorer, "score_batch")
        assert callable(TranslationScorer.score_batch)

    def test_translation_scorer_score_batch_signature(self):
        sig = inspect.signature(TranslationScorer.score_batch)
        assert "pairs" in sig.parameters or "translations" in str(sig)

    def test_translation_scorer_score_batch_return_type(self):
        ann = inspect.signature(TranslationScorer.score_batch).return_annotation
        ann_str = str(ann)
        assert "list" in ann_str.lower() or "List" in ann_str


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestTranslationScoresBehavioral:
    """Behavioral tests for TranslationScores model."""

    def test_translation_scores_creates_with_reference(self):
        """TranslationScores should construct with reference scores."""
        scores = TranslationScores(
            bleu=45.5,
            chrf=62.3,
            source_length=50,
            translation_length=55,
            reference_provided=True,
        )
        assert scores.bleu == 45.5
        assert scores.chrf == 62.3
        assert scores.reference_provided is True

    def test_translation_scores_creates_without_reference(self):
        """TranslationScores when no reference provided."""
        scores = TranslationScores(
            bleu=0.0,
            chrf=0.0,
            source_length=50,
            translation_length=55,
            reference_provided=False,
        )
        assert scores.reference_provided is False

    def test_translation_scores_error_case(self):
        """TranslationScores should support error field."""
        scores = TranslationScores(
            bleu=0.0,
            chrf=0.0,
            source_length=0,
            translation_length=0,
            reference_provided=False,
            error="Input too short",
        )
        assert scores.error == "Input too short"

    def test_translation_scores_bleu_range(self):
        """BLEU should be 0.0-100.0."""
        scores = TranslationScores(
            bleu=100.0,
            chrf=100.0,
            source_length=10,
            translation_length=10,
            reference_provided=True,
        )
        assert 0.0 <= scores.bleu <= 100.0
        assert 0.0 <= scores.chrf <= 100.0


class TestTranslationPairBehavioral:
    """Behavioral tests for TranslationPair."""

    def test_translation_pair_with_reference(self):
        """TranslationPair should construct with reference."""
        pair = TranslationPair(
            source="Hello world",
            translation="Hallo Welt",
            reference="Hallo Welt",
        )
        assert pair.source == "Hello world"
        assert pair.reference == "Hallo Welt"

    def test_translation_pair_without_reference(self):
        """TranslationPair should work without reference."""
        pair = TranslationPair(
            source="Hello world",
            translation="Hallo Welt",
        )
        assert pair.reference is None


class TestTranslationScorerBehavioral:
    """Behavioral tests for TranslationScorer."""

    def test_scorer_init(self):
        """TranslationScorer() should construct successfully."""
        scorer = TranslationScorer()
        assert scorer is not None

    def test_scorer_score_returns_scores(self):
        """score() should return a TranslationScores instance."""
        scorer = TranslationScorer()
        result = scorer.score(
            source="Hello world",
            translation="Hallo Welt",
            reference="Hallo Welt",
        )
        assert isinstance(result, TranslationScores)

    def test_scorer_score_without_reference(self):
        """score() without reference should return scores with reference_provided=False."""
        scorer = TranslationScorer()
        result = scorer.score(
            source="Hello world",
            translation="Hallo Welt",
        )
        assert result.reference_provided is False
        # BLEU/chrF should be 0 when no reference
        assert result.bleu == 0.0
        assert result.chrf == 0.0

    def test_scorer_score_identical_strings(self):
        """Identical translation and reference should give perfect score."""
        scorer = TranslationScorer()
        result = scorer.score(
            source="Hello world",
            translation="Hello world",
            reference="Hello world",
        )
        assert result.bleu >= 99.0 or result.bleu == 100.0
        assert result.chrf >= 99.0 or result.chrf == 100.0

    def test_scorer_score_completely_different(self):
        """Completely different translation and reference should give low score."""
        scorer = TranslationScorer()
        result = scorer.score(
            source="Hello world",
            translation="The quick brown fox jumps over the lazy dog",
            reference="Hallo Welt",
        )
        assert result.bleu < 50.0

    def test_scorer_batch_scoring(self):
        """score_batch() should process multiple pairs."""
        scorer = TranslationScorer()
        pairs = [
            TranslationPair(source="Hello", translation="Hallo", reference="Hallo"),
            TranslationPair(source="Goodbye", translation="Tschüss", reference="Tschüss"),
        ]
        results = scorer.score_batch(pairs)
        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, TranslationScores)

    def test_scorer_minimum_length_guard(self):
        """Very short inputs should be handled gracefully (error or 0 scores)."""
        scorer = TranslationScorer()
        result = scorer.score(
            source="Hi",
            translation="Hallo",
        )
        assert result.error is not None or (result.bleu == 0.0 and result.chrf == 0.0)
