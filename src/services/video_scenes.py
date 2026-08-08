"""Scene assembly: blog/source content → ordered scenes with narration + images.

PROVISIONAL STUB — pre-development scaffold (pre-tester, t_ba5cfcec).
Runtime behavior is implemented by the developer per analysis-brief.md §6
(P0-3, P0-6):

  split_sections(text: str) -> list[str]        — pure, unit-testable
  assemble_scenes(source, llm, voice_profile) -> list[Scene]
  Scene = {id, order, heading, narration, tts_text, image_path | None}

Blog images referenced in the post HTML/parameters are reused: the image in
each section attaches to the nearest scene as ``image_path``; broken images
are skipped (fallback to title card). Plain-text scripts produce scenes from
paragraph groups with no images. When ``brand_voice_id`` is present the
resolved voice profile injects tone guidance into the narration prompts.
"""

from __future__ import annotations

from pydantic import BaseModel


class Scene(BaseModel):
    """One video scene: narration text plus optional reused blog image."""

    id: str
    order: int
    heading: str | None = None
    narration: str = ""
    tts_text: str = ""
    image_path: str | None = None


class Section(BaseModel):
    """A content section extracted from a blog post or script."""

    heading: str | None = None
    text: str = ""


def split_sections(text: str) -> list[str]:
    """Split plain-text content into ordered sections (headings / paragraph groups).

    Pure function — must be fully deterministic and unit-testable.
    """
    raise NotImplementedError("video_scenes stub — not implemented yet")


def assemble_scenes(source: object, llm: object | None = None, voice_profile: object | None = None) -> list[Scene]:
    """Assemble ordered scenes from a blog Generation or raw script source.

    Args:
        source: BlogSource | ScriptSource — the content to turn into scenes.
        llm: LLM provider used for outline/narration (P0-3).
        voice_profile: resolved brand voice profile for tone guidance (P0-6).

    Returns:
        Ordered Scene list; scenes with section images get ``image_path`` set.
    """
    raise NotImplementedError("video_scenes stub — not implemented yet")


__all__ = ["Scene", "Section", "assemble_scenes", "split_sections"]
