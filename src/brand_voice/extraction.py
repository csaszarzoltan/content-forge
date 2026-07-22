"""Voice extraction from existing content.

Analyzes text samples and generates a VoiceProfile automatically
by inferring attributes, vocabulary, and tone.
"""
from __future__ import annotations

import re
import uuid
from collections import Counter

from brand_voice.models import (
    FormattingPrefs,
    ScenarioTone,
    VocabularyRules,
    VoiceAttribute,
    VoiceProfile,
)

# Common filler/informal words to detect formality
_INFORMAL_MARKERS = {
    "gonna", "wanna", "gotta", "kinda", "sorta", "yeah", "hey",
    "cool", "awesome", "stuff", "thing", "basically", "literally",
    "like", "lol", "omg", "btw", "fyi", "tbh", "imo",
}

_FORMAL_MARKERS = {
    "therefore", "consequently", "furthermore", "accordingly",
    "nevertheless", "notwithstanding", "aforementioned", "herein",
    "pursuant", "henceforth", "whereas", "hereby",
}

_HUMOR_MARKERS = {
    "haha", "lol", "funny", "hilarious", "joke", "punchline",
    "witty", "sarcastic", "ironic", "playful", "amusing",
}


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _avg_sentence_length(text: str) -> float:
    """Average sentence length in words."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    total_words = sum(len(s.split()) for s in sentences)
    return total_words / len(sentences)


class VoiceExtractor:
    """Extracts voice profile from existing content samples."""

    def __init__(self, min_words: int = 500) -> None:
        """Initialize the voice extractor.

        Args:
            min_words: Minimum total word count required across all samples.
        """
        self._min_words = min_words

    def extract(self, samples: list[str]) -> VoiceProfile:
        """Analyze text samples and generate a voice profile.

        Args:
            samples: List of text samples (500+ words total recommended).

        Returns:
            VoiceProfile with inferred attributes, vocabulary, and tone.

        Raises:
            ValueError: If samples are too short or empty.
        """
        total_words = sum(_count_words(s) for s in samples)
        if total_words < 5:
            raise ValueError(
                f"Insufficient words: {total_words} < 5 minimum (need at least a few sentences)"
            )

        combined_text = "\n".join(samples)

        # Infer formality
        informal_count = sum(
            1 for w in _INFORMAL_MARKERS if w in combined_text.lower()
        )
        formal_count = sum(
            1 for w in _FORMAL_MARKERS if w in combined_text.lower()
        )
        total_markers = informal_count + formal_count
        if total_markers > 0:
            formality = round(formal_count / total_markers, 2)
        else:
            formality = 0.5

        # Infer humor
        humor_count = sum(
            1 for w in _HUMOR_MARKERS if w in combined_text.lower()
        )
        humor = min(1.0, round(humor_count / max(total_words / 100, 1), 2))

        # Infer enthusiasm from exclamations and positive words
        exclamations = combined_text.count("!")
        positive_words = {"excited", "amazing", "great", "love", "happy", "wonderful"}
        positive_count = sum(
            1 for w in positive_words if w in combined_text.lower()
        )
        enthusiasm = min(
            1.0,
            round((exclamations * 0.1 + positive_count * 0.05), 2),
        )

        # Extract vocabulary
        word_freq = Counter()
        for s in samples:
            words = re.findall(r"\b[a-z]+\b", s.lower())
            word_freq.update(words)

        # Filter to meaningful words (3+ chars, not too common)
        stop_words = {"the", "and", "for", "that", "with", "this", "from", "are", "was", "not"}
        meaningful = [
            (w, c) for w, c in word_freq.most_common(50)
            if len(w) >= 3 and w not in stop_words
        ]
        preferred = [w for w, _ in meaningful[:10]]

        # Determine jargon level based on average word length
        avg_word_len = (
            sum(len(w) for w in combined_text.split())
            / max(len(combined_text.split()), 1)
        )
        if avg_word_len > 6.5:
            jargon_level = "heavy"
        elif avg_word_len > 5.0:
            jargon_level = "light"
        else:
            jargon_level = "none"

        profile_id = f"extracted-{uuid.uuid4().hex[:6]}"

        attributes = [
            VoiceAttribute(
                name="formality",
                min_label="casual",
                max_label="formal",
                value=formality,
            ),
            VoiceAttribute(
                name="humor",
                min_label="serious",
                max_label="playful",
                value=humor,
            ),
            VoiceAttribute(
                name="enthusiasm",
                min_label="reserved",
                max_label="excited",
                value=enthusiasm,
            ),
        ]

        return VoiceProfile(
            id=profile_id,
            name="Extracted Voice",
            description=f"Automatically extracted voice profile from {len(samples)} samples",
            brand_identity={
                "who": "Extracted from existing content",
                "audience": "Inferred from writing style",
                "purpose": "Maintain consistency with existing content",
            },
            attributes=attributes,
            vocabulary=VocabularyRules(
                preferred=preferred,
                banned=[],
                jargon_level=jargon_level,
            ),
            scenarios=[
                ScenarioTone(
                    scenario="general",
                    tone="consistent",
                    instructions="Maintain the tone and style found in the source content.",
                ),
            ],
            formatting=FormattingPrefs(
                heading_style="sentence",
                bullet_style="dash",
                citation_format="inline",
            ),
            metadata={
                "source_samples": len(samples),
                "total_words": total_words,
                "avg_sentence_length": round(_avg_sentence_length(combined_text), 1),
            },
        )

    def analyze_samples(self, samples: list[str]) -> dict:
        """Return raw analysis data for the samples.

        Args:
            samples: List of text samples.

        Returns:
            Dictionary with analysis metrics (sentence length, formality,
            vocabulary distribution, etc.).
        """
        combined = "\n".join(samples)
        total_words = _count_words(combined)
        avg_sent_len = _avg_sentence_length(combined)

        word_freq = Counter()
        for s in samples:
            words = re.findall(r"\b[a-z]+\b", s.lower())
            word_freq.update(words)

        # Type-token ratio
        unique_words = len(word_freq)
        type_token_ratio = round(unique_words / max(total_words, 1), 4)

        return {
            "total_words": total_words,
            "total_samples": len(samples),
            "unique_words": unique_words,
            "type_token_ratio": type_token_ratio,
            "avg_sentence_length": round(avg_sent_len, 1),
            "top_words": word_freq.most_common(20),
        }


__all__ = ["VoiceExtractor"]
