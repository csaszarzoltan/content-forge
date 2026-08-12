"""Tests for SEO content analyzer service."""
from __future__ import annotations

import inspect

import pytest

# Mark as quick (unit tests)
pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from src.schemas.seo import ContentScore
from src.services.seo_analyzer import SEOAnalyzer

# ============================================================================
# SECTION 1 — INTERFACE TESTS
# ============================================================================


class TestSEOAnalyzerInterface:
    """Verify SEOAnalyzer meets its public API contract."""

    def test_importable(self) -> None:
        assert SEOAnalyzer is not None

    def test_is_class(self) -> None:
        assert inspect.isclass(SEOAnalyzer)

    def test_has_init(self) -> None:
        assert hasattr(SEOAnalyzer, "__init__")

    def test_has_keyword_density(self) -> None:
        assert hasattr(SEOAnalyzer, "keyword_density")
        assert callable(SEOAnalyzer.keyword_density)

    def test_has_word_count(self) -> None:
        assert hasattr(SEOAnalyzer, "word_count")
        assert callable(SEOAnalyzer.word_count)

    def test_has_sentence_count(self) -> None:
        assert hasattr(SEOAnalyzer, "sentence_count")
        assert callable(SEOAnalyzer.sentence_count)

    def test_has_paragraph_count(self) -> None:
        assert hasattr(SEOAnalyzer, "paragraph_count")
        assert callable(SEOAnalyzer.paragraph_count)

    def test_has_content_score(self) -> None:
        assert hasattr(SEOAnalyzer, "content_score")
        assert callable(SEOAnalyzer.content_score)

    def test_keyword_density_is_sync(self) -> None:
        assert not inspect.iscoroutinefunction(SEOAnalyzer.keyword_density)

    def test_word_count_is_sync(self) -> None:
        assert not inspect.iscoroutinefunction(SEOAnalyzer.word_count)

    def test_sentence_count_is_sync(self) -> None:
        assert not inspect.iscoroutinefunction(SEOAnalyzer.sentence_count)

    def test_content_score_is_sync(self) -> None:
        assert not inspect.iscoroutinefunction(SEOAnalyzer.content_score)

    def test_keyword_density_signature(self) -> None:
        sig = inspect.signature(SEOAnalyzer.keyword_density)
        params = list(sig.parameters.keys())
        assert params == ["self", "text", "keyword"]
        assert sig.return_annotation == "float"

    def test_word_count_signature(self) -> None:
        sig = inspect.signature(SEOAnalyzer.word_count)
        params = list(sig.parameters.keys())
        assert params == ["self", "text"]
        assert sig.return_annotation == "int"

    def test_content_score_signature(self) -> None:
        sig = inspect.signature(SEOAnalyzer.content_score)
        params = list(sig.parameters.keys())
        assert params == ["self", "text", "target_keyword"]
        assert sig.return_annotation == "ContentScore"

    def test_content_score_target_keyword_default(self) -> None:
        sig = inspect.signature(SEOAnalyzer.content_score)
        assert sig.parameters["target_keyword"].default == ""


# ContentScore interface tests


class TestContentScoreInterface:
    """Verify ContentScore schema meets its contract."""

    def test_importable(self) -> None:
        assert ContentScore is not None

    def test_is_pydantic_model(self) -> None:
        assert issubclass(ContentScore, __import__("pydantic", fromlist=["BaseModel"]).BaseModel)

    def test_has_keyword_density_field(self) -> None:
        assert "keyword_density" in ContentScore.model_fields

    def test_has_word_count_field(self) -> None:
        assert "word_count" in ContentScore.model_fields

    def test_has_sentence_count_field(self) -> None:
        assert "sentence_count" in ContentScore.model_fields

    def test_has_paragraph_count_field(self) -> None:
        assert "paragraph_count" in ContentScore.model_fields

    def test_has_content_quality_field(self) -> None:
        assert "content_quality" in ContentScore.model_fields


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS
# ============================================================================


class TestSEOAnalyzerBehavioral:
    """Exercise SEOAnalyzer business logic."""

    @pytest.fixture()
    def analyzer(self) -> SEOAnalyzer:
        return SEOAnalyzer()

    # -- keyword_density --------------------------------------------------

    def test_keyword_density_basic(self, analyzer: SEOAnalyzer) -> None:
        # 100 words, "python" appears 3 times → 3.0 %
        words = ["word"] * 97 + ["python"] * 3
        text = " ".join(words)
        assert analyzer.keyword_density(text, "python") == pytest.approx(3.0)

    def test_keyword_density_empty_text(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.keyword_density("", "python") == 0.0

    def test_keyword_density_empty_keyword(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.keyword_density("some text here", "") == 0.0

    def test_keyword_density_case_insensitive(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.keyword_density("Python is great", "python") == pytest.approx(100.0 / 3)

    def test_keyword_density_partial_word_not_matched(self, analyzer: SEOAnalyzer) -> None:
        # "pythons" should NOT match "python"
        text = "I love pythons in the wild"
        assert analyzer.keyword_density(text, "python") == 0.0

    def test_keyword_density_high_density(self, analyzer: SEOAnalyzer) -> None:
        text = "python " * 50  # 50 words, all "python"
        assert analyzer.keyword_density(text, "python") == pytest.approx(100.0)

    def test_keyword_density_single_word(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.keyword_density("python", "python") == pytest.approx(100.0)

    def test_keyword_density_special_chars(self, analyzer: SEOAnalyzer) -> None:
        # punctuation is stripped by \b\w+\b
        text = "python! python? python."
        assert analyzer.keyword_density(text, "python") == pytest.approx(100.0)

    def test_keyword_density_unicode(self, analyzer: SEOAnalyzer) -> None:
        text = "über cool über smart über"
        assert analyzer.keyword_density(text, "über") == pytest.approx(60.0)

    # -- word_count -------------------------------------------------------

    def test_word_count_basic(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.word_count("one two three") == 3

    def test_word_count_empty(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.word_count("") == 0

    def test_word_count_numbers(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.word_count("42 is the answer") == 4

    def test_word_count_punctuation(self, analyzer: SEOAnalyzer) -> None:
        # punctuation is stripped; only \w+ tokens counted
        assert analyzer.word_count("hello, world! how are you?") == 5

    def test_word_count_unicode(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.word_count("über cool café résumé") == 4

    def test_word_count_long_text(self, analyzer: SEOAnalyzer) -> None:
        text = " ".join(["word"] * 5000)
        assert analyzer.word_count(text) == 5000

    # -- sentence_count ---------------------------------------------------

    def test_sentence_count_basic(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.sentence_count("Hello world.") == 1

    def test_sentence_count_empty(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.sentence_count("") == 0

    def test_sentence_count_multiple(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.sentence_count("First. Second. Third.") == 3

    def test_sentence_count_exclamations(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.sentence_count("Wow! Amazing! Yes!") == 3

    def test_sentence_count_questions(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.sentence_count("Who? What? Where?") == 3

    def test_sentence_count_mixed_punctuation(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.sentence_count("Hello. Wow! Really? Yes.") == 4

    # -- paragraph_count --------------------------------------------------

    def test_paragraph_count_basic(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.paragraph_count("Para one.\n\nPara two.") == 2

    def test_paragraph_count_empty(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.paragraph_count("") == 0

    def test_paragraph_count_single(self, analyzer: SEOAnalyzer) -> None:
        assert analyzer.paragraph_count("Just one paragraph here.") == 1

    def test_paragraph_count_multiple(self, analyzer: SEOAnalyzer) -> None:
        text = "First.\n\nSecond.\n\nThird.\n\nFourth."
        assert analyzer.paragraph_count(text) == 4

    # -- content_score ----------------------------------------------------

    def test_content_score_returns_model(self, analyzer: SEOAnalyzer) -> None:
        result = analyzer.content_score("Some text here.")
        assert isinstance(result, ContentScore)

    def test_content_score_empty_text(self, analyzer: SEOAnalyzer) -> None:
        result = analyzer.content_score("")
        assert result.content_quality == "empty"

    def test_content_score_thin(self, analyzer: SEOAnalyzer) -> None:
        text = " ".join(["word"] * 150)
        result = analyzer.content_score(text)
        assert result.content_quality == "thin"

    def test_content_score_adequate(self, analyzer: SEOAnalyzer) -> None:
        text = " ".join(["word"] * 500)
        result = analyzer.content_score(text)
        assert result.content_quality == "adequate"

    def test_content_score_comprehensive(self, analyzer: SEOAnalyzer) -> None:
        text = " ".join(["word"] * 1200)
        result = analyzer.content_score(text)
        assert result.content_quality == "comprehensive"

    def test_content_score_keyword_density_included(self, analyzer: SEOAnalyzer) -> None:
        words = ["python"] * 10 + ["other"] * 90
        text = " ".join(words)
        result = analyzer.content_score(text, target_keyword="python")
        assert result.keyword_density == pytest.approx(10.0)
        assert result.word_count == 100

    def test_content_score_no_keyword_defaults_zero(self, analyzer: SEOAnalyzer) -> None:
        result = analyzer.content_score("Some text here.", target_keyword="")
        assert result.keyword_density == 0.0

