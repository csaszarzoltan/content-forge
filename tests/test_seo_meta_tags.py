"""Tests for SEO meta tag generator service."""
from __future__ import annotations

import inspect

import pytest

# Mark as quick (unit tests)
pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from src.services.meta_generator import MetaTagGenerator

# ── SECTION 1: Interface Tests ──────────────────────────────────────────────


class TestMetaTagGeneratorInterface:
    """Verify the MetaTagGenerator class interface contract."""

    def test_importable(self) -> None:
        assert MetaTagGenerator is not None

    def test_is_class(self) -> None:
        assert inspect.isclass(MetaTagGenerator)

    def test_init_exists(self) -> None:
        assert hasattr(MetaTagGenerator, "__init__")

    def test_init_signature(self) -> None:
        sig = inspect.signature(MetaTagGenerator.__init__)
        params = list(sig.parameters.keys())
        assert params == ["self"]

    def test_generate_title_exists(self) -> None:
        assert hasattr(MetaTagGenerator, "generate_title")

    def test_generate_description_exists(self) -> None:
        assert hasattr(MetaTagGenerator, "generate_description")

    def test_generate_og_tags_exists(self) -> None:
        assert hasattr(MetaTagGenerator, "generate_og_tags")

    def test_generate_canonical_url_exists(self) -> None:
        assert hasattr(MetaTagGenerator, "generate_canonical_url")

    def test_generate_title_signature(self) -> None:
        sig = inspect.signature(MetaTagGenerator.generate_title)
        params = list(sig.parameters.keys())
        assert params == ["self", "title", "max_len"]

    def test_generate_description_signature(self) -> None:
        sig = inspect.signature(MetaTagGenerator.generate_description)
        params = list(sig.parameters.keys())
        assert params == ["self", "description", "max_len"]

    def test_generate_og_tags_signature(self) -> None:
        sig = inspect.signature(MetaTagGenerator.generate_og_tags)
        params = list(sig.parameters.keys())
        assert params == ["self", "title", "description", "url", "image"]


# ── SECTION 2: Behavioral Tests ─────────────────────────────────────────────


class TestGenerateTitle:
    """Behavioral tests for generate_title."""

    def setup_method(self) -> None:
        self.gen = MetaTagGenerator()

    def test_short_title_not_truncated(self) -> None:
        result = self.gen.generate_title("Hello World")
        assert result == "Hello World"

    def test_long_title_truncated_with_ellipsis(self) -> None:
        long = "A" * 100
        result = self.gen.generate_title(long)
        assert result.endswith("...")
        assert len(result) == 60

    def test_empty_title_returns_empty(self) -> None:
        assert self.gen.generate_title("") == ""

    def test_custom_max_len(self) -> None:
        long = "B" * 50
        result = self.gen.generate_title(long, max_len=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_title_exactly_at_max_len(self) -> None:
        title = "C" * 60
        result = self.gen.generate_title(title)
        assert result == title

    def test_title_one_over_max_len(self) -> None:
        title = "D" * 61
        result = self.gen.generate_title(title)
        assert len(result) == 60
        assert result.endswith("...")


class TestGenerateDescription:
    """Behavioral tests for generate_description."""

    def setup_method(self) -> None:
        self.gen = MetaTagGenerator()

    def test_short_description_not_truncated(self) -> None:
        desc = "Short description."
        assert self.gen.generate_description(desc) == desc

    def test_long_description_truncated(self) -> None:
        long = "X" * 200
        result = self.gen.generate_description(long)
        assert len(result) == 160
        assert result.endswith("...")

    def test_empty_description_returns_empty(self) -> None:
        assert self.gen.generate_description("") == ""

    def test_custom_max_len(self) -> None:
        long = "Y" * 100
        result = self.gen.generate_description(long, max_len=40)
        assert len(result) == 40
        assert result.endswith("...")

    def test_description_exactly_at_max_len(self) -> None:
        desc = "Z" * 160
        assert self.gen.generate_description(desc) == desc


class TestGenerateOgTags:
    """Behavioral tests for generate_og_tags."""

    def setup_method(self) -> None:
        self.gen = MetaTagGenerator()

    def test_og_tags_includes_og_title(self) -> None:
        tags = self.gen.generate_og_tags("T", "D", "http://x.com")
        assert tags["og:title"] == "T"

    def test_og_tags_includes_og_description(self) -> None:
        tags = self.gen.generate_og_tags("T", "D", "http://x.com")
        assert tags["og:description"] == "D"

    def test_og_tags_includes_og_url(self) -> None:
        tags = self.gen.generate_og_tags("T", "D", "http://x.com")
        assert tags["og:url"] == "http://x.com"

    def test_og_tags_includes_og_type(self) -> None:
        tags = self.gen.generate_og_tags("T", "D", "http://x.com")
        assert tags["og:type"] == "website"

    def test_og_tags_includes_image_when_provided(self) -> None:
        tags = self.gen.generate_og_tags("T", "D", "http://x.com", image="http://x.com/img.png")
        assert tags["og:image"] == "http://x.com/img.png"

    def test_og_tags_no_image_key_when_empty(self) -> None:
        tags = self.gen.generate_og_tags("T", "D", "http://x.com", image="")
        assert "og:image" not in tags


class TestGenerateCanonicalUrl:
    """Behavioral tests for generate_canonical_url."""

    def setup_method(self) -> None:
        self.gen = MetaTagGenerator()

    def test_strips_trailing_slash(self) -> None:
        result = self.gen.generate_canonical_url("http://example.com/")
        # Root path retains trailing slash as canonical form
        assert result == "http://example.com/"

    def test_lowercases_domain(self) -> None:
        result = self.gen.generate_canonical_url("http://EXAMPLE.COM/page")
        assert "example.com" in result

    def test_default_https_scheme(self) -> None:
        result = self.gen.generate_canonical_url("example.com/page")
        assert result.startswith("https://")

    def test_empty_url_returns_empty(self) -> None:
        assert self.gen.generate_canonical_url("") == ""

    def test_preserves_path(self) -> None:
        result = self.gen.generate_canonical_url("http://example.com/blog/post")
        assert "/blog/post" in result

    def test_strips_path_trailing_slash(self) -> None:
        result = self.gen.generate_canonical_url("http://example.com/page/")
        assert not result.endswith("/page/")
        assert result.endswith("/page")

    def test_no_scheme_defaults_to_https(self) -> None:
        result = self.gen.generate_canonical_url("example.com")
        assert result.startswith("https://example.com")
