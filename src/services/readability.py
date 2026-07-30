"""Deterministic, offline readability scoring.

The implementation uses the published Flesch-Kincaid, Coleman-Liau, and Flesch
Reading Ease formulas with a lightweight English syllable estimator. It avoids
runtime corpus downloads, making API and test behavior reproducible offline.
"""

from __future__ import annotations

import re

from src.schemas.seo import ReadabilityMetrics

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_SENTENCE_RE = re.compile(r"[.!?]+")
_VOWELS = "aeiouy"


def _syllables(word: str) -> int:
    clean = re.sub(r"[^a-z]", "", word.lower())
    if not clean:
        return 0
    groups = 0
    previous_vowel = False
    for char in clean:
        is_vowel = char in _VOWELS
        if is_vowel and not previous_vowel:
            groups += 1
        previous_vowel = is_vowel
    if clean.endswith("e") and not clean.endswith(("le", "ye")) and groups > 1:
        groups -= 1
    if clean.endswith("ed") and len(clean) > 3 and clean[-3] not in "td" and groups > 1:
        groups -= 1
    return max(1, groups)


def _counts(text: str) -> tuple[int, int, int, int]:
    words = _WORD_RE.findall(text)
    word_count = max(1, len(words))
    sentences = max(1, len(_SENTENCE_RE.findall(text)))
    syllables = sum(_syllables(word) for word in words)
    letters = sum(len(re.sub(r"[^A-Za-z]", "", word)) for word in words)
    return word_count, sentences, syllables, letters


class ReadabilityScorer:
    """Score English text without external data files or network access."""

    def __init__(self) -> None:
        """Create a stateless scorer."""

    def flesch_kincaid(self, text: str) -> float:
        if not text:
            return 0.0
        words, sentences, syllables, _ = _counts(text)
        return float(round(0.39 * words / sentences + 11.8 * syllables / words - 15.59, 2))

    def coleman_liau(self, text: str) -> float:
        if not text:
            return 0.0
        words, sentences, _, letters = _counts(text)
        per_hundred_letters = letters / words * 100
        per_hundred_sentences = sentences / words * 100
        return float(round(0.0588 * per_hundred_letters - 0.296 * per_hundred_sentences - 15.8, 2))

    def flesch_reading_ease(self, text: str) -> float:
        if not text:
            return 0.0
        words, sentences, syllables, _ = _counts(text)
        return float(round(206.835 - 1.015 * words / sentences - 84.6 * syllables / words, 2))

    def readability_metrics(self, text: str) -> ReadabilityMetrics:
        if not text:
            return ReadabilityMetrics()
        fre = self.flesch_reading_ease(text)
        level = (
            "easy"
            if fre >= 80
            else "standard"
            if fre >= 60
            else "difficult"
            if fre >= 40
            else "very_difficult"
        )
        return ReadabilityMetrics(
            flesch_kincaid=self.flesch_kincaid(text),
            coleman_liau=self.coleman_liau(text),
            flesch_reading_ease=fre,
            reading_level=level,
        )
