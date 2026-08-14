"""Content-Forge brief entity schemas (spec §3.1, P0-1).

Pydantic v2 request/response models for the structured, versioned Brief.
Validation is enforced by BriefStore.validate() against FORGE_CHANNELS;
the schemas only enforce shape/length constraints.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OutputConstraints(BaseModel):
    """Per-channel output constraints attached to a brief."""

    length: str = "medium"  # short | medium | long
    tone: str = "professional"
    reading_level: str = "general"  # general | specialist
    keywords: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    hashtags: int | None = Field(default=None, strict=True)  # max hashtags for the channel


class BriefCreate(BaseModel):
    """Payload for creating/updating a brief (immutable per version)."""

    title: str = Field(..., min_length=1, max_length=200)
    audience: str = Field(..., min_length=1, max_length=2000)
    objective: str = Field(..., min_length=1, max_length=2000)
    offer: str = Field(..., min_length=1, max_length=2000)
    primary_cta: str = Field(..., min_length=1, max_length=500)
    language: str = "en"
    brand_profile_id: str | None = None
    channels: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)  # source refs: url | pasted text
    required_claims: list[str] = Field(default_factory=list)
    prohibited_phrases: list[str] = Field(default_factory=list)
    output_constraints: dict[str, OutputConstraints] = Field(default_factory=dict)  # key = channel


class Brief(BriefCreate):
    """A stored brief version — immutable once persisted."""

    brief_id: str
    version: int = 1  # immutable per save
    status: Literal["draft", "valid", "archived"] = "draft"
    created_by: str = "system"
    created_at: float = 0.0


__all__ = ["Brief", "BriefCreate", "OutputConstraints"]
