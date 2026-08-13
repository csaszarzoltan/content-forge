"""Pydantic schemas for the content-creation pipeline module.

Covers US-001..US-004 acceptance criteria from analysis-brief.md
(t_ef548473) — the "turn one source asset into a consistent
cross-platform content package" workflow:

  US-001  Create a cross-platform content package (source → variants → publish)
  US-002  Validate and correct inputs before running
  US-003  Recover safely from interrupted/external-dependency failures
  US-004  Review history, status, and outcomes (audit trail)

API contract (canonical repo v1 convention, brief §6):
  POST /api/v1/content-packages                      → 201 {id, state, platforms, created_at}
  GET  /api/v1/content-packages/{id}                 → ContentPackageResponse
  POST /api/v1/content-packages/{id}/generate        → {state, variant_count}
  POST /api/v1/content-packages/{id}/validate        → {state, variants}
  POST /api/v1/content-packages/{id}/approve         → {state}
  POST /api/v1/content-packages/{id}/publish         → {state, deliveries}
  GET  /api/v1/content-packages/{id}/history         → {events}
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ───────────────────────────────────────────────────────────────────


class ContentPackageState(str, Enum):
    """Package state machine: draft → generating → validating → ready_to_approve → approved → publishing → published | failed."""

    draft = "draft"
    generating = "generating"
    validating = "validating"
    ready_to_approve = "ready_to_approve"
    approved = "approved"
    publishing = "publishing"
    published = "published"
    failed = "failed"


class ContentVariantState(str, Enum):
    """Per-variant sub-state: pending → generated → validated → published | failed."""

    pending = "pending"
    generated = "generated"
    validated = "validated"
    published = "published"
    failed = "failed"


class ContentSourceType(str, Enum):
    """Accepted package source types."""

    generation_id = "generation_id"
    text = "text"
    url = "url"


# ── Request / response models ───────────────────────────────────────────────


class ContentPackageCreate(BaseModel):
    """POST /api/v1/content-packages request body (P0-2, brief §6)."""

    source_type: ContentSourceType
    source_ref: str = Field(..., min_length=1, max_length=200_000)
    platforms: list[str] = Field(default_factory=list, max_length=10)
    brand_voice_id: str | None = None


class ContentVariantResponse(BaseModel):
    """Per-platform variant row inside ContentPackageResponse."""

    id: str
    platform: str
    content: str = ""
    char_count: int = 0
    validation_status: ContentVariantState = ContentVariantState.pending
    publish_status: ContentVariantState = ContentVariantState.pending
    error: str | None = None
    remote_id: str | None = None


class ContentPackageResponse(BaseModel):
    """GET /api/v1/content-packages/{id} response (brief §6)."""

    id: str
    source_type: ContentSourceType
    source_ref: str
    state: ContentPackageState = ContentPackageState.draft
    brand_voice_id: str | None = None
    platforms: list[str] = Field(default_factory=list)
    variants: list[ContentVariantResponse] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContentPackageHistory(BaseModel):
    """GET /api/v1/content-packages/{id}/history response."""

    events: list[dict] = Field(default_factory=list)
