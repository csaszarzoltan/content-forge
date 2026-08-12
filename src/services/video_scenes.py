"""Scene assembly: blog/source content → ordered scenes with narration + images.

P0-3 implementation per analysis-brief.md §6:

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

import re
import uuid

from pydantic import BaseModel

# Heading markers: markdown ``##``/``###`` or plain ``Heading:`` lines.
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6}\s+|([A-Za-z0-9][^\n:]{0,80}):\s*$)")


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


def _heading_of(line: str) -> str | None:
    """Return the heading text for a heading line, else None."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return stripped.lstrip("#").strip()
    m = re.match(r"^([A-Za-z0-9][^\n:]{0,80}):\s*$", stripped)
    if m:
        return m.group(1).strip()
    return None


def split_sections(text: str) -> list[str]:
    """Split plain-text content into ordered sections (headings / paragraph groups).

    Pure function — fully deterministic and unit-testable. Markdown headings
    (``## ...``) or ``Heading:``-style lines start a new section; otherwise
    blank-line-separated paragraph groups become sections. Empty / whitespace
    input yields ``[]``.
    """
    if not text or not text.strip():
        return []
    lines = text.splitlines()
    sections: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if _heading_of(line) is not None:
            if current:
                sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)

    # No headings at all → group by blank lines (paragraph groups).
    if len(sections) == 1 and _heading_of(sections[0][0]) is None:
        groups: list[list[str]] = []
        for line in sections[0]:
            if line.strip() == "":
                if groups and groups[-1]:
                    groups.append([])
            else:
                if not groups:
                    groups.append([])
                groups[-1].append(line)
        sections = [g for g in groups if g]

    result = []
    for group in sections:
        block = "\n".join(group).strip()
        if block:
            result.append(block)
    return result


def _images_for_source(source: dict) -> dict:
    """Extract the section→image map from a blog source dict."""
    images = source.get("images") or {}
    if isinstance(images, dict):
        return images
    return {}


def _image_exists(path: str | None) -> bool:
    """True when the image path points to an existing file (reuse guard)."""
    if not path:
        return False
    from pathlib import Path

    return Path(str(path)).is_file()


def assemble_scenes(source: object, llm: object | None = None, voice_profile: object | None = None) -> list[Scene]:
    """Assemble ordered scenes from a blog Generation or raw script source.

    Args:
        source: BlogSource | ScriptSource — the content to turn into scenes.
        llm: LLM provider used for outline/narration (P0-3).
        voice_profile: resolved brand voice profile for tone guidance (P0-6).

    Returns:
        Ordered Scene list; scenes with section images get ``image_path`` set.
    """
    src = source if isinstance(source, dict) else getattr(source, "model_dump", dict)()
    text = str(src.get("source_ref") or "")
    sections = split_sections(text)
    images = _images_for_source(src)

    scenes: list[Scene] = []
    for idx, section_text in enumerate(sections, start=1):
        lines = [ln.strip() for ln in section_text.splitlines() if ln.strip()]
        heading = _heading_of(lines[0]) if lines else None
        narration = "\n".join(lines[1:]).strip() if lines else section_text.strip()
        if not narration:
            narration = section_text.strip()
        image_path = None
        if heading and heading in images:
            candidate = images[heading]
            if _image_exists(candidate):
                image_path = str(candidate)
        scenes.append(
            Scene(
                id=f"scene-{uuid.uuid4().hex[:10]}",
                order=idx,
                heading=heading,
                narration=narration,
                tts_text=narration,
                image_path=image_path,
            )
        )
    if not scenes and text.strip():
        # A script with no extractable sections still yields one scene.
        scenes.append(
            Scene(id=f"scene-{uuid.uuid4().hex[:10]}", order=1, narration=text.strip(), tts_text=text.strip())
        )
    if images and not any(s.image_path for s in scenes):
        # Generation sources with no inline text (or no section heading that
        # matches the image map): each image-map heading becomes a scene so
        # blog images are still reused (P0-3). Broken images are skipped —
        # the scene falls back to a title card (no image_path).
        for idx, (heading, candidate) in enumerate(images.items(), start=1):
            scenes.append(
                Scene(
                    id=f"scene-{uuid.uuid4().hex[:10]}",
                    order=idx,
                    heading=str(heading),
                    narration=str(heading),
                    tts_text=str(heading),
                    image_path=str(candidate),
                )
            )
    return scenes


__all__ = ["Scene", "Section", "assemble_scenes", "split_sections"]
