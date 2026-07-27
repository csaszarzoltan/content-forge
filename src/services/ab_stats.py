"""Statistical significance calculator for A/B testing.

Provides chi-squared and z-test based significance calculations
using scipy.stats.
"""

from __future__ import annotations

import math

from pydantic import BaseModel


class SignificanceResult(BaseModel):
    """Result of a statistical significance calculation."""

    chi_square_statistic: float
    p_value: float
    dof: int
    expected_frequencies: list[list[float]]
    z_score: float | None = None
    sufficient_data: bool = True
    method: str = "chi-squared"


class AbStatsService:
    """Statistical calculator for A/B test significance tests.

    Uses scipy.stats.chi2_contingency for the canonical chi-squared
    test and derives z-scores for 2-variant comparisons.
    """

    @staticmethod
    def calculate_significance(
        counts: list[tuple[int, int]],
    ) -> SignificanceResult:
        """Perform chi-squared test on a 2xk contingency table.

        Args:
            counts: List of (impressions, conversions) tuples, one per variant.

        Returns:
            SignificanceResult with chi-squared statistic, p-value, etc.

        Raises:
            ValueError: If fewer than 2 variants are provided.
        """
        if len(counts) < 2:
            raise ValueError("At least 2 variants are required")

        # Build contingency table: each row is [conversions, non-conversions]
        observed: list[list[float]] = []
        for impressions, conversions in counts:
            observed.append([float(conversions), float(impressions - conversions)])

        # Handle edge case: if all conversions in a column are zero or
        # expected frequencies contain zeros, scipy raises ValueError.
        from scipy.stats import chi2_contingency

        try:
            chi2, p, dof, expected = chi2_contingency(observed, correction=False)
        except ValueError:
            # Fallback: no detectable difference
            chi2, p, dof = 0.0, 1.0, min(len(counts) - 1, 1)
            expected = observed  # type: ignore[assignment]

        # Calculate z-score comparing first two variants
        z_score: float | None = None
        if len(counts) >= 2 and counts[0][0] > 0 and counts[1][0] > 0:
            p1 = counts[0][1] / counts[0][0]
            p2 = counts[1][1] / counts[1][0]
            se = math.sqrt(
                p1 * (1 - p1) / counts[0][0]
                + p2 * (1 - p2) / counts[1][0]
            )
            if se > 0:
                z_score = (p1 - p2) / se
            else:
                z_score = 0.0

        return SignificanceResult(
            chi_square_statistic=float(chi2),
            p_value=float(p),
            dof=int(dof),
            expected_frequencies=[[float(v) for v in row] for row in expected],
            z_score=z_score,
            sufficient_data=True,
            method="chi-squared",
        )

    @staticmethod
    def needs_more_data(
        counts: list[tuple[int, int]], min_per_variant: int = 30
    ) -> bool:
        """Check if any variant has fewer than min_per_variant impressions.

        Args:
            counts: List of (impressions, conversions) tuples.
            min_per_variant: Minimum impressions required per variant.

        Returns:
            True if any variant has fewer impressions than the minimum.
        """
        for impressions, _ in counts:
            if impressions < min_per_variant:
                return True
        return False

    @staticmethod
    def format_confidence(p_value: float) -> str:
        """Return a human-readable confidence string.

        Examples: '95.0%', '99.0%', 'Insufficient data'.

        Returns:
            Formatted confidence string based on p-value.
        """
        if p_value < 0 or p_value > 1:
            return "Invalid p-value"
        if p_value > 0.1:
            return "Insufficient data"
        confidence = (1 - p_value) * 100
        return f"{confidence:.1f}%"
