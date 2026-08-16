"""RED contract tests for short-video P0-1: Video Ingestion & Storage.

All imports come from src.short_video.* which does not exist yet.
Every test MUST fail with ModuleNotFoundError (RED) until the developer implements the module.
"""

from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# Layer 1 — Import / existence tests
# ---------------------------------------------------------------------------
class TestImports:
    """Verify that the expected public API exists in src.short_video.ingestion."""

    def test_import_ingestion_module(self):
        from src.short_video import ingestion  # noqa: F401

    def test_import_ingestion_config(self):
        from src.short_video.ingestion import IngestionConfig  # noqa: F401

    def test_import_video_ingestor(self):
        from src.short_video.ingestion import VideoIngestor  # noqa: F401

    def test_import_supported_formats(self):
        from src.short_video import SUPPORTED_INPUT_FORMATS  # noqa: F401

    def test_import_max_upload_size(self):
        from src.short_video import MAX_UPLOAD_SIZE_MB  # noqa: F401

    def test_import_chunk_size(self):
        from src.short_video import CHUNK_SIZE_BYTES  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 2 — Interface / signature tests
# ---------------------------------------------------------------------------
class TestInterface:
    """Verify signatures and types for the P0-1 public API."""

    def test_supported_input_formats_is_frozenset(self):
        from src.short_video import SUPPORTED_INPUT_FORMATS

        assert isinstance(SUPPORTED_INPUT_FORMATS, frozenset)

    def test_supported_input_formats_contains_expected(self):
        from src.short_video import SUPPORTED_INPUT_FORMATS

        expected = {"mp4", "mov", "avi", "mkv", "webm", "flv", "wmv"}
        assert expected.issubset(SUPPORTED_INPUT_FORMATS)

    def test_max_upload_size_mb_is_positive_int(self):
        from src.short_video import MAX_UPLOAD_SIZE_MB

        assert isinstance(MAX_UPLOAD_SIZE_MB, int)
        assert MAX_UPLOAD_SIZE_MB > 0

    def test_chunk_size_bytes_is_positive_int(self):
        from src.short_video import CHUNK_SIZE_BYTES

        assert isinstance(CHUNK_SIZE_BYTES, int)
        assert CHUNK_SIZE_BYTES > 0

    def test_ingestion_config_is_pydantic_model(self):
        from src.short_video.ingestion import IngestionConfig

        # Pydantic v2: check model_fields exists
        assert hasattr(IngestionConfig, "model_fields")

    def test_ingestion_config_has_storage_dir(self):
        from src.short_video.ingestion import IngestionConfig

        assert "storage_dir" in IngestionConfig.model_fields

    def test_ingestion_config_has_max_file_size_mb(self):
        from src.short_video.ingestion import IngestionConfig

        assert "max_file_size_mb" in IngestionConfig.model_fields

    def test_ingestion_config_has_allowed_formats(self):
        from src.short_video.ingestion import IngestionConfig

        assert "allowed_formats" in IngestionConfig.model_fields

    def test_ingestion_config_defaults(self):
        from src.short_video import SUPPORTED_INPUT_FORMATS
        from src.short_video.ingestion import IngestionConfig

        cfg = IngestionConfig()
        assert cfg.storage_dir == "/tmp/short_video_uploads"
        assert cfg.max_file_size_mb > 0
        assert set(cfg.allowed_formats) == set(SUPPORTED_INPUT_FORMATS)

    def test_video_ingestor_init_signature(self):
        from src.short_video.ingestion import VideoIngestor

        sig = inspect.signature(VideoIngestor.__init__)
        assert "config" in sig.parameters

    def test_video_ingestor_has_ingest_upload(self):
        from src.short_video.ingestion import VideoIngestor

        assert hasattr(VideoIngestor, "ingest_upload")
        assert callable(VideoIngestor.ingest_upload)

    def test_video_ingestor_has_ingest_url(self):
        from src.short_video.ingestion import VideoIngestor

        assert hasattr(VideoIngestor, "ingest_url")
        assert callable(VideoIngestor.ingest_url)

    def test_video_ingestor_has_get_video_info(self):
        from src.short_video.ingestion import VideoIngestor

        assert hasattr(VideoIngestor, "get_video_info")
        assert callable(VideoIngestor.get_video_info)

    def test_get_video_info_signature(self):
        from src.short_video.ingestion import VideoIngestor

        sig = inspect.signature(VideoIngestor.get_video_info)
        assert "path" in sig.parameters

    def test_ingest_upload_is_coroutine(self):
        from src.short_video.ingestion import VideoIngestor

        assert inspect.iscoroutinefunction(VideoIngestor.ingest_upload)

    def test_ingest_url_is_coroutine(self):
        from src.short_video.ingestion import VideoIngestor

        assert inspect.iscoroutinefunction(VideoIngestor.ingest_url)


# ---------------------------------------------------------------------------
# Layer 3 — Behavioral / future tests
# ---------------------------------------------------------------------------
class TestBehavioral:
    """Behavioral expectations that will pass only after implementation."""

    def test_ingestion_config_allowed_formats_default(self):
        """Config defaults to SUPPORTED_INPUT_FORMATS."""
        from src.short_video.ingestion import IngestionConfig

        cfg = IngestionConfig()
        assert "mp4" in cfg.allowed_formats
        assert "exe" not in cfg.allowed_formats

    def test_get_video_info_missing_file(self):
        """get_video_info raises FileNotFoundError for nonexistent file."""
        from src.short_video.ingestion import VideoIngestor

        ingestor = VideoIngestor()
        with pytest.raises(FileNotFoundError):
            ingestor.get_video_info("/nonexistent/video.mp4")

    def test_ingestor_stores_config(self):
        """VideoIngestor stores the config it was given."""
        from src.short_video.ingestion import IngestionConfig, VideoIngestor

        cfg = IngestionConfig(storage_dir="/custom/dir")
        ingestor = VideoIngestor(config=cfg)
        assert ingestor._config.storage_dir == "/custom/dir"

    def test_ingestor_default_config(self):
        """VideoIngestor uses default IngestionConfig when None."""
        from src.short_video.ingestion import VideoIngestor

        ingestor = VideoIngestor()
        assert ingestor._config is not None
        assert ingestor._config.storage_dir == "/tmp/short_video_uploads"
