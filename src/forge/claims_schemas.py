"""Content-Forge claim/provenance schemas (spec §3.3, P0-3).

Pydantic models for claim verification and provenance blocks. The enum and
behavioral logic live in src/forge/claims.py — this module exists per the
spec's file layout and re-exports the shared models.
"""

from __future__ import annotations

from src.forge.claims import (  # noqa: F401
    Claim,
    ClaimClassification,
    ProvenanceBlock,
)

__all__ = ["Claim", "ClaimClassification", "ProvenanceBlock"]
