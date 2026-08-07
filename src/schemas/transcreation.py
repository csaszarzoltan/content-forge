"""Pydantic schemas for the transcreation / cultural adaptation module.

Covers US-001 .. US-005 acceptance criteria:
  US-001  Cultural risk detection (idioms, references, register, taboo)
  US-002  Locale formatting conversion (dates, currency, units, honorifics)
  US-003  Low-confidence flagging
  US-004  Side-by-side review (per-segment accept/edit/reject)
  US-005  Pre-flight publish check
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ── Enums ───────────────────────────────────────────────────────────────────

class RiskCategory(str, Enum):
    """Categories of cultural risk detected in translated content."""

    idiom = "idiom"
    cultural_reference = "cultural_reference"
    register = "register"
    taboo = "taboo"


class RiskLevel(str, Enum):
    """Severity of a detected cultural risk item."""

    low = "low"
    medium = "medium"
    high = "high"


class FormatType(str, Enum):
    """Locale-specific format categories."""

    date = "date"
    currency = "currency"
    unit = "unit"
    honorific = "honorific"


class SegmentDecision(str, Enum):
    """Reviewer decision on a per-segment basis."""

    accept = "accept"
    reject = "reject"
    edit = "edit"


# ── US-001/002/003 — Risk & adaptation models ──────────────────────────────

class RiskItem(BaseModel):
    """A single cultural risk item detected by the analyzer."""

    id: str = Field(..., description="Unique segment-level risk identifier")
    segment: str = Field(..., description="The source text segment")
    category: RiskCategory = Field(..., description="Risk category")
    original_text: str = Field(..., description="Original text triggering the risk")
    issue_description: str = Field(..., description="Human-readable issue description")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence (0-1)"
    )
    risk_level: RiskLevel = Field(..., description="Assessed risk severity")
    suggested_replacement: str | None = Field(
        None, description="Suggested culturally adapted replacement"
    )
    locale: str = Field(..., description="Target locale code (e.g. 'de-DE')")


class LocaleFormatItem(BaseModel):
    """A locale-formatting conversion detected and applied."""

    id: str | None = Field(
        None, description="Stable identifier (e.g. 'fmt-date-1') used to accept/reject conversions"
    )
    original: str = Field(..., description="Original value before conversion")
    converted: str = Field(..., description="Converted value for target locale")
    format_type: FormatType = Field(..., description="Type of formatting applied")
    ambiguous: bool = Field(
        False, description="True if conversion is ambiguous and needs manual review"
    )
    locale: str = Field(..., description="Target locale code")


# ── US-001 — Analyze request/response ──────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/transcreation/analyze."""

    text: str = Field(..., min_length=1, description="Text to analyze for cultural risks")
    target_locale: str = Field(..., min_length=2, description="Target locale (e.g. 'de-DE')")
    source_locale: str = Field("auto", description="Source locale or 'auto'")


class AnalyzeResponse(BaseModel):
    """Response body for POST /api/v1/transcreation/analyze."""

    risk_items: list[RiskItem] = Field(default_factory=list)
    format_items: list[LocaleFormatItem] = Field(default_factory=list)
    overall_risk: RiskLevel = Field(RiskLevel.low, description="Highest risk level found")
    locale: str = Field(..., description="Target locale analyzed against")


# ── US-001/004 — Adapt request/response ────────────────────────────────────

class AdaptedSegment(BaseModel):
    """A single segment with original, literal, and adapted versions."""

    id: str = Field(..., description="Segment identifier (matches RiskItem.id)")
    original: str = Field(..., description="Original source text")
    literal: str = Field(..., description="Literal translation")
    adapted: str = Field(..., description="Cultural adaptation applied")
    risk_item: RiskItem | None = Field(None, description="Associated risk item, if any")
    decision: SegmentDecision | None = Field(None, description="Reviewer decision")


class AdaptRequest(BaseModel):
    """Request body for POST /api/v1/transcreation/adapt."""

    text: str = Field(..., min_length=1, description="Text to culturally adapt")
    target_locale: str = Field(..., min_length=2, description="Target locale")
    source_locale: str = Field("auto", description="Source locale or 'auto'")
    accepted_ids: list[str] = Field(default_factory=list)
    rejected_ids: list[str] = Field(default_factory=list)
    edits: dict[str, str] = Field(default_factory=dict)


class AdaptResponse(BaseModel):
    """Response body for POST /api/v1/transcreation/adapt."""

    adapted_text: str = Field(..., description="Fully adapted text output")
    segments: list[AdaptedSegment] = Field(default_factory=list)
    changes_log: list[dict] = Field(default_factory=list)
    flagged_segments: list[str] = Field(
        default_factory=list,
        description="IDs of low-confidence segments needing review",
    )


# ── US-003 — Confidence flagging ───────────────────────────────────────────

class FlaggedSegment(BaseModel):
    """A segment flagged for human review due to low confidence."""

    id: str
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., description="Why this segment was flagged")


class ConfidenceFlag(BaseModel):
    """Container for flagged segments returned by analyze/adapt."""

    flagged: list[FlaggedSegment] = Field(default_factory=list)
    threshold: float = Field(0.7, description="Confidence threshold below which segments are flagged")


# ── US-005 — Preflight ────────────────────────────────────────────────────

class PreflightRequest(BaseModel):
    """Request body for POST /api/v1/transcreation/preflight."""

    asset_id: str = Field(..., min_length=1, description="Asset identifier")
    content: str = Field(..., min_length=1, description="Content to preflight-check")
    target_locale: str = Field(..., min_length=2, description="Target locale")


class PreflightResult(BaseModel):
    """Response body for POST /api/v1/transcreation/preflight."""

    asset_id: str
    risk_items: list[RiskItem] = Field(default_factory=list)
    format_items: list[LocaleFormatItem] = Field(default_factory=list)
    blocked: bool = Field(False, description="True if high-risk items block publish")
    blocked_reasons: list[str] = Field(default_factory=list)
    audit_status: Literal["pass", "fail", "review_needed"] = Field("pass")
    override_available: bool = Field(
        True, description="Whether the user may override and publish anyway"
    )


# ── US-004 — Decision log ──────────────────────────────────────────────────

class DecisionLog(BaseModel):
    """Records a reviewer decision on a segment."""

    segment_id: str
    decision: SegmentDecision
    edited_text: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: str = Field("system", description="Who made the decision")


# ── Persisted result ────────────────────────────────────────────────────────

class TranscreationResult(BaseModel):
    """Persisted transcreation analysis + adaptation result for an asset."""

    id: str = Field(..., description="Result identifier")
    asset_id: str = Field(..., description="Associated asset")
    analysis: AnalyzeResponse | None = None
    adaptation: AdaptResponse | None = None
    preflight: PreflightResult | None = None
    decisions: list[DecisionLog] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
