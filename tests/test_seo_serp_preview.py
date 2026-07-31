"""Interface and behavioral tests for SERPPreviewGenerator (AC-SERP).

Interface tests  — verify import, class structure, method signatures.
Behavioral tests — verify SERP preview and breadcrumb generation.
"""
from __future__ import annotations

import inspect

from src.services.serp_preview import SERPPreviewGenerator

import pytest



# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================



# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

class TestSERPPreviewGeneratorInterface:
    """Verify the SERPPreviewGenerator interface."""

    def test_importable(self):
        assert SERPPreviewGenerator is not None

    def test_is_class(self):
        assert inspect.isclass(SERPPreviewGenerator)

    def test_init_exists(self):
        assert hasattr(SERPPreviewGenerator, "__init__")

    def test_generate_serp_preview_method_exists(self):
        assert hasattr(SERPPreviewGenerator, "generate_serp_preview")
        assert callable(SERPPreviewGenerator.generate_serp_preview)

    def test_generate_breadcrumb_method_exists(self):
        assert hasattr(SERPPreviewGenerator, "generate_breadcrumb")
        assert callable(SERPPreviewGenerator.generate_breadcrumb)

    def test_generate_serp_preview_signature(self):
        sig = inspect.signature(SERPPreviewGenerator.generate_serp_preview)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "title" in params
        assert "url" in params
        assert "description" in params
        assert "date" in params

    def test_generate_breadcrumb_signature(self):
        sig = inspect.signature(SERPPreviewGenerator.generate_breadcrumb)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "url" in params

    def test_instantiation(self):
        gen = SERPPreviewGenerator()
        assert gen is not None


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS
# ============================================================================


class TestSERPPreviewGeneratorBehavioral:
    """Verify SERP preview and breadcrumb generation behavior."""

    def setup_method(self):
        self.gen = SERPPreviewGenerator()

    def test_generate_serp_preview_returns_string(self):
        result = self.gen.generate_serp_preview("Title", "https://example.com", "Desc")
        assert isinstance(result, str)

    def test_serp_preview_contains_title_text(self):
        result = self.gen.generate_serp_preview("My Blog Post", "https://example.com", "Desc")
        assert "My Blog Post" in result

    def test_serp_preview_contains_url(self):
        result = self.gen.generate_serp_preview("Title", "https://example.com/page", "Desc")
        assert "https://example.com/page" in result

    def test_serp_preview_contains_description(self):
        result = self.gen.generate_serp_preview("Title", "https://example.com", "This is a description")
        assert "This is a description" in result

    def test_serp_preview_date_included_when_provided(self):
        result = self.gen.generate_serp_preview("Title", "https://example.com", "Desc", date="2025-01-15")
        assert "2025-01-15" in result

    def test_serp_preview_date_omitted_when_empty_string(self):
        result = self.gen.generate_serp_preview("Title", "https://example.com", "Desc", date="")
        assert "serp-date" not in result

    def test_serp_preview_html_escapes_angle_brackets(self):
        result = self.gen.generate_serp_preview("<script>alert('x')</script>", "https://example.com", "Desc")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_serp_preview_has_div_wrapper(self):
        result = self.gen.generate_serp_preview("Title", "https://example.com", "Desc")
        assert result.startswith('<div class="serp-preview">')
        assert result.endswith("</div>")

    def test_breadcrumb_from_url_with_path_segments(self):
        result = self.gen.generate_breadcrumb("https://example.com/blog/post-one")
        assert "example.com" in result
        assert "blog" in result
        assert "post-one" in result

    def test_breadcrumb_from_root_url(self):
        result = self.gen.generate_breadcrumb("https://example.com/")
        assert "example.com" in result

    def test_breadcrumb_empty_url_returns_empty(self):
        result = self.gen.generate_breadcrumb("")
        assert result == ""

    def test_breadcrumb_handles_deeply_nested_paths(self):
        result = self.gen.generate_breadcrumb("https://example.com/a/b/c/d/e")
        assert "example.com" in result
        assert "a" in result
        assert "e" in result

    def test_breadcrumb_uses_separator(self):
        result = self.gen.generate_breadcrumb("https://example.com/blog/post")
        assert " &gt; " in result
