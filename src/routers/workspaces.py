"""Human-facing workspaces and automation contracts for content operations."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from src.product_ops import ContentOpsStore, render_approval_detail, render_campaign_detail, render_publish_batch_detail, render_workspace

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


def _form(body: bytes) -> dict[str, str]:
    from urllib.parse import parse_qs
    return {key: values[0] for key, values in parse_qs(body.decode(), keep_blank_values=True).items()}

@router.get("/workspace/campaigns/{campaign_id}", response_class=HTMLResponse)
def campaign_detail(campaign_id: str) -> HTMLResponse:
    try: return HTMLResponse(render_campaign_detail(campaign_id, _store()))
    except KeyError as exc: raise HTTPException(404, "campaign_not_found") from exc

@router.post("/workspace/campaigns/create")
async def create_campaign_form(request: Request) -> Response:
    data=_form(await request.body()); name=data.get("name","").strip(); brief=data.get("brief","").strip(); channels=[x.strip().lower() for x in data.get("channels","").split(",") if x.strip()]
    if not name or not brief or not channels: return HTMLResponse(render_workspace("campaigns",_store(),"Check the campaign name, brief, and channels.",True),422)
    campaign_id=_store().create_campaign(name,channels); return RedirectResponse(f"/workspace/campaigns/{campaign_id}",303)

@router.get("/workspace/approvals/{request_id}", response_class=HTMLResponse)
def approval_detail(request_id: str) -> HTMLResponse:
    try: return HTMLResponse(render_approval_detail(request_id,_store()))
    except KeyError as exc: raise HTTPException(404,"approval_not_found") from exc

@router.post("/workspace/approvals/{request_id}/decision")
async def approval_decision(request_id: str, request: Request) -> Response:
    data=_form(await request.body()); reviewer=data.get("reviewer","").strip(); decision=data.get("decision",""); reason=data.get("reason","").strip()
    if not reviewer or decision not in {"APPROVED","NEEDS_CHANGES","REJECTED"} or not reason:
        return HTMLResponse(render_approval_detail(request_id,_store(),"Reviewer, decision, and reason are required.",True),422)
    try: _store().decide_approval(request_id,reviewer,decision,reason)
    except PermissionError: return HTMLResponse(render_approval_detail(request_id,_store(),"High-risk content cannot be approved by its requester.",True),403)
    except KeyError as exc: raise HTTPException(404,"approval_not_found") from exc
    return RedirectResponse(f"/workspace/approvals/{request_id}",303)

@router.get("/workspace/publish/{batch_id}", response_class=HTMLResponse)
def publish_batch_detail(batch_id: str) -> HTMLResponse:
    try: return HTMLResponse(render_publish_batch_detail(batch_id,_store()))
    except KeyError as exc: raise HTTPException(404,"publish_batch_not_found") from exc

@router.post("/workspace/publish/{batch_id}/retry")
async def publish_batch_retry(batch_id: str, request: Request) -> Response:
    await request.body()
    try: channels=_store().request_publish_retry(batch_id)
    except KeyError as exc: raise HTTPException(404,"publish_batch_not_found") from exc
    except ValueError: return HTMLResponse(render_publish_batch_detail(batch_id,_store(),"This batch has no failed channels to retry.",True),409)
    scope=", ".join(channels)
    return HTMLResponse(render_publish_batch_detail(batch_id,_store(),f"Retry queued for: {scope}. Successful channels were preserved."),202)



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
