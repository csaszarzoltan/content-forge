"""SERP preview generator service.

Generates Google-style search result snippets and breadcrumbs.
"""
from __future__ import annotations

from html import escape


class SERPPreviewGenerator:
    """Generate SERP preview HTML."""

    def __init__(self) -> None:
        pass

    def generate_serp_preview(
        self,
        title: str,
        url: str,
        description: str,
        date: str = "",
    ) -> str:
        """Generate a Google-style SERP snippet as HTML."""
        safe_title = escape(title)
        safe_url = escape(url)
        safe_desc = escape(description)
        date_part = f' <span class="serp-date">{escape(date)}</span>' if date else ""
        return (
            f'<div class="serp-preview">'
            f'<h3 class="serp-title"><a href="{safe_url}">{safe_title}</a></h3>'
            f'<div class="serp-url">{safe_url}</div>'
            f'<div class="serp-description">{safe_desc}{date_part}</div>'
            f"</div>"
        )

    def generate_breadcrumb(self, url: str) -> str:
        """Generate breadcrumb navigation HTML from a URL."""
        if not url:
            return ""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if not parts:
            return escape(parsed.netloc)
        crumbs = [escape(parsed.netloc)]
        for part in parts:
            crumbs.append(escape(part))
        return " &gt; ".join(crumbs)
