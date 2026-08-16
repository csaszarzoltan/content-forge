"""RED contract tests for short-video P0-5: HLS Streaming Output.

All imports come from src.short_video.hls_generator which does not exist yet.
Every test MUST fail with ModuleNotFoundError (RED) until the developer implements the module.
"""

from __future__ import annotations

import inspect
import os


# ---------------------------------------------------------------------------
# Layer 1 — Import / existence tests
# ---------------------------------------------------------------------------
class TestImports:
    """Verify that the expected public API exists in src.short_video.hls_generator."""

    def test_import_hls_generator_module(self):
        from src.short_video import hls_generator  # noqa: F401

    def test_import_hls_generator_class(self):
        from src.short_video.hls_generator import HLSGenerator  # noqa: F401

    def test_import_hls_config(self):
        from src.short_video.hls_generator import HLSConfig  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 2 — Interface / signature tests
# ---------------------------------------------------------------------------
class TestInterface:
    """Verify signatures and types for the P0-5 public API."""

    def test_hls_config_is_pydantic_model(self):
        from src.short_video.hls_generator import HLSConfig

        assert hasattr(HLSConfig, "model_fields")

    def test_hls_config_fields(self):
        from src.short_video.hls_generator import HLSConfig

        fields = HLSConfig.model_fields
        assert "output_dir" in fields
        assert "segment_duration" in fields
        assert "resolutions" in fields

    def test_hls_config_defaults(self):
        from src.short_video.hls_generator import HLSConfig

        cfg = HLSConfig()
        assert cfg.segment_duration == 6
        assert "720p" in cfg.resolutions
        assert "480p" in cfg.resolutions

    def test_hls_generator_init_signature(self):
        from src.short_video.hls_generator import HLSGenerator

        sig = inspect.signature(HLSGenerator.__init__)
        assert "config" in sig.parameters

    def test_hls_generator_has_generate_hls(self):
        from src.short_video.hls_generator import HLSGenerator

        assert hasattr(HLSGenerator, "generate_hls")
        assert callable(HLSGenerator.generate_hls)

    def test_generate_hls_is_coroutine(self):
        from src.short_video.hls_generator import HLSGenerator

        assert inspect.iscoroutinefunction(HLSGenerator.generate_hls)

    def test_generate_hls_signature(self):
        from src.short_video.hls_generator import HLSGenerator

        sig = inspect.signature(HLSGenerator.generate_hls)
        assert "video_path" in sig.parameters
        assert "clip_id" in sig.parameters

    def test_hls_generator_has_build_hls_command(self):
        from src.short_video.hls_generator import HLSGenerator

        assert hasattr(HLSGenerator, "_build_hls_command")
        assert callable(HLSGenerator._build_hls_command)

    def test_build_hls_command_signature(self):
        from src.short_video.hls_generator import HLSGenerator

        sig = inspect.signature(HLSGenerator._build_hls_command)
        assert "input_path" in sig.parameters
        assert "output_dir" in sig.parameters
        assert "resolution" in sig.parameters

    def test_hls_generator_has_generate_master_playlist(self):
        from src.short_video.hls_generator import HLSGenerator

        assert hasattr(HLSGenerator, "_generate_master_playlist")
        assert callable(HLSGenerator._generate_master_playlist)

    def test_generate_master_playlist_signature(self):
        from src.short_video.hls_generator import HLSGenerator

        sig = inspect.signature(HLSGenerator._generate_master_playlist)
        assert "playlists" in sig.parameters
        assert "clip_id" in sig.parameters


# ---------------------------------------------------------------------------
# Layer 3 — Behavioral / future tests
# ---------------------------------------------------------------------------
class TestBehavioral:
    """Behavioral expectations that will pass only after implementation."""

    def test_hls_config_segment_duration(self):
        from src.short_video.hls_generator import HLSConfig

        cfg = HLSConfig(segment_duration=10)
        assert cfg.segment_duration == 10

    def test_hls_config_custom_resolutions(self):
        from src.short_video.hls_generator import HLSConfig

        cfg = HLSConfig(resolutions=["1080p", "720p", "480p"])
        assert len(cfg.resolutions) == 3

    def test_build_hls_command_structure(self):
        from src.short_video.hls_generator import HLSGenerator

        gen = HLSGenerator()
        cmd = gen._build_hls_command(
            input_path="/tmp/clip.mp4",
            output_dir="/tmp/hls/clip1",
            resolution="720p",
        )
        assert "-f hls" in cmd or "hls" in " ".join(cmd)
        assert "segment" in " ".join(cmd).lower() or "hls_segment" in " ".join(cmd)

    def test_generate_master_playlist(self, tmp_path):
        from src.short_video.hls_generator import HLSConfig, HLSGenerator

        gen = HLSGenerator(config=HLSConfig(output_dir=str(tmp_path)))
        playlists = {
            "720p": str(tmp_path / "720p" / "stream.m3u8"),
            "480p": str(tmp_path / "480p" / "stream.m3u8"),
        }
        master_path = gen._generate_master_playlist(playlists, "test_clip")
        assert master_path.endswith("master.m3u8")
        # Verify master playlist references both resolutions
        with open(master_path) as f:
            content = f.read()
        assert "720p" in content
        assert "480p" in content

    def test_hls_generator_stores_config(self):
        from src.short_video.hls_generator import HLSConfig, HLSGenerator

        cfg = HLSConfig(segment_duration=8)
        gen = HLSGenerator(config=cfg)
        assert gen._config.segment_duration == 8

    def test_hls_generator_creates_output_dir(self, tmp_path):
        from src.short_video.hls_generator import HLSConfig, HLSGenerator

        out_dir = str(tmp_path / "hls_out")
        HLSGenerator(config=HLSConfig(output_dir=out_dir))
        assert os.path.isdir(out_dir)

    def test_hls_generator_default_config(self):
        from src.short_video.hls_generator import HLSGenerator

        gen = HLSGenerator()
        assert gen._config is not None
        assert gen._config.segment_duration == 6
