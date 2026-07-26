"""SEO content analyzer service.

Provides keyword density, word/sentence/paragraph counting,
and content quality scoring.
"""
from __future__ import annotations

import re

from src.schemas.seo import ContentScore


class SEOAnalyzer:
    """Analyze text for SEO metrics."""

    def __init__(self) -> None:
        pass

    def keyword_density(self, text: str, keyword: str) -> float:
        """Calculate keyword density as a percentage."""
        if not text or not keyword:
            return 0.0
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0
        keyword_lower = keyword.lower()
        count = sum(1 for w in words if w == keyword_lower)
        return (count / len(words)) * 100

    def word_count(self, text: str) -> int:
        """Count words in text."""
        if not text:
            return 0
        return len(re.findall(r'\b\w+\b', text))

    def sentence_count(self, text: str) -> int:
        """Count sentences in text."""
        if not text:
            return 0
        sentences = re.split(r'[.!?]+', text)
        return len([s for s in sentences if s.strip()])

    def paragraph_count(self, text: str) -> int:
        """Count paragraphs in text."""
        if not text:
            return 0
        paragraphs = text.split('\n\n')
        return len([p for p in paragraphs if p.strip()])

    def content_score(self, text: str, target_keyword: str = "") -> ContentScore:
        """Compute comprehensive content score."""
        wc = self.word_count(text)
        sc = self.sentence_count(text)
        pc = self.paragraph_count(text)
        kd = self.keyword_density(text, target_keyword) if target_keyword else 0.0

        if wc == 0:
            quality = "empty"
        elif wc < 300:
            quality = "thin"
        elif wc < 1000:
            quality = "adequate"
        else:
            quality = "comprehensive"

        return ContentScore(
            keyword_density=kd,
            word_count=wc,
            sentence_count=sc,
            paragraph_count=pc,
            content_quality=quality,
        )
