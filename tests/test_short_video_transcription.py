"""RED contract tests for short-video P0-2: Transcription Service.

All imports come from src.short_video.transcription which does not exist yet.
Every test MUST fail with ModuleNotFoundError (RED) until the developer implements the module.
"""

from __future__ import annotations

import inspect


# ---------------------------------------------------------------------------
# Layer 1 — Import / existence tests
# ---------------------------------------------------------------------------
class TestImports:
    """Verify that the expected public API exists in src.short_video.transcription."""

    def test_import_transcription_module(self):
        from src.short_video import transcription  # noqa: F401

    def test_import_transcription_service(self):
        from src.short_video.transcription import TranscriptionService  # noqa: F401

    def test_import_transcript_segment(self):
        from src.short_video.transcription import TranscriptSegment  # noqa: F401

    def test_import_word_timing(self):
        from src.short_video.transcription import WordTiming  # noqa: F401

    def test_import_transcription_result(self):
        from src.short_video.transcription import TranscriptionResult  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 2 — Interface / signature tests
# ---------------------------------------------------------------------------
class TestInterface:
    """Verify signatures and types for the P0-2 public API."""

    def test_transcript_segment_is_pydantic_model(self):
        from src.short_video.transcription import TranscriptSegment

        assert hasattr(TranscriptSegment, "model_fields")

    def test_transcript_segment_fields(self):
        from src.short_video.transcription import TranscriptSegment

        fields = TranscriptSegment.model_fields
        assert "start" in fields
        assert "end" in fields
        assert "text" in fields
        assert "words" in fields

    def test_word_timing_is_pydantic_model(self):
        from src.short_video.transcription import WordTiming

        assert hasattr(WordTiming, "model_fields")

    def test_word_timing_fields(self):
        from src.short_video.transcription import WordTiming

        fields = WordTiming.model_fields
        assert "word" in fields
        assert "start" in fields
        assert "end" in fields
        assert "probability" in fields

    def test_transcription_result_is_pydantic_model(self):
        from src.short_video.transcription import TranscriptionResult

        assert hasattr(TranscriptionResult, "model_fields")

    def test_transcription_result_fields(self):
        from src.short_video.transcription import TranscriptionResult

        fields = TranscriptionResult.model_fields
        assert "language" in fields
        assert "language_probability" in fields
        assert "duration" in fields
        assert "segments" in fields

    def test_transcription_service_init_signature(self):
        from src.short_video.transcription import TranscriptionService

        sig = inspect.signature(TranscriptionService.__init__)
        params = sig.parameters
        assert "model_size" in params
        assert "device" in params

    def test_transcription_service_model_size_default(self):
        from src.short_video.transcription import TranscriptionService

        sig = inspect.signature(TranscriptionService.__init__)
        assert sig.parameters["model_size"].default == "base"

    def test_transcription_service_device_default(self):
        from src.short_video.transcription import TranscriptionService

        sig = inspect.signature(TranscriptionService.__init__)
        assert sig.parameters["device"].default == "cpu"

    def test_transcription_service_has_transcribe(self):
        from src.short_video.transcription import TranscriptionService

        assert hasattr(TranscriptionService, "transcribe")
        assert callable(TranscriptionService.transcribe)

    def test_transcribe_is_coroutine(self):
        from src.short_video.transcription import TranscriptionService

        assert inspect.iscoroutinefunction(TranscriptionService.transcribe)

    def test_transcribe_signature(self):
        from src.short_video.transcription import TranscriptionService

        sig = inspect.signature(TranscriptionService.transcribe)
        assert "video_path" in sig.parameters

    def test_transcription_service_has_extract_audio(self):
        from src.short_video.transcription import TranscriptionService

        assert hasattr(TranscriptionService, "_extract_audio")
        assert callable(TranscriptionService._extract_audio)

    def test_extract_audio_signature(self):
        from src.short_video.transcription import TranscriptionService

        sig = inspect.signature(TranscriptionService._extract_audio)
        assert "video_path" in sig.parameters
        assert "output_path" in sig.parameters

    def test_transcription_service_has_load_model(self):
        from src.short_video.transcription import TranscriptionService

        assert hasattr(TranscriptionService, "_load_model")
        assert callable(TranscriptionService._load_model)


# ---------------------------------------------------------------------------
# Layer 3 — Behavioral / future tests
# ---------------------------------------------------------------------------
class TestBehavioral:
    """Behavioral expectations that will pass only after implementation."""

    def test_transcript_segment_model_construction(self):
        from src.short_video.transcription import TranscriptSegment

        seg = TranscriptSegment(start=0.0, end=2.5, text="Hello world")
        assert seg.start == 0.0
        assert seg.end == 2.5
        assert seg.text == "Hello world"
        assert seg.words == []

    def test_transcript_segment_with_words(self):
        from src.short_video.transcription import TranscriptSegment, WordTiming

        words = [WordTiming(word="hello", start=0.0, end=0.5)]
        seg = TranscriptSegment(start=0.0, end=1.0, text="hello", words=words)
        assert len(seg.words) == 1

    def test_word_timing_model_construction(self):
        from src.short_video.transcription import WordTiming

        wt = WordTiming(word="hello", start=0.0, end=0.5, probability=0.95)
        assert wt.probability == 0.95
        assert wt.word == "hello"

    def test_word_timing_default_probability(self):
        from src.short_video.transcription import WordTiming

        wt = WordTiming(word="test", start=0.0, end=0.5)
        assert wt.probability == 1.0

    def test_transcription_result_model_construction(self):
        from src.short_video.transcription import (
            TranscriptionResult,
            TranscriptSegment,
        )

        result = TranscriptionResult(
            language="en",
            language_probability=0.98,
            duration=120.0,
            segments=[TranscriptSegment(start=0, end=5, text="test")],
        )
        assert result.language == "en"
        assert len(result.segments) == 1
        assert result.duration == 120.0

    def test_transcription_service_init_attributes(self):
        from src.short_video.transcription import TranscriptionService

        svc = TranscriptionService(model_size="tiny", device="cpu")
        assert svc._model_size == "tiny"
        assert svc._device == "cpu"
        assert svc._model is None  # lazy-loaded

    def test_extract_audio_uses_pcm_codec(self):
        """Verify ffmpeg command uses pcm_s16le codec (no real execution)."""
        from src.short_video.transcription import TranscriptionService

        svc = TranscriptionService()
        source = inspect.getsource(svc._extract_audio)
        assert "pcm_s16le" in source
        assert "16000" in source  # sample rate

    def test_extract_audio_has_ffmpeg_call(self):
        """Verify _extract_audio uses ffmpeg."""
        from src.short_video.transcription import TranscriptionService

        svc = TranscriptionService()
        source = inspect.getsource(svc._extract_audio)
        # Should reference ffmpeg or imageio_ffmpeg
        assert "ffmpeg" in source.lower() or "imageio" in source.lower()
