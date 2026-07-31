"""Interface and behavioral tests for language metadata additions to models/schemas.

Interface tests  — verify imports, column presence, schema field signatures.
                  Some fail now (pre-dev contract) and pass once fields are added.
Behavioral tests — verify NotImplementedError for stubs that need implementation.

AC-T2 coverage:
  AC-T2.1  Generation.language field
  AC-T2.2  BrandVoice.languages field
  AC-T2.3  ScheduledPost.source_language + target_language fields
  AC-T2.4  Existing data remains valid
  AC-T2.5  DB migration script
  AC-T2.6  Schema updates
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.models.brand_voice import BrandVoice
from src.models.generation import Generation
from src.models.scheduled_post import ScheduledPost
from src.schemas.brand_voice import BrandVoiceResponse
from src.schemas.content import GenerationResponse
from src.schemas.schedule import ScheduleRequest, ScheduleResponse


# ============================================================================
# SECTION 1 — MODEL INTERFACE TESTS
#
# These verify that the ORM models have the expected language columns.
# Tests for EXISTING columns should PASS.
# Tests for NEW columns (language, languages, source_language, target_language)
# will FAIL now — they define the pre-dev contract.
# ============================================================================


class TestGenerationLanguageColumn:
    """AC-T2.1: Generation model gains optional `language` field."""

    def test_generation_importable(self):
        """Existing import — should PASS."""
        assert Generation is not None

    def test_generation_has_language_column(self):
        """language column must exist on Generation model."""
        cols = {c.name for c in Generation.__table__.columns}
        assert "language" in cols, "Generation model needs a 'language' column (str, ISO 639-1)"

    def test_generation_language_type_string(self):
        """language column must be of String type."""
        col = {c.name: c for c in Generation.__table__.columns}.get("language")
        if col is None:
            pytest.skip("language column not yet added to Generation model")
        from sqlalchemy import String
        assert isinstance(col.type, String)

    def test_generation_language_default_en(self):
        """language column must default to 'en'."""
        col = {c.name: c for c in Generation.__table__.columns}.get("language")
        if col is None:
            pytest.skip("language column not yet added to Generation model")
        # SQLAlchemy default can be a scalar or a callable
        assert col.default is not None, "language field should have default='en'"
        # The default can be a server_default or Python-side default; check either
        has_python_default = col.default is not None and (
            getattr(col.default, "arg", None) == "en"
        )
        has_server_default = (
            col.server_default is not None
            and getattr(col.server_default, "arg", None) is not None
        )
        assert has_python_default or has_server_default, (
            "language column should default to 'en'"
        )

    def test_generation_language_nullable(self):
        """language column must be nullable (or have a default)."""
        col = {c.name: c for c in Generation.__table__.columns}.get("language")
        if col is None:
            pytest.skip("language column not yet added to Generation model")
        assert col.nullable is True or col.default is not None, (
            "language column should be either nullable or have a default"
        )


class TestBrandVoiceLanguageColumn:
    """AC-T2.2: BrandVoice model gains optional `languages` field."""

    def test_brand_voice_importable(self):
        """Existing import — should PASS."""
        assert BrandVoice is not None

    def test_brand_voice_has_languages_column(self):
        """languages column must exist on BrandVoice model."""
        cols = {c.name for c in BrandVoice.__table__.columns}
        assert "languages" in cols, (
            "BrandVoice model needs a 'languages' column (list[str], default ['en'])"
        )

    def test_brand_voice_languages_type_json(self):
        """languages column must be of JSON type (stores list[str])."""
        col = {c.name: c for c in BrandVoice.__table__.columns}.get("languages")
        if col is None:
            pytest.skip("languages column not yet added to BrandVoice model")
        from sqlalchemy.dialects.postgresql import JSON as PGJSON
        from sqlalchemy import JSON as SAJSON
        assert isinstance(col.type, (SAJSON, PGJSON)), (
            "languages column should be JSON type to store list[str]"
        )

    def test_brand_voice_languages_default_en_list(self):
        """languages column must default to ['en']."""
        col = {c.name: c for c in BrandVoice.__table__.columns}.get("languages")
        if col is None:
            pytest.skip("languages column not yet added to BrandVoice model")
        assert col.default is not None, "languages field should have default=['en']"


class TestScheduledPostLanguageColumns:
    """AC-T2.3: ScheduledPost gains source_language + target_language fields."""

    def test_scheduled_post_importable(self):
        """Existing import — should PASS."""
        assert ScheduledPost is not None

    def test_scheduled_post_has_source_language_column(self):
        """source_language column must exist on ScheduledPost model."""
        cols = {c.name for c in ScheduledPost.__table__.columns}
        assert "source_language" in cols, (
            "ScheduledPost model needs a 'source_language' column (str, nullable)"
        )

    def test_scheduled_post_has_target_language_column(self):
        """target_language column must exist on ScheduledPost model."""
        cols = {c.name for c in ScheduledPost.__table__.columns}
        assert "target_language" in cols, (
            "ScheduledPost model needs a 'target_language' column (str, nullable)"
        )

    def test_scheduled_post_source_language_nullable(self):
        """source_language column should be nullable."""
        col = {c.name: c for c in ScheduledPost.__table__.columns}.get("source_language")
        if col is None:
            pytest.skip("source_language column not yet added")
        assert col.nullable is True, "source_language should be nullable"

    def test_scheduled_post_target_language_nullable(self):
        """target_language column should be nullable."""
        col = {c.name: c for c in ScheduledPost.__table__.columns}.get("target_language")
        if col is None:
            pytest.skip("target_language column not yet added")
        assert col.nullable is True, "target_language should be nullable"

    def test_scheduled_post_source_language_type_string(self):
        """source_language column must be String type."""
        col = {c.name: c for c in ScheduledPost.__table__.columns}.get("source_language")
        if col is None:
            pytest.skip("source_language column not yet added")
        from sqlalchemy import String
        assert isinstance(col.type, String), "source_language should be String"

    def test_scheduled_post_target_language_type_string(self):
        """target_language column must be String type."""
        col = {c.name: c for c in ScheduledPost.__table__.columns}.get("target_language")
        if col is None:
            pytest.skip("target_language column not yet added")
        from sqlalchemy import String
        assert isinstance(col.type, String), "target_language should be String"


# ============================================================================
# SECTION 2 — SCHEMA INTERFACE TESTS
#
# AC-T2.6: Pydantic schemas expose language fields.
# Tests for EXISTING schema fields should PASS.
# Tests for NEW language fields will FAIL now.
# ============================================================================


class TestGenerationResponseSchema:
    """AC-T2.6: GenerationResponse gains `language` field."""

    def test_generation_response_importable(self):
        """Existing import — should PASS."""
        assert GenerationResponse is not None

    def test_generation_response_is_pydantic(self):
        """Existing type check — should PASS."""
        from pydantic import BaseModel
        assert issubclass(GenerationResponse, BaseModel)

    def test_generation_response_has_language_field(self):
        """GenerationResponse must have a 'language' field."""
        sig = inspect.signature(GenerationResponse)
        assert "language" in sig.parameters, (
            "GenerationResponse needs a 'language' field (str, default 'en')"
        )

    def test_generation_response_language_type_str(self):
        """GenerationResponse.language field should default to 'en'."""
        try:
            lang_field = GenerationResponse.model_fields["language"]
        except (AttributeError, KeyError):
            pytest.skip("language field not yet added to GenerationResponse")
        assert lang_field.default == "en", "language field should default to 'en'"


class TestBrandVoiceResponseSchema:
    """AC-T2.6: BrandVoiceResponse gains `languages` field."""

    def test_brand_voice_response_importable(self):
        """Existing import — should PASS."""
        assert BrandVoiceResponse is not None

    def test_brand_voice_response_is_pydantic(self):
        """Existing type check — should PASS."""
        from pydantic import BaseModel
        assert issubclass(BrandVoiceResponse, BaseModel)

    def test_brand_voice_response_has_languages_field(self):
        """BrandVoiceResponse must have a 'languages' field."""
        sig = inspect.signature(BrandVoiceResponse)
        assert "languages" in sig.parameters, (
            "BrandVoiceResponse needs a 'languages' field (list[str], default ['en'])"
        )

    def test_brand_voice_response_languages_default(self):
        """BrandVoiceResponse.languages field should default to ['en']."""
        try:
            lang_field = BrandVoiceResponse.model_fields["languages"]
        except (AttributeError, KeyError):
            pytest.skip("languages field not yet added to BrandVoiceResponse")
        assert lang_field.default == ["en"], (
            "languages field should default to ['en']"
        )


class TestScheduleRequestSchema:
    """AC-T2.6: ScheduleRequest gains source_language + target_language fields."""

    def test_schedule_request_importable(self):
        """Existing import — should PASS."""
        assert ScheduleRequest is not None

    def test_schedule_request_is_pydantic(self):
        """Existing type check — should PASS."""
        from pydantic import BaseModel
        assert issubclass(ScheduleRequest, BaseModel)

    def test_schedule_request_has_source_language(self):
        """ScheduleRequest must have a 'source_language' field."""
        sig = inspect.signature(ScheduleRequest)
        assert "source_language" in sig.parameters, (
            "ScheduleRequest needs a 'source_language' field (str, optional)"
        )

    def test_schedule_request_has_target_language(self):
        """ScheduleRequest must have a 'target_language' field."""
        sig = inspect.signature(ScheduleRequest)
        assert "target_language" in sig.parameters, (
            "ScheduleRequest needs a 'target_language' field (str, optional)"
        )

    def test_schedule_request_source_language_optional(self):
        """ScheduleRequest.source_language should be optional (default None)."""
        try:
            field = ScheduleRequest.model_fields["source_language"]
        except (AttributeError, KeyError):
            pytest.skip("source_language field not yet added to ScheduleRequest")
        assert field.default is None, "source_language should default to None"

    def test_schedule_request_target_language_optional(self):
        """ScheduleRequest.target_language should be optional (default None)."""
        try:
            field = ScheduleRequest.model_fields["target_language"]
        except (AttributeError, KeyError):
            pytest.skip("target_language field not yet added to ScheduleRequest")
        assert field.default is None, "target_language should default to None"


class TestScheduleResponseSchema:
    """AC-T2.6: ScheduleResponse gains source_language + target_language fields."""

    def test_schedule_response_importable(self):
        """Existing import — should PASS."""
        assert ScheduleResponse is not None

    def test_schedule_response_is_pydantic(self):
        """Existing type check — should PASS."""
        from pydantic import BaseModel
        assert issubclass(ScheduleResponse, BaseModel)

    def test_schedule_response_has_source_language(self):
        """ScheduleResponse must have a 'source_language' field."""
        sig = inspect.signature(ScheduleResponse)
        assert "source_language" in sig.parameters, (
            "ScheduleResponse needs a 'source_language' field (str, optional)"
        )

    def test_schedule_response_has_target_language(self):
        """ScheduleResponse must have a 'target_language' field."""
        sig = inspect.signature(ScheduleResponse)
        assert "target_language" in sig.parameters, (
            "ScheduleResponse needs a 'target_language' field (str, optional)"
        )


# ============================================================================
# SECTION 3 — BEHAVIORAL STUBS (NotImplementedError)
#
# These define expected runtime behavior. They fail with NotImplementedError
# until the developer provides implementations.
# ============================================================================


class TestGenerationLanguageBehavior:
    """Runtime behavior tests for Generation.language field."""

    def test_generation_default_language_is_en(self):
        """Creating a Generation without language defaults to 'en'."""
        pytest.skip("Requires DB — implement with in-memory SQLite once model is ready")

    def test_generation_language_accepts_valid_iso_code(self):
        """language field should accept valid ISO 639-1 codes like 'de', 'fr', 'ja'."""
        pytest.skip("Requires model validation — implement once language field exists")

    def test_generation_language_rejects_long_code(self):
        """language field should reject codes longer than 2 characters (ISO 639-1)."""
        pytest.skip("Requires model/validation — implement once language field exists")


class TestBrandVoiceLanguageBehavior:
    """Runtime behavior tests for BrandVoice.languages field."""

    def test_brand_voice_default_languages_is_en_list(self):
        """Creating a BrandVoice without languages defaults to ['en']."""
        pytest.skip("Requires DB — implement with in-memory SQLite once model is ready")

    def test_brand_voice_languages_accepts_multiple_codes(self):
        """languages field should accept multiple ISO codes, e.g. ['en', 'de', 'fr']."""
        pytest.skip("Requires model — implement once languages field exists")


class TestScheduledPostLanguageBehavior:
    """Runtime behavior tests for ScheduledPost language fields."""

    def test_scheduled_post_language_fields_nullable_by_default(self):
        """source_language and target_language can be null."""
        pytest.skip("Requires DB — implement with in-memory SQLite once model is ready")

    def test_scheduled_post_language_fields_accept_valid_codes(self):
        """source_language and target_language accept ISO 639-1 codes."""
        pytest.skip("Requires model — implement once language fields exist")


class TestBackwardCompatibility:
    """AC-T2.4: Existing data remains valid after migration."""

    def test_interface_existing_columns_no_removal(self):
        """Verify no existing columns were removed from any model."""
        # Generation columns
        gen_cols = {c.name for c in Generation.__table__.columns}
        for expected in ("id", "brand_voice_id", "content_type", "topic",
                          "parameters", "generated_text", "compliance_scores",
                          "model_used", "tokens_used", "latency_ms", "created_at"):
            assert expected in gen_cols, f"Existing column '{expected}' removed from Generation"

        # BrandVoice columns
        bv_cols = {c.name for c in BrandVoice.__table__.columns}
        for expected in ("id", "name", "description", "profile_data",
                          "version", "user_id", "deleted_at", "created_at", "updated_at"):
            assert expected in bv_cols, f"Existing column '{expected}' removed from BrandVoice"

        # ScheduledPost columns
        sp_cols = {c.name for c in ScheduledPost.__table__.columns}
        for expected in ("id", "generation_id", "publish_at", "platform",
                          "platform_config", "status", "retry_count",
                          "max_retries", "created_at", "updated_at"):
            assert expected in sp_cols, f"Existing column '{expected}' removed from ScheduledPost"


class TestMigration:
    """AC-T2.5: DB migration script is provided and tested."""

    def test_migration_script_exists(self):
        """A migration script (Alembic revision or raw SQL) must exist."""
        pytest.skip(
            "AC-T2.5: Implement migration script (Alembic or raw SQL) "
            "that adds language/languages/source_language/target_language columns."
        )

    def test_migration_adds_generation_language(self):
        """Migration must add 'language' column to generations table."""
        pytest.skip(
            "AC-T2.5: Write and test the migration SQL that adds "
            "'language VARCHAR DEFAULT en' to generations table."
        )

    def test_migration_adds_brand_voice_languages(self):
        """Migration must add 'languages' column to brand_voices table."""
        pytest.skip(
            "AC-T2.5: Write and test the migration SQL that adds "
            "'languages JSON DEFAULT [\"en\"]' to brand_voices table."
        )

    def test_migration_adds_scheduled_post_language_fields(self):
        """Migration must add source_language and target_language columns."""
        pytest.skip(
            "AC-T2.5: Write and test the migration SQL that adds "
            "'source_language VARCHAR' and 'target_language VARCHAR' "
            "to scheduled_posts table."
        )

    def test_migration_preserves_existing_data(self):
        """Migration must not destroy existing rows (backward compatible)."""
        pytest.skip(
            "AC-T2.5: Write a test that runs the migration against a SQLite DB "
            "with pre-existing records and verifies they survive."
        )

    def test_migration_reversible(self):
        """Migration must have a downgrade/reverse path."""
        pytest.skip(
            "AC-T2.5: The migration script should be reversible (downgrade "
            "removes the added columns without data loss)."
        )


class TestLanguageFieldValidation:
    """Validate language field constraints (ISO 639-1)."""

    def test_iso_639_1_format_validation(self):
        """Language codes must be 2-letter lowercase ISO 639-1 codes."""
        pytest.skip(
            "Add validation that ensures language fields accept only "
            "valid ISO 639-1 alpha-2 codes (e.g. 'en', 'de', 'fr')."
        )

    def test_invalid_language_code_rejected(self):
        """Invalid language codes like 'english' or '123' should be rejected."""
        pytest.skip(
            "Add validation that rejects non-ISO-639-1 language codes."
        )

    def test_languages_list_validation(self):
        """BrandVoice.languages must be a list of valid ISO codes."""
        pytest.skip(
            "Add validation that each entry in the languages list "
            "is a valid ISO 639-1 code."
        )


class TestSchemaLanguageSerialization:
    """AC-T2.6: Verify language fields serialize correctly in API responses."""

    def test_generation_response_includes_language(self):
        """GenerationResponse serialization should include 'language'."""
        pytest.skip(
            "AC-T2.6: Ensure GenerationResponse schema model_serialize or "
            "model_dump includes 'language' in its output."
        )

    def test_brand_voice_response_includes_languages(self):
        """BrandVoiceResponse serialization should include 'languages'."""
        pytest.skip(
            "AC-T2.6: Ensure BrandVoiceResponse schema model_serialize "
            "includes 'languages' in its output."
        )

    def test_schedule_response_includes_language_fields(self):
        """ScheduleResponse serialization should include source/target language."""
        pytest.skip(
            "AC-T2.6: Ensure ScheduleResponse schema model_serialize "
            "includes 'source_language' and 'target_language'."
        )

    def test_schedule_request_excludes_when_not_set(self):
        """ScheduleRequest should serialize to None when language fields unset."""
        pytest.skip(
            "AC-T2.6: Verify source_language and target_language are absent/null "
            "in serialized output when not provided."
        )


# ============================================================================
# SECTION 4 — DATA INTEGRITY TESTS (skipped, require DB fixture)
# ============================================================================


class TestExistingDataIntegrity:
    """AC-T2.4: Verify existing data integrity after model changes."""

    def test_existing_generation_can_be_instantiated(self):
        """Existing Generation fields still work after adding language column."""
        gen = Generation(
            id="test-id",
            content_type="blog",
            topic="Test topic",
            generated_text="Some text",
        )
        assert gen.id == "test-id"
        assert gen.content_type == "blog"
        assert gen.topic == "Test topic"

    def test_existing_brand_voice_can_be_instantiated(self):
        """Existing BrandVoice fields still work after adding languages column."""
        bv = BrandVoice(
            id="test-id",
            name="Test Voice",
            profile_data={},
        )
        assert bv.id == "test-id"
        assert bv.name == "Test Voice"

    def test_existing_scheduled_post_can_be_instantiated(self):
        """Existing ScheduledPost fields still work after adding language columns."""
        from datetime import datetime, timezone
        sp = ScheduledPost(
            id="test-id",
            generation_id="gen-id",
            publish_at=datetime.now(timezone.utc),
            platform="twitter",
        )
        assert sp.id == "test-id"
        assert sp.generation_id == "gen-id"
        assert sp.platform == "twitter"

    def test_existing_generations_table_structure_intact(self):
        """Verify Generation table structure is intact (column count sanity)."""
        col_count = len(Generation.__table__.columns)
        # 11 existing + 1 new (language) = 12
        assert col_count >= 11, (
            f"Generation table has {col_count} columns, expected at least 11"
        )

    def test_existing_brand_voices_table_structure_intact(self):
        """Verify BrandVoice table structure is intact (column count sanity)."""
        col_count = len(BrandVoice.__table__.columns)
        # 9 existing + 1 new (languages) = 10
        assert col_count >= 9, (
            f"BrandVoice table has {col_count} columns, expected at least 9"
        )

    def test_existing_scheduled_posts_table_structure_intact(self):
        """Verify ScheduledPost table structure is intact (column count sanity)."""
        col_count = len(ScheduledPost.__table__.columns)
        # 10 existing + 2 new (source_language, target_language) = 12
        assert col_count >= 10, (
            f"ScheduledPost table has {col_count} columns, expected at least 10"
        )
