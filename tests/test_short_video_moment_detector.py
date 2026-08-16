"""RED contract tests for short-video P0-3: Moment Detection.

All imports come from src.short_video.moment_detector which does not exist yet.
Every test MUST fail with ModuleNotFoundError (RED) until the developer implements the module.
"""

from __future__ import annotations

import inspect


# ---------------------------------------------------------------------------
# Layer 1 — Import / existence tests
# ---------------------------------------------------------------------------
class TestImports:
    """Verify that the expected public API exists in src.short_video.moment_detector."""

    def test_import_moment_detector_module(self):
        from src.short_video import moment_detector  # noqa: F401

    def test_import_moment_detector_class(self):
        from src.short_video.moment_detector import MomentDetector  # noqa: F401

    def test_import_moment_detection_config(self):
        from src.short_video.moment_detector import MomentDetectionConfig  # noqa: F401

    def test_import_detected_moment(self):
        from src.short_video.moment_detector import DetectedMoment  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 2 — Interface / signature tests
# ---------------------------------------------------------------------------
class TestInterface:
    """Verify signatures and types for the P0-3 public API."""

    def test_detected_moment_is_pydantic_model(self):
        from src.short_video.moment_detector import DetectedMoment

        assert hasattr(DetectedMoment, "model_fields")

    def test_detected_moment_fields(self):
        from src.short_video.moment_detector import DetectedMoment

        fields = DetectedMoment.model_fields
        assert "start_time" in fields
        assert "end_time" in fields
        assert "score" in fields
        assert "reason" in fields
        assert "title" in fields

    def test_moment_detection_config_is_pydantic_model(self):
        from src.short_video.moment_detector import MomentDetectionConfig

        assert hasattr(MomentDetectionConfig, "model_fields")

    def test_moment_detection_config_fields(self):
        from src.short_video.moment_detector import MomentDetectionConfig

        fields = MomentDetectionConfig.model_fields
        assert "min_clip_duration" in fields
        assert "max_clip_duration" in fields
        assert "target_clip_count" in fields
        assert "api_model" in fields
        assert "use_local_fallback" in fields

    def test_moment_detection_config_defaults(self):
        from src.short_video.moment_detector import MomentDetectionConfig

        cfg = MomentDetectionConfig()
        assert cfg.min_clip_duration == 15.0
        assert cfg.max_clip_duration == 60.0
        assert cfg.target_clip_count == 5
        assert cfg.api_model == "gemini-2.0-flash"
        assert cfg.use_local_fallback is False

    def test_moment_detector_init_signature(self):
        from src.short_video.moment_detector import MomentDetector

        sig = inspect.signature(MomentDetector.__init__)
        assert "config" in sig.parameters

    def test_moment_detector_has_detect_moments(self):
        from src.short_video.moment_detector import MomentDetector

        assert hasattr(MomentDetector, "detect_moments")
        assert callable(MomentDetector.detect_moments)

    def test_detect_moments_is_coroutine(self):
        from src.short_video.moment_detector import MomentDetector

        assert inspect.iscoroutinefunction(MomentDetector.detect_moments)

    def test_detect_moments_signature(self):
        from src.short_video.moment_detector import MomentDetector

        sig = inspect.signature(MomentDetector.detect_moments)
        assert "transcript" in sig.parameters
        assert "video_duration" in sig.parameters

    def test_moment_detector_has_build_prompt(self):
        from src.short_video.moment_detector import MomentDetector

        assert hasattr(MomentDetector, "_build_detection_prompt")
        assert callable(MomentDetector._build_detection_prompt)

    def test_build_prompt_signature(self):
        from src.short_video.moment_detector import MomentDetector

        sig = inspect.signature(MomentDetector._build_detection_prompt)
        assert "transcript" in sig.parameters
        assert "video_duration" in sig.parameters

    def test_moment_detector_has_parse_response(self):
        from src.short_video.moment_detector import MomentDetector

        assert hasattr(MomentDetector, "_parse_gemini_response")
        assert callable(MomentDetector._parse_gemini_response)

    def test_parse_response_signature(self):
        from src.short_video.moment_detector import MomentDetector

        sig = inspect.signature(MomentDetector._parse_gemini_response)
        assert "response_text" in sig.parameters

    def test_moment_detector_has_validate_clips(self):
        from src.short_video.moment_detector import MomentDetector

        assert hasattr(MomentDetector, "_validate_clips")
        assert callable(MomentDetector._validate_clips)

    def test_validate_clips_signature(self):
        from src.short_video.moment_detector import MomentDetector

        sig = inspect.signature(MomentDetector._validate_clips)
        assert "moments" in sig.parameters


# ---------------------------------------------------------------------------
# Layer 3 — Behavioral / future tests
# ---------------------------------------------------------------------------
class TestBehavioral:
    """Behavioral expectations that will pass only after implementation."""

    def test_detected_moment_construction(self):
        from src.short_video.moment_detector import DetectedMoment

        m = DetectedMoment(start_time=10.0, end_time=35.0, score=0.85, reason="Hook")
        assert m.start_time == 10.0
        assert m.end_time == 35.0
        assert m.score == 0.85
        assert m.title is None  # optional

    def test_detected_moment_with_title(self):
        from src.short_video.moment_detector import DetectedMoment

        m = DetectedMoment(
            start_time=0, end_time=30, score=0.9, reason="Insight", title="Big Idea"
        )
        assert m.title == "Big Idea"

    def test_build_detection_prompt_includes_transcript(self):
        """Prompt should include transcript text and video duration."""
        from src.short_video.moment_detector import MomentDetector
        from src.short_video.transcription import TranscriptionResult, TranscriptSegment

        detector = MomentDetector()
        transcript = TranscriptionResult(
            language="en",
            language_probability=0.99,
            duration=300.0,
            segments=[
                TranscriptSegment(start=0, end=10, text="Welcome to the show"),
                TranscriptSegment(start=10, end=25, text="Today we discuss AI"),
                TranscriptSegment(start=25, end=45, text="The key insight is..."),
            ],
        )
        prompt = detector._build_detection_prompt(transcript, 300.0)
        assert "300" in prompt or "5:00" in prompt  # duration mentioned
        assert "Welcome" in prompt  # transcript text included
        assert "15" in prompt or "minimum" in prompt.lower()  # duration constraint

    def test_parse_gemini_response_valid(self):
        from src.short_video.moment_detector import MomentDetector

        detector = MomentDetector()
        response = (
            '[{"start_time": 10.0, "end_time": 35.0, "score": 0.85, '
            '"reason": "Strong opening hook"}, '
            '{"start_time": 60.0, "end_time": 90.0, "score": 0.72, '
            '"reason": "Key insight moment"}]'
        )
        moments = detector._parse_gemini_response(response)
        assert len(moments) == 2
        assert moments[0].score >= moments[1].score  # sorted by score

    def test_parse_gemini_response_malformed(self):
        from src.short_video.moment_detector import MomentDetector

        detector = MomentDetector()
        moments = detector._parse_gemini_response("not json at all")
        assert moments == []  # graceful fallback

    def test_validate_clips_respects_bounds(self):
        from src.short_video.moment_detector import (
            DetectedMoment,
            MomentDetectionConfig,
            MomentDetector,
        )

        detector = MomentDetector(
            config=MomentDetectionConfig(
                min_clip_duration=10.0, max_clip_duration=30.0
            )
        )
        moments = [
            DetectedMoment(start_time=0, end_time=5, score=0.9, reason="too short"),
            DetectedMoment(start_time=0, end_time=20, score=0.8, reason="ok"),
            DetectedMoment(
                start_time=0, end_time=120, score=0.7, reason="too long"
            ),
        ]
        validated = detector._validate_clips(moments)
        # Only the middle clip should survive bounds check
        assert all(
            10.0 <= (m.end_time - m.start_time) <= 30.0 for m in validated
        )

    def test_moment_detector_stores_config(self):
        from src.short_video.moment_detector import (
            MomentDetectionConfig,
            MomentDetector,
        )

        cfg = MomentDetectionConfig(target_clip_count=10)
        detector = MomentDetector(config=cfg)
        assert detector._config.target_clip_count == 10

    def test_moment_detector_default_config(self):
        from src.short_video.moment_detector import MomentDetector

        detector = MomentDetector()
        assert detector._config is not None
        assert detector._config.min_clip_duration == 15.0
