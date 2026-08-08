"""MP4 render + export pipeline (MoviePy 2.x + imageio-ffmpeg).

PROVISIONAL STUB — pre-development scaffold (pre-tester, t_ba5cfcec).
Runtime behavior is implemented by the developer per analysis-brief.md §6
(P0-5, P1-2, P1-4):

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

from pathlib import Path

RESOLUTIONS: dict[str, tuple[int, int]] = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
}

# Optional extra marker for the local Coqui TTS provider (P1-3).
VIDEO_COQUI_EXTRA = "video-coqui"


def render_scene(scene: object) -> Path:
    """Render one scene (image or styled title card + TTS audio) to a clip file."""
    raise NotImplementedError("video_render stub — not implemented yet")


def render_job(job_id: str, scenes: list[object], resolution: str = "720p") -> Path:
    """Render all scenes in order to an H.264 MP4 at the requested resolution."""
    raise NotImplementedError("video_render stub — not implemented yet")


def combine_scenes(paths: list[str | Path], resolution: str = "720p", out: str | Path = "") -> Path:
    """Concatenate already-rendered scene clips into one MP4 (P1-1 combine)."""
    raise NotImplementedError("video_render stub — not implemented yet")


__all__ = ["RESOLUTIONS", "VIDEO_COQUI_EXTRA", "combine_scenes", "render_job", "render_scene"]
