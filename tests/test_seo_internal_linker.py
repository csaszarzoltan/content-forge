"""Interface and behavioral tests for InternalLinker (AC-LINKER).

Interface tests  — verify import, class structure, method signatures, LinkSuggestion schema.
Behavioral tests — verify TF-IDF scoring and internal link suggestion behavior.
"""
from __future__ import annotations

import inspect

from src.schemas.seo import LinkSuggestion
from src.services.internal_linker import InternalLinker

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestInternalLinkerInterface:
    """Verify the InternalLinker interface."""

    def test_importable(self):
        assert InternalLinker is not None

    def test_is_class(self):
        assert inspect.isclass(InternalLinker)

    def test_init_exists(self):
        assert hasattr(InternalLinker, "__init__")

    def test_tfidf_score_method_exists(self):
        assert hasattr(InternalLinker, "tfidf_score")
        assert callable(InternalLinker.tfidf_score)

    def test_suggest_links_method_exists(self):
        assert hasattr(InternalLinker, "suggest_links")
        assert callable(InternalLinker.suggest_links)

    def test_tfidf_score_signature(self):
        sig = inspect.signature(InternalLinker.tfidf_score)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "term" in params
        assert "documents" in params

    def test_suggest_links_signature(self):
        sig = inspect.signature(InternalLinker.suggest_links)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "content" in params
        assert "existing_pages" in params

    def test_link_suggestion_importable(self):
        assert LinkSuggestion is not None

    def test_link_suggestion_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(LinkSuggestion, BaseModel)

    def test_link_suggestion_fields(self):
        schema = LinkSuggestion.model_fields
        assert "anchor_text" in schema
        assert "target_url" in schema
        assert "relevance_score" in schema


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS
# ============================================================================


class TestInternalLinkerTFIDF:
    """Verify TF-IDF scoring behavior."""

    def setup_method(self):
        self.linker = InternalLinker()

    def test_tfidf_zero_for_empty_term(self):
        result = self.linker.tfidf_score("", ["some document"])
        assert result == 0.0

    def test_tfidf_zero_for_empty_docs(self):
        result = self.linker.tfidf_score("python", [])
        assert result == 0.0

    def test_tfidf_basic_term_document_score_positive(self):
        result = self.linker.tfidf_score("python", ["python is a great language", "other text here"])
        assert result > 0.0

    def test_tfidf_term_in_all_docs_has_lower_idf(self):
        # Term in 1 of 1 docs -> idf = log(1/1) = 0, score = 0
        # Term in 1 of 2 docs -> idf = log(2/1) > 0
        score_in_one = self.linker.tfidf_score("python", ["python is great"])
        score_in_two = self.linker.tfidf_score("python", ["python is great", "other text here"])
        # score_in_one has idf = log(1/1) = 0, so score = 0
        # score_in_two has idf = log(2/1) > 0, so score > 0
        assert score_in_one == 0.0
        assert score_in_two > 0.0

    def test_tfidf_term_not_in_any_doc_returns_zero(self):
        result = self.linker.tfidf_score("rustlang", ["python is great", "java is nice"])
        assert result == 0.0


class TestInternalLinkerSuggestLinks:
    """Verify link suggestion behavior."""

    def setup_method(self):
        self.linker = InternalLinker()

    def test_suggest_empty_content_returns_empty(self):
        result = self.linker.suggest_links("", [{"title": "Python Guide", "url": "/python"}])
        assert result == []

    def test_suggest_empty_pages_returns_empty(self):
        result = self.linker.suggest_links("Learn about python programming", [])
        assert result == []

    def test_suggest_matching_content_returns_non_empty(self):
        pages = [{"title": "Python Guide", "url": "/python"}]
        result = self.linker.suggest_links("Learn about python programming", pages)
        assert len(result) > 0

    def test_suggestions_sorted_by_relevance_descending(self):
        pages = [
            {"title": "Python Guide", "url": "/python"},
            {"title": "Java Tutorial", "url": "/java"},
            {"title": "Python Advanced", "url": "/python-advanced"},
        ]
        result = self.linker.suggest_links("Learn about python programming advanced", pages)
        if len(result) > 1:
            scores = [s.relevance_score for s in result]
            assert scores == sorted(scores, reverse=True)

    def test_max_10_suggestions_returned(self):
        pages = [{"title": f"Page about keyword-{i}", "url": f"/page-{i}"} for i in range(20)]
        # All pages share the word "keyword" which has 7 chars, so all match
        result = self.linker.suggest_links("keyword content with keyword", pages)
        assert len(result) <= 10

    def test_each_suggestion_has_required_fields(self):
        pages = [{"title": "Python Guide", "url": "/python"}]
        result = self.linker.suggest_links("Learn about python programming", pages)
        for suggestion in result:
            assert hasattr(suggestion, "anchor_text")
            assert hasattr(suggestion, "target_url")
            assert hasattr(suggestion, "relevance_score")
            assert isinstance(suggestion.anchor_text, str)
            assert isinstance(suggestion.target_url, str)
            assert isinstance(suggestion.relevance_score, float)
