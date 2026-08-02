"""Pure metric math for AI visibility (analysis brief §5 M3).

Deterministic, side-effect-free functions with zero-division guards and
clamping — every formula is a pure function so tests need no DB. Canonical
definitions (brief §5 M3):

- ``citation_rate`` = citations / mentions, clamped [0.0, 1.0], 0.0 when no mentions.
- ``mention_rate`` = mentions / samples, clamped [0.0, 1.0].
- ``share_of_voice`` = own_citations / corpus_citations * 100, clamped
  [0.0, 100.0], 0.0 when corpus is empty.
- ``ai_referral_conversion_rate`` = conversions / referrals, clamped [0.0, 1.0].
- ``sentiment_average`` = mean of per-mention scores in [-1.0, 1.0], 0.0 when empty.
"""

from __future__ import annotations

import statistics


def citation_rate(citations: int, mentions: int) -> float:
    """Share of AI answers mentioning the brand that also link the content.

    Clamped to [0.0, 1.0]; 0.0 when there are no mentions (avoids division by
    zero).
    """
    if mentions <= 0:
        return 0.0
    return min(1.0, citations / mentions)


def mention_rate(mentions: int, samples: int) -> float:
    """How often the brand/content appears across the sampled answer set.

    Clamped to [0.0, 1.0]; 0.0 when no samples were taken.
    """
    if samples <= 0:
        return 0.0
    return min(1.0, mentions / samples)


def share_of_voice(own_citations: int, corpus_citations: int) -> float:
    """Content's share of all citations across the tracked corpus (percent).

    Clamped to [0.0, 100.0]; 0.0 when the corpus has no citations.
    """
    if corpus_citations <= 0:
        return 0.0
    return min(100.0, own_citations / corpus_citations * 100.0)


def ai_referral_conversion_rate(conversions: int, referrals: int) -> float:
    """Conversion rate of AI-referred visits.

    Clamped to [0.0, 1.0]; 0.0 when there are no referrals.
    """
    if referrals <= 0:
        return 0.0
    return min(1.0, conversions / referrals)


def sentiment_breakdown(labels: list[str]) -> dict[str, int]:
    """Count mentions per sentiment label.

    Returns a dict with keys ``positive``, ``neutral``, ``negative``,
    ``unknown`` — each 0 when absent from the input.
    """
    breakdown = {"positive": 0, "neutral": 0, "negative": 0, "unknown": 0}
    for label in labels:
        if label in breakdown:
            breakdown[label] += 1
    return breakdown


def sentiment_average(scores: list[float]) -> float:
    """Mean of per-mention sentiment scores.

    Clamped to [-1.0, 1.0]; 0.0 when the list is empty.
    """
    if not scores:
        return 0.0
    return min(1.0, max(-1.0, statistics.fmean(scores)))
