"""MP4 render + export pipeline (MoviePy 2.x + imageio-ffmpeg).

P0-5/P1-2/P1-4 implementation per analysis-brief.md §6:

  RESOLUTIONS = {"480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080)}
  render_job(job_id, scenes, resolution) -> Path
  render_scene(scene) -> Path
  combine_scenes(paths, resolution, out) -> Path

Render runs via imageio-ffmpeg's bundled binary — NO dependency on system
ffmpeg (verified absent on the host). CPU-bound render MUST run in an
executor thread (repo rule: no blocking calls in async). Partial export
renders only ``done`` scenes (P1-2, US-003).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
)

RESOLUTIONS: dict[str, tuple[int, int]] = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
}

# Optional extra marker for the local Coqui TTS provider (P1-3).
VIDEO_COQUI_EXTRA = "video-coqui"

_RENDER_ROOT = Path(os.getenv("VIDEO_RENDER_DIR", "/tmp/contentforge_video"))


def _style_for(preset: str | None) -> dict:
    """Resolve a style preset to title-card colors (P1-4)."""
    if preset == "documentary":
        return {"bg": (28, 25, 23), "fg": "white"}
    return {"bg": (15, 23, 42), "fg": "white"}  # explainer default


def _title_card(scene: dict, size: tuple[int, int], preset: str | None) -> ImageClip:
    """Build a styled title card for a scene without an image."""
    w = size[0]
    style = _style_for(preset)
    background = ColorClip(size=size, color=style["bg"], duration=1.0)
    heading = str(scene.get("heading") or scene.get("id") or "Scene")
    text = TextClip(
        text=heading,
        font_size=max(28, w // 28),
        color=style["fg"],
        method="caption",
        size=(int(w * 0.9), None),
        duration=1.0,
    )
    return CompositeVideoClip([background, text.with_position("center")], size=size)


def _scene_image(scene: dict, size: tuple[int, int]) -> ImageClip:
    """Load the scene's reused blog image, or fall back to a title card."""
    image_path = scene.get("image_path")
    if image_path and Path(str(image_path)).is_file():
        try:
            clip = ImageClip(str(image_path)).resized(new_size=size)
            return clip
        except (OSError, ValueError):
            pass  # broken image → title card fallback
    return _title_card(scene, size, scene.get("style_preset"))


def render_scene(scene: object) -> Path:
    """Render one scene (image or styled title card + TTS audio) to a clip file.

    Scenes are dicts with ``id``, ``heading``, ``audio_path``/``narration``
    and optional ``image_path``/``style_preset``. Returns the MP4 clip path.
    Idempotent: a clip already rendered for this scene id + resolution is
    returned as-is (the worker caches per-scene clips so combine can reuse
    them — see ``clip_path_for``).
    """
    scene_dict = scene if isinstance(scene, dict) else getattr(scene, "model_dump", lambda: dict(scene))()
    resolution = str(scene_dict.get("resolution") or "720p")
    if resolution not in RESOLUTIONS:
        raise ValueError(f"unsupported resolution: {resolution}")
    size = RESOLUTIONS[resolution]
    scene_id = str(scene_dict.get("id") or "scene")
    render_dir = _RENDER_ROOT / "scenes" / scene_id
    out = render_dir / f"{scene_id}_{resolution}.mp4"
    if out.is_file() and out.stat().st_size > 0:
        return out  # already rendered — reuse the cached clip

    render_dir.mkdir(parents=True, exist_ok=True)
    image_clip = _scene_image(scene_dict, size)
    audio_path = scene_dict.get("audio_path")
    audio = AudioFileClip(str(audio_path)) if audio_path and Path(str(audio_path)).is_file() else None
    if audio is not None:
        image_clip = image_clip.with_duration(audio.duration).with_audio(audio)
    else:
        image_clip = image_clip.with_duration(1.0)
    _write_clip(image_clip, out)
    if audio is not None:
        audio.close()
    image_clip.close()
    return out


def clip_path_for(scene: object, resolution: str = "720p") -> Path:
    """Return the deterministic clip path for a scene (may not exist yet).

    Mirrors ``render_scene``'s output layout so callers (the worker cache,
    the combine endpoint) can resolve a scene's rendered MP4 without
    re-rendering or guessing paths.
    """
    scene_dict = scene if isinstance(scene, dict) else getattr(scene, "model_dump", lambda: dict(scene))()
    res = str(scene_dict.get("resolution") or resolution or "720p")
    if res not in RESOLUTIONS:
        res = "720p"
    scene_id = str(scene_dict.get("id") or "scene")
    return _RENDER_ROOT / "scenes" / scene_id / f"{scene_id}_{res}.mp4"


def render_job(job_id: str, scenes: list[object], resolution: str = "720p") -> Path:
    """Render all scenes in order to an H.264 MP4 at the requested resolution.

    Scenes without audio are rendered as still title cards so the job always
    produces a playable MP4 (≥1 frame per scene, H.264 + AAC).
    """
    if resolution not in RESOLUTIONS:
        raise ValueError(f"unsupported resolution: {resolution}")
    job_dir = _RENDER_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    out = job_dir / f"export_{resolution}.mp4"

    clips: list[object] = []
    for scene in scenes:
        scene_dict = scene if isinstance(scene, dict) else getattr(scene, "model_dump", dict)()
        scene_dict = dict(scene_dict)
        scene_dict["resolution"] = resolution
        clip_path = render_scene(scene_dict)
        clips.append(clip_path)

    if clips:
        _concat_to(out, clips, resolution)
    else:
        # No scenes at all → still emit a valid single-card MP4.
        _concat_to(out, [], resolution)
    return out


def combine_scenes(paths: list[str | Path], resolution: str = "720p", out: str | Path = "") -> Path:
    """Concatenate already-rendered scene clips into one MP4 (P1-1 combine)."""
    if resolution not in RESOLUTIONS:
        raise ValueError(f"unsupported resolution: {resolution}")
    out_path = Path(out) if out else _RENDER_ROOT / "combined" / "combined.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _concat_to(out_path, [Path(p) for p in paths], resolution)
    return out_path


def _write_clip(clip, out: Path) -> None:
    """Write one clip to MP4 (H.264 + AAC, yuv420p for player compat).

    ``temp_audiofile_path`` is pinned to the output's own directory: moviepy
    otherwise writes its ``<name>TEMP_MPY_wvf_snd.<ext>`` temp audio into the
    process CWD, which collides when concurrent workers render different
    jobs (shared repo root → broken pipe / invalid data). Per-output temp
    files keep concurrent renders isolated (BLOCKER-1 review t_db9e57ad).
    """
    clip.write_videofile(
        str(out),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        ffmpeg_params=["-pix_fmt", "yuv420p"],
        temp_audiofile_path=str(out.parent),
        logger=None,
    )


def _concat_to(out: Path, paths: list[Path], resolution: str) -> None:
    """Concatenate clips (or emit a blank card when empty) to ``out``."""
    if paths:
        from moviepy import VideoFileClip

        clips = []
        try:
            for p in paths:
                try:
                    clips.append(VideoFileClip(str(p)))
                except (OSError, ValueError):
                    # Unreadable/invalid clip (e.g. a stub file): fall back to a
                    # title card so the combined output is still playable.
                    style = _style_for(None)
                    card = ColorClip(size=RESOLUTIONS[resolution], color=style["bg"], duration=1.0)
                    clips.append(card)
            composed = concatenate_videoclips([c for c in clips if c is not None])
            _write_clip(composed, out)
            composed.close()
        finally:
            for c in clips:
                if c is not None:
                    try:
                        c.close()
                    except (OSError, ValueError):
                        pass
        return
    # Empty scene list → a minimal blank MP4 so export still streams a file.
    size = RESOLUTIONS[resolution]
    blank = ColorClip(size=size, color=(15, 23, 42), duration=1.0)
    _write_clip(blank, out)
    blank.close()


def _ffmpeg_exe() -> str:
    """Return the imageio-ffmpeg bundled binary (no system ffmpeg dependency)."""
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _probe_duration(path: Path) -> float:
    """Return the video duration in seconds via ffprobe-style ffmpeg probe."""
    try:
        exe = _ffmpeg_exe()
        result = subprocess.run(
            [exe, "-i", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        for line in (result.stderr or "").splitlines():
            if "Duration:" in line:
                token = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
                parts = token.split(":")
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 0.0


__all__ = ["RESOLUTIONS", "VIDEO_COQUI_EXTRA", "clip_path_for", "combine_scenes", "render_job", "render_scene"]
