"""Long-post segmentation + combine (P1-1, US-002).

PROVISIONAL STUB — pre-development scaffold (pre-tester, t_ba5cfcec).
Runtime behavior is implemented by the developer per analysis-brief.md §6:

  split_at_section_boundaries(text, cap) -> [str]
      — splits a long post at section boundaries into sequential segments,
        each ≤ cap (VIDEO_MAX_SECTION_CHARS, default 10000); a single
        section longer than cap is hard-split as a last resort.

Segments preserve narrative order; each segment job inherits the parent's
voice, style preset and brand voice so the combined MP4 has consistent
voice/style with no duplicated transitions (US-002 AC2).
"""

from __future__ import annotations


def split_at_section_boundaries(text: str, cap: int = 10000) -> list[str]:
    """Split long text at section boundaries; each segment is ≤ cap chars."""
    raise NotImplementedError("video_segments stub — not implemented yet")


__all__ = ["split_at_section_boundaries"]
