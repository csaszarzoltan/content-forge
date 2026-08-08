"""Long-post segmentation + combine (P1-1, US-002).

P1-1 implementation per analysis-brief.md §6:

  split_at_section_boundaries(text, cap) -> [str]
      — splits a long post at section boundaries into sequential segments,
        each ≤ cap (VIDEO_MAX_SECTION_CHARS, default 10000); a single
        section longer than cap is hard-split as a last resort.

Segments preserve narrative order; each segment job inherits the parent's
voice, style preset and brand voice so the combined MP4 has consistent
voice/style with no duplicated transitions (US-002 AC2).
"""

from __future__ import annotations

from src.services.video_scenes import split_sections


def _split_oversized(block: str, cap: int) -> list[str]:
    """Hard-split one section that exceeds the cap (last resort)."""
    parts: list[str] = []
    remaining = block
    while len(remaining) > cap:
        cut = remaining.rfind(" ", 0, cap)
        if cut <= 0:
            cut = cap
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def split_at_section_boundaries(text: str, cap: int = 10000) -> list[str]:
    """Split long text at section boundaries; each segment is ≤ cap chars.

    Short posts stay as a single segment. Sections are never torn apart
    unless a single section alone exceeds the cap (hard-split fallback),
    and narrative order is preserved.
    """
    if not text or not text.strip():
        return []
    if len(text) <= cap:
        return [text]
    sections = split_sections(text)
    segments: list[str] = []
    current = ""
    for section in sections:
        if len(section) > cap:
            if current:
                segments.append(current)
                current = ""
            segments.extend(_split_oversized(section, cap))
            continue
        if current and len(current) + len(section) + 1 > cap:
            segments.append(current)
            current = section
        else:
            current = f"{current}\n{section}" if current else section
    if current:
        segments.append(current)
    return segments


__all__ = ["split_at_section_boundaries"]
