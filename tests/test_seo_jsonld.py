"""Interface and behavioral tests for JSONLDGenerator (AC-JSONLD).

Interface tests  — verify import, class structure, method signatures.
Behavioral tests — verify JSON-LD schema generation for Article, BlogPosting, WebPage.
"""
from __future__ import annotations

import inspect

from src.services.jsonld_generator import JSONLDGenerator

import pytest



# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================



# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

class TestJSONLDGeneratorInterface:
    """Verify the JSONLDGenerator interface."""

    def test_importable(self):
        assert JSONLDGenerator is not None

    def test_is_class(self):
        assert inspect.isclass(JSONLDGenerator)

    def test_init_exists(self):
        assert hasattr(JSONLDGenerator, "__init__")

    def test_generate_article_schema_method_exists(self):
        assert hasattr(JSONLDGenerator, "generate_article_schema")
        assert callable(JSONLDGenerator.generate_article_schema)

    def test_generate_blog_posting_schema_method_exists(self):
        assert hasattr(JSONLDGenerator, "generate_blog_posting_schema")
        assert callable(JSONLDGenerator.generate_blog_posting_schema)

    def test_generate_webpage_schema_method_exists(self):
        assert hasattr(JSONLDGenerator, "generate_webpage_schema")
        assert callable(JSONLDGenerator.generate_webpage_schema)

    def test_generate_article_schema_signature(self):
        sig = inspect.signature(JSONLDGenerator.generate_article_schema)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "article_data" in params

    def test_generate_webpage_schema_signature(self):
        sig = inspect.signature(JSONLDGenerator.generate_webpage_schema)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "page_data" in params


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS
# ============================================================================


class TestJSONLDGeneratorBehavioral:
    """Verify JSON-LD schema generation behavior."""

    def setup_method(self):
        self.gen = JSONLDGenerator()

    def test_article_has_context(self):
        result = self.gen.generate_article_schema({})
        assert result["@context"] == "https://schema.org"

    def test_article_has_type(self):
        result = self.gen.generate_article_schema({})
        assert result["@type"] == "Article"

    def test_article_headline_from_data(self):
        result = self.gen.generate_article_schema({"headline": "My Headline"})
        assert result["headline"] == "My Headline"

    def test_article_author(self):
        result = self.gen.generate_article_schema({"author": "Jane Doe"})
        assert result["author"] == "Jane Doe"

    def test_article_date_published(self):
        result = self.gen.generate_article_schema({"date_published": "2025-01-01"})
        assert result["datePublished"] == "2025-01-01"

    def test_article_all_fields_populated(self):
        data = {
            "headline": "Test Article",
            "author": "Author",
            "date_published": "2025-01-01",
            "date_modified": "2025-02-01",
            "description": "A test article",
            "image": "https://example.com/img.jpg",
            "publisher": "Publisher Inc",
        }
        result = self.gen.generate_article_schema(data)
        assert result["headline"] == "Test Article"
        assert result["author"] == "Author"
        assert result["datePublished"] == "2025-01-01"
        assert result["dateModified"] == "2025-02-01"
        assert result["description"] == "A test article"
        assert result["image"] == "https://example.com/img.jpg"
        assert result["publisher"] == "Publisher Inc"

    def test_blog_posting_type(self):
        result = self.gen.generate_blog_posting_schema({})
        assert result["@type"] == "BlogPosting"

    def test_blog_has_word_count(self):
        result = self.gen.generate_blog_posting_schema({"word_count": 1500})
        assert result["wordCount"] == 1500

    def test_blog_has_keywords(self):
        result = self.gen.generate_blog_posting_schema({"keywords": "python, testing"})
        assert result["keywords"] == "python, testing"

    def test_blog_all_fields_populated(self):
        data = {
            "headline": "Blog Post",
            "author": "Writer",
            "date_published": "2025-03-01",
            "word_count": 800,
            "keywords": "seo, blog",
        }
        result = self.gen.generate_blog_posting_schema(data)
        assert result["@type"] == "BlogPosting"
        assert result["wordCount"] == 800
        assert result["keywords"] == "seo, blog"
        assert result["headline"] == "Blog Post"

    def test_webpage_type(self):
        result = self.gen.generate_webpage_schema({})
        assert result["@type"] == "WebPage"

    def test_webpage_name(self):
        result = self.gen.generate_webpage_schema({"name": "Home Page"})
        assert result["name"] == "Home Page"

    def test_webpage_url(self):
        result = self.gen.generate_webpage_schema({"url": "https://example.com"})
        assert result["url"] == "https://example.com"

    def test_webpage_all_fields_populated(self):
        data = {
            "name": "About Us",
            "description": "Our story",
            "url": "https://example.com/about",
            "date_published": "2024-01-01",
            "date_modified": "2025-06-01",
        }
        result = self.gen.generate_webpage_schema(data)
        assert result["name"] == "About Us"
        assert result["description"] == "Our story"
        assert result["url"] == "https://example.com/about"

    def test_empty_data_returns_schema_with_empty_strings(self):
        result = self.gen.generate_article_schema({})
        assert result["headline"] == ""
        assert result["author"] == ""
        assert result["datePublished"] == ""
