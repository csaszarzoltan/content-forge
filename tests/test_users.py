"""Interface and behavioral tests for the User ORM model.

Interface tests  — verify imports, model columns, tablename (should PASS).
Behavioral tests — verify User model instantiation and defaults.
"""

from __future__ import annotations

import uuid

from src.models.user import User

import pytest

# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

# ============================================================================
# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestUserModelInterface:
    """Verify the User ORM model interface."""

    def test_user_importable(self):
        assert User is not None

    def test_user_is_sqlalchemy_model(self):
        assert hasattr(User, "__tablename__")
        assert hasattr(User, "__table__")

    def test_user_tablename(self):
        assert User.__tablename__ == "users"

    def test_user_columns(self):
        cols = {c.name for c in User.__table__.columns}
        assert "id" in cols
        assert "email" in cols
        assert "password_hash" in cols
        assert "display_name" in cols
        assert "is_active" in cols
        assert "role" in cols
        assert "organization_id" in cols
        assert "refresh_token_hash" in cols
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_user_email_unique_indexed(self):
        """Email column should have unique constraint and index."""
        email_col = User.__table__.columns["email"]
        assert email_col.unique is True
        assert email_col.nullable is False
        assert email_col.index is True

    def test_user_password_hash_not_nullable(self):
        pwhash = User.__table__.columns["password_hash"]
        assert pwhash.nullable is False

    def test_user_role_has_default(self):
        role = User.__table__.columns["role"]
        assert role.default is not None

    def test_user_is_active_has_default(self):
        is_active = User.__table__.columns["is_active"]
        assert is_active.default is not None

    def test_user_created_at_has_server_default(self):
        created = User.__table__.columns["created_at"]
        assert created.server_default is not None

    def test_user_model_exported_from_models_package(self):
        from src import models
        assert hasattr(models, "User")
        assert models.User is User

    def test_user_id_column_is_primary_key(self):
        id_col = User.__table__.columns["id"]
        assert id_col.primary_key is True
        assert isinstance(id_col.type.length, int)
        assert id_col.type.length == 36  # UUID string length


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real model behavior)
# ============================================================================


class TestUserModelBehavioral:
    """Behavioral tests for the User model — instantiation and defaults."""

    def test_user_can_be_instantiated_with_required_fields(self):
        """A User instance can be created with explicit required fields."""
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        uid = str(uuid.uuid4())
        u = User(
            id=uid,
            email="user@example.com",
            password_hash="hashed_pw_placeholder",
            display_name="Test User",
            is_active=True,
            role="user",
        )
        assert u.id == uid
        assert u.email == "user@example.com"
        assert u.password_hash == "hashed_pw_placeholder"
        assert u.display_name == "Test User"
        assert u.is_active is True
        assert u.role == "user"

    def test_user_organization_id_defaults_to_none(self):
        """organization_id should be None when not provided."""
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        u = User(
            id=str(uuid.uuid4()),
            email="org-test@example.com",
            password_hash="hash",
            display_name="Org Test",
        )
        assert u.organization_id is None

    def test_user_refresh_token_hash_defaults_to_none(self):
        """refresh_token_hash should be None when not provided."""
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        u = User(
            id=str(uuid.uuid4()),
            email="refresh-test@example.com",
            password_hash="hash",
            display_name="Refresh Test",
        )
        assert u.refresh_token_hash is None

    def test_user_timestamps_are_datetime_columns(self):
        """created_at and updated_at should be DateTime columns."""
        created = User.__table__.columns["created_at"]
        updated = User.__table__.columns["updated_at"]
        from sqlalchemy import DateTime

        assert isinstance(created.type, DateTime)
        assert isinstance(updated.type, DateTime)
