"""Transcreation API endpoints.

US-001..US-005 implementation:
  POST /api/v1/transcreation/analyze   — detect cultural risks + locale formatting
  POST /api/v1/transcreation/adapt     — culturally adapt content with review inputs
  POST /api/v1/transcreation/preflight — pre-flight publish check (blocks until
                                         resolved or explicitly overridden)

Results are persisted per asset in SQLite via the product_ops
(TranscreationStore) pattern. Error handling contract:
  400 malformed params (Pydantic validation), 404 missing assets,
  409 preflight-blocked publish, 502/503 external (LLM) failures —
  every error body is JSON.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.product_ops import TranscreationStore
from src.schemas.transcreation import (
    AdaptRequest,
    AdaptResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ExportRequest,
    PreflightRequest,
    PreflightResult,
    TranscreationResult,
)
from src.services.transcreation import (
    TranscreationBlockedError,
    TranscreationProviderError,
    TranscreationService,
)

router = APIRouter(prefix="/api/v1/transcreation", tags=["transcreation"])

_DB = Path(os.getenv("CONTENTFORGE_OPS_DB", "/tmp/contentforge_ops.db"))


def _store() -> TranscreationStore:
    return TranscreationStore(_DB)


def _service(store: TranscreationStore) -> TranscreationService:
    return TranscreationService(store=store)


class PreflightOverrideRequest(BaseModel):
    """Explicit override of a preflight block (US-005)."""

    override: bool = Field(True, description="Set false to revoke an override")


def _provider_error_status(exc: Exception) -> tuple[int, str]:
    """Map provider errors to 502 (bad gateway) / 503 (unavailable) responses."""
    message = str(exc)
    if any(token in message.lower() for token in ("timeout", "unavailable", "connection")):
        return 503, "transcreation_provider_unavailable"
    return 502, "transcreation_provider_error"


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_transcreation(body: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze content for cultural risks and locale formatting (US-001/US-002)."""
    store = _store()
    service = _service(store)
    try:
        result = await service.analyze(body.text, body.target_locale, body.source_locale)
    except TranscreationProviderError as exc:
        status, detail = _provider_error_status(exc)
        raise HTTPException(status_code=status, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="transcreation_analysis_unavailable") from exc
    return result


@router.post("/adapt", response_model=AdaptResponse)
async def adapt_transcreation(body: AdaptRequest) -> AdaptResponse:
    """Culturally adapt content, honoring per-segment review decisions (US-004)."""
    store = _store()
    service = _service(store)
    try:
        result = await service.adapt(
            body.text,
            body.target_locale,
            body.source_locale,
            accepted_ids=body.accepted_ids,
            rejected_ids=body.rejected_ids,
            edits=body.edits,
        )
    except TranscreationProviderError as exc:
        status, detail = _provider_error_status(exc)
        raise HTTPException(status_code=status, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="transcreation_adaptation_unavailable") from exc

    asset_id = getattr(body, "asset_id", None)
    if asset_id:
        store.save_result(
            TranscreationResult(
                id=store._id(),
                asset_id=asset_id,
                adaptation=result,
            )
        )
    return result


@router.post("/preflight", response_model=PreflightResult)
async def preflight_transcreation(body: PreflightRequest) -> PreflightResult:
    """Pre-flight publish check: flag high-risk items and block until resolved (US-005)."""
    store = _store()
    service = _service(store)
    try:
        result = await service.preflight(body.asset_id, body.content, body.target_locale)
    except TranscreationProviderError as exc:
        status, detail = _provider_error_status(exc)
        raise HTTPException(status_code=status, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="transcreation_preflight_unavailable") from exc

    return result


@router.get("/preflight/{asset_id}", response_model=PreflightResult)
async def get_preflight(asset_id: str) -> PreflightResult:
    """Return the latest stored preflight result for an asset (for publish gates)."""
    store = _store()
    try:
        result = store.result(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="transcreation_result_not_found") from exc
    if result.preflight is None:
        raise HTTPException(status_code=404, detail="transcreation_preflight_not_found")
    return result.preflight


@router.post("/preflight/{asset_id}/override", response_model=PreflightResult)
async def override_preflight(asset_id: str, body: PreflightOverrideRequest) -> PreflightResult:
    """Explicitly override the preflight block so publishing may proceed (US-005)."""
    store = _store()
    try:
        store.set_override(asset_id, body.override)
        result = store.result(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="transcreation_result_not_found") from exc
    if result.preflight is None:
        raise HTTPException(status_code=404, detail="transcreation_preflight_not_found")
    return result.preflight


@router.get("/assets/{asset_id}/result")
async def get_asset_result(asset_id: str) -> TranscreationResult:
    """Return the full persisted transcreation result for an asset."""
    store = _store()
    try:
        return store.result(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="transcreation_result_not_found") from exc


@router.post("/assets/{asset_id}/export", response_model=dict[str, str])
async def export_asset(asset_id: str, body: ExportRequest | None = None) -> dict[str, str]:
    """Export accepted adaptations; blocked while unresolved flags exist (US-003 AC2)."""
    if body is None:
        body = ExportRequest()
    store = _store()
    service = _service(store)
    try:
        adapted = await service.export(asset_id, accepted_ids=body.accepted_ids, rejected_ids=body.rejected_ids)
    except TranscreationBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="transcreation_result_not_found") from exc
    return {"asset_id": asset_id, "adapted_text": adapted}
