"""Interface + behavioral tests for M3 — pure metric math.

Interface tests verify the six public functions exist with the exact
signatures from brief §5 M3 — these PASS immediately. Behavioral tests assert
the canonical formulas including zero-division guards and clamping; against
the stubs they FAIL with ``NotImplementedError`` (TDD RED phase).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from src.ai_visibility.metrics import (
    ai_referral_conversion_rate,
    citation_rate,
    mention_rate,
    sentiment_average,
    sentiment_breakdown,
    share_of_voice,
)

FUNCTIONS = [
    citation_rate,
    mention_rate,
    share_of_voice,
    ai_referral_conversion_rate,
    sentiment_breakdown,
    sentiment_average,
]


def _ret_annotation(fn):
    """Return annotation base name, tolerating `from __future__ import
    annotations` (string) vs a real class, and subscripted generics such as
    ``dict[str, int]`` -> ``dict``."""
    ann = inspect.signature(fn).return_annotation
    if isinstance(ann, str):
        return ann.split("[", 1)[0]
    return ann.__name__


# ============================================================================
# SECTION 1 — INTERFACE TESTS (PASS immediately)
# ============================================================================


class TestMetricsInterface:
    """Verify imports, signatures, parameter names and return annotations."""

    def test_module_importable(self):
        assert all(callable(fn) for fn in FUNCTIONS)

    @pytest.mark.parametrize("fn, params, ret", [
        (citation_rate, ("citations", "mentions"), "float"),
        (mention_rate, ("mentions", "samples"), "float"),
        (share_of_voice, ("own_citations", "corpus_citations"), "float"),
        (ai_referral_conversion_rate, ("conversions", "referrals"), "float"),
        (sentiment_breakdown, ("labels",), "dict"),
        (sentiment_average, ("scores",), "float"),
    ])
    def test_signature(self, fn, params, ret):
        """Exact parameter names and float/dict return annotations (brief §5 M3)."""
        sig = inspect.signature(fn)
        assert tuple(sig.parameters) == params
        assert _ret_annotation(fn) == ret

    def test_no_defaults_required(self):
        """All six functions require every parameter (no defaults)."""
        for fn in FUNCTIONS:
            sig = inspect.signature(fn)
            assert all(
                p.default is inspect.Parameter.empty for p in sig.parameters.values()
            )


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestCitationRateBehavioral:
    """citation_rate = citations / mentions, clamped [0,1], 0.0 when no mentions."""

    @pytest.mark.parametrize("citations, mentions, expected", [
        (2, 4, 0.5),      # basic ratio
        (1, 3, 1 / 3),    # non-terminating ratio
        (0, 5, 0.0),      # no citations
        (5, 3, 1.0),      # clamp: citations > mentions -> 1.0
        (0, 0, 0.0),      # no mentions -> 0.0 (zero-division guard)
        (7, 0, 0.0),      # mentions == 0 with citations -> 0.0
    ])
    def test_formula(self, citations, mentions, expected):
        assert citation_rate(citations, mentions) == pytest.approx(expected)


class TestMentionRateBehavioral:
    """mention_rate = mentions / samples, clamped [0,1], 0.0 when no samples."""

    @pytest.mark.parametrize("mentions, samples, expected", [
        (3, 10, 0.3),
        (0, 5, 0.0),
        (7, 0, 0.0),      # zero-division guard
        (12, 5, 1.0),     # clamp
    ])
    def test_formula(self, mentions, samples, expected):
        assert mention_rate(mentions, samples) == pytest.approx(expected)


class TestShareOfVoiceBehavioral:
    """share_of_voice = own/corpus * 100, clamped [0,100], 0.0 when empty."""

    @pytest.mark.parametrize("own, corpus, expected", [
        (10, 100, 10.0),      # basic percent
        (1, 4, 25.0),         # quarter share
        (0, 50, 0.0),         # no own citations
        (150, 100, 100.0),    # clamp at 100
        (5, 0, 0.0),          # empty corpus -> 0.0
        (0, 0, 0.0),          # both zero -> 0.0
    ])
    def test_formula(self, own, corpus, expected):
        assert share_of_voice(own, corpus) == pytest.approx(expected)


class TestReferralConversionRateBehavioral:
    """ai_referral_conversion_rate = conversions / referrals, clamped [0,1]."""

    @pytest.mark.parametrize("conversions, referrals, expected", [
        (2, 4, 0.5),
        (0, 3, 0.0),
        (5, 2, 1.0),      # clamp
        (3, 0, 0.0),      # zero-division guard
    ])
    def test_formula(self, conversions, referrals, expected):
        assert ai_referral_conversion_rate(conversions, referrals) == pytest.approx(
            expected
        )


class TestSentimentBehavioral:
    """sentiment_breakdown counts labels; sentiment_average means scores."""

    def test_breakdown_counts(self):
        labels = ["positive", "neutral", "positive", "negative", "unknown",
                  "positive"]
        assert sentiment_breakdown(labels) == {
            "positive": 3,
            "neutral": 1,
            "negative": 1,
            "unknown": 1,
        }

    def test_breakdown_empty(self):
        assert sentiment_breakdown([]) == {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "unknown": 0,
        }

    def test_average_mixed(self):
        assert sentiment_average([1.0, 0.0, -1.0, 0.5]) == pytest.approx(0.125)

    def test_average_empty(self):
        assert sentiment_average([]) == 0.0

    def test_average_single(self):
        assert sentiment_average([-0.75]) == pytest.approx(-0.75)
