"""Human-facing workspaces and automation contracts for content operations."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from src.product_ops import ContentOpsStore, render_campaign_detail, render_workspace

router = APIRouter()
_DB = Path(os.getenv("CONTENTFORGE_OPS_DB", "/tmp/contentforge_ops.db"))


def _store() -> ContentOpsStore:
    return ContentOpsStore(_DB)


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    channels: list[str] = Field(min_length=1, max_length=20)


class ApprovalCreate(BaseModel):
    asset_id: str
    requester: str
    risk: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    findings: list[str] = Field(default_factory=list)


class PublishBatchCreate(BaseModel):
    asset_id: str
    channels: list[str] = Field(min_length=1)


class LocalizationCreate(BaseModel):
    asset_id: str
    locales: list[str] = Field(min_length=1)


class ProvenanceCreate(BaseModel):
    asset_id: str
    model: str
    prompt_template: str
    voice_version: str


@router.get("/workspace/{page}", response_class=HTMLResponse)
def workspace(page: str) -> HTMLResponse:
    """Render an accessible workspace with empty and recovery states."""
    try:
        return HTMLResponse(render_workspace(page, _store()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc


@router.get("/workspace/campaigns/{campaign_id}", response_class=HTMLResponse)
def campaign_detail(campaign_id: str) -> HTMLResponse:
    """Show one campaign with human-readable state and contextual next action."""
    try:
        return HTMLResponse(render_campaign_detail(campaign_id, _store()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="campaign_not_found") from exc


@router.post("/workspace/campaigns/create", response_class=HTMLResponse)
async def create_campaign_from_workspace(request: Request) -> Response:
    """Create a campaign from the accessible HTML form without JavaScript."""
    from urllib.parse import parse_qs

    values = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    name = values.get("name", [""])[0].strip()
    brief = values.get("brief", [""])[0].strip()
    channels = [item.strip().lower() for item in values.get("channels", [""])[0].split(",") if item.strip()]
    if not name or not brief or not channels or len(name) > 160 or len(brief) > 4000 or len(channels) > 20:
        return HTMLResponse(render_workspace("campaigns", _store(), "Check the campaign name, brief, and channels.", True), status_code=422)
    campaign_id = _store().create_campaign(name, channels)
    return RedirectResponse(f"/workspace/campaigns/{campaign_id}", status_code=303)


@router.post("/api/v1/campaigns", status_code=201)
def create_campaign(body: CampaignCreate) -> dict[str, str]:
    campaign_id = _store().create_campaign(body.name, body.channels)
    return {"id": campaign_id, "state": "DRAFT"}


@router.post("/api/v1/approvals", status_code=201)
def create_approval(body: ApprovalCreate) -> dict[str, str]:
    request_id = _store().request_approval(body.asset_id, body.requester, body.risk, body.findings)
    return {"id": request_id, "state": "PENDING"}


@router.post("/api/v1/publish-batches", status_code=201)
def create_publish_batch(body: PublishBatchCreate) -> dict[str, str]:
    batch_id = _store().create_publish_batch(body.asset_id, body.channels)
    return {"id": batch_id, "state": "VALIDATING"}


@router.post("/api/v1/localization-jobs", status_code=201)
def create_localization(body: LocalizationCreate) -> dict[str, str]:
    job_id = _store().create_localization_job(body.asset_id, body.locales)
    return {"id": job_id, "state": "QUEUED"}


@router.post("/api/v1/provenance", status_code=201)
def create_provenance(body: ProvenanceCreate) -> dict[str, str]:
    record_id = _store().capture_provenance(
        body.asset_id, body.model, body.prompt_template, body.voice_version
    )
    return {"id": record_id, "state": "CAPTURED"}


@router.get("/api/v1/provenance/{record_id}/export")
def export_provenance(record_id: str) -> Response:
    try:
        return Response(
            content=_store().export_provenance(record_id), media_type="application/json"
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="provenance_not_found") from exc
