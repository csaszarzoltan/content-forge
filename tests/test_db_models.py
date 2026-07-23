"""Interface and behavioral tests for SQLAlchemy ORM models.

Interface tests  — verify imports, class signatures, fields (should PASS).
Behavioral tests — verify NotImplementedError for stub methods.
"""

from __future__ import annotations

import inspect

import pytest

from src.models.brand_voice import BrandVoice
from src.models.generation import Generation
from src.models.scheduled_post import ScheduledPost
from src.models.analytics import ContentAnalytics


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestBrandVoiceModelInterface:
    """Verify the BrandVoice ORM model interface."""

    def test_brand_voice_importable(self):
        assert BrandVoice is not None

    def test_brand_voice_is_sqlalchemy_model(self):
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(BrandVoice, DeclarativeBase) or hasattr(BrandVoice, "__tablename__")

    def test_brand_voice_tablename(self):
        assert BrandVoice.__tablename__ == "brand_voices"

    def test_brand_voice_columns(self):
        cols = {c.name for c in BrandVoice.__table__.columns}
        assert "id" in cols
        assert "name" in cols
        assert "description" in cols
        assert "profile_data" in cols
        assert "version" in cols
        assert "user_id" in cols
        assert "deleted_at" in cols
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_brand_voice_has_soft_delete(self):
        assert hasattr(BrandVoice, "soft_delete")
        assert callable(BrandVoice.soft_delete)

    def test_brand_voice_has_increment_version(self):
        assert hasattr(BrandVoice, "increment_version")
        assert callable(BrandVoice.increment_version)


class TestGenerationModelInterface:
    """Verify the Generation ORM model interface."""

    def test_generation_importable(self):
        assert Generation is not None

    def test_generation_tablename(self):
        assert Generation.__tablename__ == "generations"

    def test_generation_columns(self):
        cols = {c.name for c in Generation.__table__.columns}
        assert "id" in cols
        assert "brand_voice_id" in cols
        assert "content_type" in cols
        assert "topic" in cols
        assert "parameters" in cols
        assert "generated_text" in cols
        assert "compliance_scores" in cols
        assert "model_used" in cols
        assert "tokens_used" in cols
        assert "latency_ms" in cols
        assert "created_at" in cols


class TestScheduledPostModelInterface:
    """Verify the ScheduledPost ORM model interface."""

    def test_scheduled_post_importable(self):
        assert ScheduledPost is not None

    def test_scheduled_post_tablename(self):
        assert ScheduledPost.__tablename__ == "scheduled_posts"

    def test_scheduled_post_columns(self):
        cols = {c.name for c in ScheduledPost.__table__.columns}
        assert "id" in cols
        assert "generation_id" in cols
        assert "publish_at" in cols
        assert "platform" in cols
        assert "platform_config" in cols
        assert "status" in cols
        assert "retry_count" in cols
        assert "max_retries" in cols
        assert "created_at" in cols
        assert "updated_at" in cols


class TestContentAnalyticsModelInterface:
    """Verify the ContentAnalytics ORM model interface."""

    def test_content_analytics_importable(self):
        assert ContentAnalytics is not None

    def test_content_analytics_tablename(self):
        assert ContentAnalytics.__tablename__ == "content_analytics"

    def test_content_analytics_columns(self):
        cols = {c.name for c in ContentAnalytics.__table__.columns}
        assert "id" in cols
        assert "generation_id" in cols
        assert "views" in cols
        assert "engagement_rate" in cols
        assert "shares" in cols
        assert "comments" in cols
        assert "avg_read_time_seconds" in cols
        assert "compliance_overall" in cols
        assert "compliance_vocabulary" in cols
        assert "compliance_readability" in cols
        assert "compliance_tone" in cols
        assert "violations" in cols
        assert "last_synced_at" in cols


class TestModelsPackage:
    """Verify the models package can be imported and has expected exports."""

    def test_models_init_importable(self):
        from src import models
        assert models is not None


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestBrandVoiceModelBehavioral:
    """Behavioral tests for BrandVoice — verify real implementation."""

    def test_brand_voice_soft_delete_works(self):
        """soft_delete() should set deleted_at timestamp."""
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        bv = BrandVoice(id="test", name="Test", profile_data={})
        assert bv.deleted_at is None
        bv.soft_delete()
        assert bv.deleted_at is not None

    def test_brand_voice_increment_version_works(self):
        """increment_version() should bump version number."""
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        bv = BrandVoice(id="test", name="Test", profile_data={}, version=1)
        assert bv.version == 1
        bv.increment_version()
        assert bv.version == 2
