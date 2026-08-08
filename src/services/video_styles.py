"""Style presets + aspect-ratio mapping for the video render (P1-4).

PROVISIONAL STUB — pre-development scaffold (pre-tester, t_ba5cfcec).
Runtime behavior is implemented by the developer per analysis-brief.md §6:

  STYLE_PRESETS = {
      "explainer":   {...title card, colors, font sizes, caption style...},
      "documentary": {...serif/dark, lower-third captions...},
  }
  aspect_ratio maps to canvas dims per resolution (16:9 / 9:16 / 1:1).

Style is applied to title cards/captions during render and stored on the job.
"""

from __future__ import annotations

STYLE_PRESETS: dict[str, dict[str, object]] = {
    "explainer": {
        "title_card": {"bg": "#0f172a", "fg": "#f8fafc"},
        "font": "sans",
        "caption_style": "center",
    },
    "documentary": {
        "title_card": {"bg": "#1c1917", "fg": "#fafaf9"},
        "font": "serif",
        "caption_style": "lower-third",
    },
}

ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "1:1": (1, 1),
}

__all__ = ["ASPECT_RATIOS", "STYLE_PRESETS"]
