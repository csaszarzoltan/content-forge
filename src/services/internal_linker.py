"""Internal linking service.

Provides TF-IDF scoring and internal link suggestions.
"""
from __future__ import annotations

import math
import re

from src.schemas.seo import LinkSuggestion


class InternalLinker:
    """Suggest internal links using TF-IDF scoring."""

    def __init__(self) -> None:
        pass

    def tfidf_score(self, term: str, documents: list[str]) -> float:
        """Compute TF-IDF score for a term across documents."""
        if not term or not documents:
            return 0.0
        term_lower = term.lower()
        # Term frequency in first document
        words = re.findall(r'\b\w+\b', documents[0].lower())
        if not words:
            return 0.0
        tf = words.count(term_lower) / len(words)
        # Document frequency
        df = sum(1 for doc in documents if term_lower in doc.lower())
        if df == 0:
            return 0.0
        idf = math.log(len(documents) / df)
        return round(tf * idf, 4)

    def suggest_links(
        self, content: str, existing_pages: list[dict]
    ) -> list[LinkSuggestion]:
        """Suggest internal links based on content relevance."""
        if not content or not existing_pages:
            return []
        suggestions = []
        content_words = set(re.findall(r'\b\w{4,}\b', content.lower()))
        for page in existing_pages:
            title = page.get("title", "")
            url = page.get("url", "")
            page_words = set(re.findall(r'\b\w{4,}\b', title.lower()))
            overlap = content_words & page_words
            if overlap:
                score = len(overlap) / max(len(content_words), 1)
                suggestions.append(LinkSuggestion(
                    anchor_text=next(iter(overlap)) if overlap else title,
                    target_url=url,
                    relevance_score=round(score, 4),
                ))
        suggestions.sort(key=lambda s: s.relevance_score, reverse=True)
        return suggestions[:10]
