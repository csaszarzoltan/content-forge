"""JSON-LD structured data generator service.

Generates Article, BlogPosting, and WebPage schema.org markup.
"""
from __future__ import annotations


class JSONLDGenerator:
    """Generate JSON-LD structured data."""

    def __init__(self) -> None:
        pass

    def generate_article_schema(self, article_data: dict) -> dict:
        """Generate Article schema.org JSON-LD."""
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article_data.get("headline", ""),
            "author": article_data.get("author", ""),
            "datePublished": article_data.get("date_published", ""),
            "dateModified": article_data.get("date_modified", ""),
            "description": article_data.get("description", ""),
            "image": article_data.get("image", ""),
            "publisher": article_data.get("publisher", ""),
        }

    def generate_blog_posting_schema(self, blog_data: dict) -> dict:
        """Generate BlogPosting schema.org JSON-LD."""
        schema = self.generate_article_schema(blog_data)
        schema["@type"] = "BlogPosting"
        schema["wordCount"] = blog_data.get("word_count", 0)
        schema["keywords"] = blog_data.get("keywords", "")
        return schema

    def generate_webpage_schema(self, page_data: dict) -> dict:
        """Generate WebPage schema.org JSON-LD."""
        return {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": page_data.get("name", ""),
            "description": page_data.get("description", ""),
            "url": page_data.get("url", ""),
            "datePublished": page_data.get("date_published", ""),
            "dateModified": page_data.get("date_modified", ""),
        }
