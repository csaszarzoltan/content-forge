"""Readability scoring service.

Wraps textstat to compute Flesch-Kincaid, Coleman-Liau,
and Flesch Reading Ease scores.
"""
from __future__ import annotations

import textstat

from src.schemas.seo import ReadabilityMetrics


class ReadabilityScorer:
    """Score text readability using standard formulas."""

    def __init__(self) -> None:
        pass

    def flesch_kincaid(self, text: str) -> float:
        """Compute Flesch-Kincaid grade level."""
        if not text:
            return 0.0
        return textstat.flesch_kincaid_grade(text)

    def coleman_liau(self, text: str) -> float:
        """Compute Coleman-Liau index."""
        if not text:
            return 0.0
        return textstat.coleman_liau_index(text)

    def flesch_reading_ease(self, text: str) -> float:
        """Compute Flesch Reading Ease score."""
        if not text:
            return 0.0
        return textstat.flesch_reading_ease(text)

    def readability_metrics(self, text: str) -> ReadabilityMetrics:
        """Compute all readability metrics."""
        if not text:
            return ReadabilityMetrics()
        fre = self.flesch_reading_ease(text)
        if fre >= 80:
            level = "easy"
        elif fre >= 60:
            level = "standard"
        elif fre >= 40:
            level = "difficult"
        else:
            level = "very_difficult"
        return ReadabilityMetrics(
            flesch_kincaid=self.flesch_kincaid(text),
            coleman_liau=self.coleman_liau(text),
            flesch_reading_ease=fre,
            reading_level=level,
        )
