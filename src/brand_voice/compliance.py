"""Real-time voice compliance scoring.

Scores generated text against brand voice rules including vocabulary,
tone, readability, and banned term detection.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from brand_voice.models import VoiceProfile


class ComplianceResult(BaseModel):
    """Result of compliance scoring against brand voice rules."""

    overall_score: float = Field(ge=0.0, le=1.0, description="Weighted overall compliance score")
    vocabulary_score: float = Field(ge=0.0, le=1.0, description="Vocabulary adherence score")
    readability_score: float = Field(ge=0.0, le=1.0, description="Readability score")
    tone_score: float = Field(ge=0.0, le=1.0, description="Tone alignment score")
    banned_terms_found: list[str] = Field(
        default_factory=list, description="Banned terms detected in text"
    )
    violations: list[str] = Field(
        default_factory=list, description="Human-readable violation descriptions"
    )


def _count_syllables(word: str) -> int:
    """Estimate syllable count for a word."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _flesch_kincaid_score(text: str) -> float:
    """Compute a Flesch-Kincaid-like readability score normalized to 0-1."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = text.split()
    if not sentences or not words:
        return 1.0

    total_syllables = sum(_count_syllables(w) for w in words)
    num_words = len(words)
    num_sentences = len(sentences)

    # Flesch-Kincaid Grade Level
    fk_grade = (
        0.39 * (num_words / num_sentences)
        + 11.8 * (total_syllables / num_words)
        - 15.59
    )
    # Normalize: grade 0 -> 1.0, grade 14+ -> 0.0
    score = max(0.0, min(1.0, 1.0 - (fk_grade / 14.0)))
    return round(score, 4)


class ComplianceScorer:
    """Scores text against brand voice compliance rules."""

    def __init__(self, profile: VoiceProfile) -> None:
        """Initialize the compliance scorer.

        Args:
            profile: The brand voice profile to score against.
        """
        self._profile = profile

    def score(self, text: str) -> ComplianceResult:
        """Score text for brand voice compliance.

        Args:
            text: Text to evaluate.

        Returns:
            ComplianceResult with overall_score (0-1), per-rule scores,
            and list of violations.
        """
        banned_found = self.check_banned_terms(text)
        readability = self.check_readability(text)

        violations: list[str] = []
        for term in banned_found:
            violations.append(f"Banned term found: '{term}'")

        # Vocabulary score: based on preferred word usage
        preferred_count = 0
        for word in self._profile.vocabulary.preferred:
            if word.lower() in text.lower():
                preferred_count += 1
        if self._profile.vocabulary.preferred:
            vocab_score = min(1.0, preferred_count / len(self._profile.vocabulary.preferred))
        else:
            vocab_score = 1.0

        # Banned penalty: -0.3 per banned term found
        banned_penalty = len(banned_found) * 0.3
        vocab_score = max(0.0, vocab_score - banned_penalty)

        # Tone score: starts at 1.0, no banned terms means aligned
        tone_score = 1.0

        # Overall: 1.0 if no banned terms and no violations
        # Vocabulary is a bonus, not a penalty
        has_violations = len(banned_found) > 0
        if has_violations:
            overall = round(
                0.4 * vocab_score + 0.3 * readability + 0.3 * tone_score,
                4,
            )
        else:
            # No banned terms = compliant
            overall = 1.0

        overall = max(0.0, min(1.0, overall))

        return ComplianceResult(
            overall_score=overall,
            vocabulary_score=round(vocab_score, 4),
            readability_score=readability,
            tone_score=round(tone_score, 4),
            banned_terms_found=banned_found,
            violations=violations,
        )

    def check_banned_terms(self, text: str) -> list[str]:
        """Return list of banned terms found in text.

        Performs exact and case-insensitive matching against
        the profile's banned vocabulary list.

        Args:
            text: Text to scan.

        Returns:
            List of banned terms found.
        """
        text_lower = text.lower()
        found: list[str] = []
        for term in self._profile.vocabulary.banned:
            if term.lower() in text_lower:
                found.append(term)
        return found

    def check_vocabulary(self, text: str) -> dict[str, float]:
        """Check vocabulary usage against preferred/banned lists.

        Args:
            text: Text to analyze.

        Returns:
            Dict with keys like 'preferred_ratio', 'banned_ratio', etc.
        """
        text_lower = text.lower()
        preferred_used = 0
        for term in self._profile.vocabulary.preferred:
            if term.lower() in text_lower:
                preferred_used += 1

        banned_used = len(self.check_banned_terms(text))

        preferred_ratio = (
            preferred_used / len(self._profile.vocabulary.preferred)
            if self._profile.vocabulary.preferred
            else 0.0
        )
        banned_ratio = (
            banned_used / len(self._profile.vocabulary.banned)
            if self._profile.vocabulary.banned
            else 0.0
        )

        return {
            "preferred_ratio": round(preferred_ratio, 4),
            "banned_ratio": round(banned_ratio, 4),
            "preferred_count": preferred_used,
            "banned_count": banned_used,
        }

    def check_readability(self, text: str) -> float:
        """Return readability score (Flesch-Kincaid or similar).

        Args:
            text: Text to analyze.

        Returns:
            Readability score between 0.0 and 1.0.
        """
        return _flesch_kincaid_score(text)


__all__ = ["ComplianceScorer", "ComplianceResult"]
