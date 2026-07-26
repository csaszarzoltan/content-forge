"""Meta tag generator service.

Generates title tags, meta descriptions, OG tags, and canonical URLs.
"""
from __future__ import annotations

from urllib.parse import urlparse


class MetaTagGenerator:
    """Generate HTML meta tags for SEO."""

    def __init__(self) -> None:
        pass

    def generate_title(self, title: str, max_len: int = 60) -> str:
        """Generate title tag, truncated with '...' if too long."""
        if not title:
            return ""
        if len(title) <= max_len:
            return title
        return title[: max_len - 3] + "..."

    def generate_description(self, description: str, max_len: int = 160) -> str:
        """Generate meta description, truncated with '...' if too long."""
        if not description:
            return ""
        if len(description) <= max_len:
            return description
        return description[: max_len - 3] + "..."

    def generate_og_tags(
        self, title: str, description: str, url: str, image: str = ""
    ) -> dict:
        """Generate Open Graph meta tags as a dict."""
        tags = {
            "og:title": title,
            "og:description": description,
            "og:url": url,
            "og:type": "website",
        }
        if image:
            tags["og:image"] = image
        return tags

    def generate_canonical_url(self, url: str) -> str:
        """Normalize URL to canonical form."""
        if not url:
            return ""
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc.lower().rstrip("/")
        path = parsed.path.rstrip("/") or "/"
        return f"{scheme}://{netloc}{path}"
