"""Migration v003 — Add language columns for multi-language support.

Revision ID: v003
Revises: v002
Create Date: 2026-07-25

Adds:
  - generations.language column (VARCHAR(10), default 'en')
  - brand_voices.languages column (JSON, default '["en"]')
  - scheduled_posts.source_language column (VARCHAR(10), nullable)
  - scheduled_posts.target_language column (VARCHAR(10), nullable)

Reverse: Removes the added columns.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import JSON

# Revision identifiers
revision: str = "v003"
down_revision: str | None = "v002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(op):
    """Apply the migration."""
    # generations.language
    op.add_column(
        "generations",
        op.Column("language", Text, server_default=text("'en'"), nullable=False),
    )

    # brand_voices.languages
    op.add_column(
        "brand_voices",
        op.Column("languages", JSON, server_default=text("'[\"en\"]'"), nullable=True),
    )

    # scheduled_posts.source_language
    op.add_column(
        "scheduled_posts",
        op.Column("source_language", Text, nullable=True),
    )

    # scheduled_posts.target_language
    op.add_column(
        "scheduled_posts",
        op.Column("target_language", Text, nullable=True),
    )


def downgrade(op):
    """Reverse the migration."""
    op.drop_column("generations", "language")
    op.drop_column("brand_voices", "languages")
    op.drop_column("scheduled_posts", "source_language")
    op.drop_column("scheduled_posts", "target_language")
