"""RED contract tests for short-video P0-4: Clip Generator with Face Tracking & Subtitles.

All imports come from src.short_video.clip_generator which does not exist yet.
Every test MUST fail with ModuleNotFoundError (RED) until the developer implements the module.
"""

from __future__ import annotations

import inspect


# ---------------------------------------------------------------------------
# Layer 1 — Import / existence tests
# ---------------------------------------------------------------------------
class TestImports:
    """Verify that the expected public API exists in src.short_video.clip_generator."""

    def test_import_clip_generator_module(self):
        from src.short_video import clip_generator  # noqa: F401

    def test_import_clip_generator_class(self):
        from src.short_video.clip_generator import ClipGenerator  # noqa: F401

    def test_import_clip_config(self):
        from src.short_video.clip_generator import ClipConfig  # noqa: F401

    def test_import_crop_region(self):
        from src.short_video.clip_generator import CropRegion  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 2 — Interface / signature tests
# ---------------------------------------------------------------------------
class TestInterface:
    """Verify signatures and types for the P0-4 public API."""

    def test_crop_region_is_pydantic_model(self):
        from src.short_video.clip_generator import CropRegion

        assert hasattr(CropRegion, "model_fields")

    def test_crop_region_fields(self):
        from src.short_video.clip_generator import CropRegion

        fields = CropRegion.model_fields
        assert "x" in fields
        assert "y" in fields
        assert "width" in fields
        assert "height" in fields

    def test_clip_config_is_pydantic_model(self):
        from src.short_video.clip_generator import ClipConfig

        assert hasattr(ClipConfig, "model_fields")

    def test_clip_config_fields(self):
        from src.short_video.clip_generator import ClipConfig

        fields = ClipConfig.model_fields
        assert "output_width" in fields
        assert "output_height" in fields
        assert "subtitle_font" in fields
        assert "subtitle_fontsize" in fields
        assert "subtitle_color" in fields
        assert "subtitle_bg_color" in fields
        assert "subtitle_position" in fields
        assert "add_hook_text" in fields

    def test_clip_config_defaults(self):
        from src.short_video.clip_generator import ClipConfig

        cfg = ClipConfig()
        assert cfg.output_width == 1080
        assert cfg.output_height == 1920
        assert cfg.subtitle_fontsize == 48
        assert cfg.subtitle_color == "white"
        assert cfg.add_hook_text is True

    def test_clip_generator_init_signature(self):
        from src.short_video.clip_generator import ClipGenerator

        sig = inspect.signature(ClipGenerator.__init__)
        assert "config" in sig.parameters

    def test_clip_generator_has_generate_clip(self):
        from src.short_video.clip_generator import ClipGenerator

        assert hasattr(ClipGenerator, "generate_clip")
        assert callable(ClipGenerator.generate_clip)

    def test_generate_clip_is_coroutine(self):
        from src.short_video.clip_generator import ClipGenerator

        assert inspect.iscoroutinefunction(ClipGenerator.generate_clip)

    def test_generate_clip_signature(self):
        from src.short_video.clip_generator import ClipGenerator

        sig = inspect.signature(ClipGenerator.generate_clip)
        assert "video_path" in sig.parameters
        assert "moment" in sig.parameters
        assert "transcript" in sig.parameters
        assert "output_path" in sig.parameters

    def test_clip_generator_has_detect_faces(self):
        from src.short_video.clip_generator import ClipGenerator

        assert hasattr(ClipGenerator, "_detect_faces")
        assert callable(ClipGenerator._detect_faces)

    def test_detect_faces_signature(self):
        from src.short_video.clip_generator import ClipGenerator

        sig = inspect.signature(ClipGenerator._detect_faces)
        assert "video_path" in sig.parameters
        assert "start" in sig.parameters
        assert "end" in sig.parameters

    def test_clip_generator_has_compute_crop_region(self):
        from src.short_video.clip_generator import ClipGenerator

        assert hasattr(ClipGenerator, "_compute_crop_region")
        assert callable(ClipGenerator._compute_crop_region)

    def test_compute_crop_region_signature(self):
        from src.short_video.clip_generator import ClipGenerator

        sig = inspect.signature(ClipGenerator._compute_crop_region)
        assert "faces" in sig.parameters
        assert "source_width" in sig.parameters
        assert "source_height" in sig.parameters

    def test_clip_generator_has_get_subtitle_text(self):
        from src.short_video.clip_generator import ClipGenerator

        assert hasattr(ClipGenerator, "_get_subtitle_text")
        assert callable(ClipGenerator._get_subtitle_text)

    def test_get_subtitle_text_signature(self):
        from src.short_video.clip_generator import ClipGenerator

        sig = inspect.signature(ClipGenerator._get_subtitle_text)
        assert "transcript" in sig.parameters
        assert "start" in sig.parameters
        assert "end" in sig.parameters

    def test_clip_generator_has_build_ffmpeg_command(self):
        from src.short_video.clip_generator import ClipGenerator

        assert hasattr(ClipGenerator, "_build_ffmpeg_command")
        assert callable(ClipGenerator._build_ffmpeg_command)

    def test_build_ffmpeg_command_signature(self):
        from src.short_video.clip_generator import ClipGenerator

        sig = inspect.signature(ClipGenerator._build_ffmpeg_command)
        assert "video_path" in sig.parameters
        assert "crop" in sig.parameters
        assert "subtitle_text" in sig.parameters
        assert "output_path" in sig.parameters
        assert "duration" in sig.parameters


# ---------------------------------------------------------------------------
# Layer 3 — Behavioral / future tests
# ---------------------------------------------------------------------------
class TestBehavioral:
    """Behavioral expectations that will pass only after implementation."""

    def test_crop_region_model_construction(self):
        from src.short_video.clip_generator import CropRegion

        crop = CropRegion(x=100, y=200, width=1080, height=1920)
        assert crop.width == 1080
        assert crop.height == 1920
        assert crop.x == 100
        assert crop.y == 200

    def test_compute_crop_center_fallback(self):
        """No faces detected → center crop."""
        from src.short_video.clip_generator import ClipGenerator

        gen = ClipGenerator()
        crop = gen._compute_crop_region([], 1920, 1080)
        assert crop.width == 1080
        assert crop.height == 1920

    def test_compute_crop_with_faces(self):
        from src.short_video.clip_generator import ClipGenerator

        gen = ClipGenerator()
        faces = [{"x": 400, "y": 200, "w": 200, "h": 200, "frame": 0.0}]
        crop = gen._compute_crop_region(faces, 1920, 1080)
        assert crop.width == 1080
        assert crop.height == 1920

    def test_get_subtitle_text_filters_by_time(self):
        from src.short_video.clip_generator import ClipGenerator
        from src.short_video.transcription import (
            TranscriptionResult,
            TranscriptSegment,
            WordTiming,
        )

        gen = ClipGenerator()
        transcript = TranscriptionResult(
            language="en",
            language_probability=0.99,
            duration=60.0,
            segments=[
                TranscriptSegment(
                    start=0,
                    end=5,
                    text="Hello world",
                    words=[
                        WordTiming(word="Hello", start=0, end=0.5),
                        WordTiming(word="world", start=0.5, end=1.0),
                    ],
                ),
                TranscriptSegment(
                    start=10,
                    end=15,
                    text="Later text",
                    words=[WordTiming(word="Later", start=10, end=10.5)],
                ),
            ],
        )
        text = gen._get_subtitle_text(transcript, 0.0, 5.0)
        assert "Hello" in text
        assert "Later" not in text  # outside time range

    def test_build_ffmpeg_command_structure(self):
        from src.short_video.clip_generator import ClipGenerator, CropRegion

        gen = ClipGenerator()
        cmd = gen._build_ffmpeg_command(
            video_path="/tmp/test.mp4",
            crop=CropRegion(x=420, y=0, width=1080, height=1920),
            subtitle_text="Hello",
            output_path="/tmp/out.mp4",
            duration=15.0,
        )
        assert "-ss" in cmd or "-t" in cmd  # seek/duration flags
        assert "-vf" in cmd  # video filter chain
        assert "crop" in " ".join(cmd)  # crop filter present
        assert "/tmp/out.mp4" in cmd  # output path

    def test_clip_generator_stores_config(self):
        from src.short_video.clip_generator import ClipConfig, ClipGenerator

        cfg = ClipConfig(output_width=720, output_height=1280)
        gen = ClipGenerator(config=cfg)
        assert gen._config.output_width == 720

    def test_clip_generator_default_config(self):
        from src.short_video.clip_generator import ClipGenerator

        gen = ClipGenerator()
        assert gen._config is not None
        assert gen._config.output_width == 1080
