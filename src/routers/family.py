"""Family Creator authenticated workflow API."""
# ruff: noqa: B008

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.family.store import FamilyStore, PermissionDenied

router = APIRouter(prefix="/api/v1/family", tags=["family"])
_DB = Path(os.getenv("CONTENTFORGE_OPS_DB", "/tmp/contentforge_ops.db"))


def store():
    return FamilyStore(_DB)


def actor(
    x_user_id: str = Header(...),
    x_user_name: str = Header("Family member"),
    x_user_email: str = Header("member@example.com"),
):
    return {"id": x_user_id, "name": x_user_name, "email": x_user_email}


def run(fn):
    try:
        return fn()
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            409 if "approval_" in str(e) or "stale" in str(e) or "idempotency" in str(e) else 422,
            detail=str(e),
        ) from e


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    mode: str = Field(pattern="^FAMILY_(CREATOR|BUSINESS)$")


class InviteIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str


class JourneyIn(BaseModel):
    workspace_id: str
    goal: str
    project_name: str = Field(min_length=2, max_length=80)
    audience: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=10, max_length=2000)
    cta: str = ""
    source_notes: str = ""
    channels: list[str] = Field(min_length=1, max_length=2)


class ReviewIn(BaseModel):
    workspace_id: str
    note: str = Field(default="", max_length=500)


class DecisionIn(BaseModel):
    workspace_id: str
    decision: str
    reason: str = Field(default="", max_length=1000)


class PublishIn(BaseModel):
    workspace_id: str
    asset_id: str
    revision_version: int = Field(ge=1)
    channels: list[str] = Field(min_length=1, max_length=2)


@router.post("/workspaces", status_code=201)
def create_workspace(
    body: WorkspaceIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    a: dict = Depends(actor),
):
    return run(
        lambda: store().create_workspace(a["id"], a["name"], body.name, body.mode, idempotency_key)
    )


@router.get("/session")
def session(workspace_id: str, a: dict = Depends(actor)):
    return run(lambda: store().session(workspace_id, a["id"]))


@router.post("/workspaces/{workspace_id}/invitations", status_code=201)
def invite(workspace_id: str, body: InviteIn, a: dict = Depends(actor)):
    return run(lambda: store().create_invitation(workspace_id, a["id"], body.email, body.role))


@router.post("/invitations/{token}/accept")
def accept(token: str, a: dict = Depends(actor)):
    return run(lambda: store().accept_invitation(token, a["id"], a["email"]))


@router.get("/home")
def home(workspace_id: str, a: dict = Depends(actor)):
    return run(lambda: store().home(workspace_id, a["id"]))


@router.post("/journeys", status_code=201)
def journey(
    body: JourneyIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    a: dict = Depends(actor),
):
    return run(
        lambda: store().create_journey(
            body.workspace_id, a["id"], body.model_dump(exclude={"workspace_id"}), idempotency_key
        )
    )


@router.post("/ideas", status_code=201)
async def idea(
    workspace_id: str = Form(...),
    client_id: str = Form(...),
    kind: str = Form(...),
    text: str = Form(""),
    caption: str = Form(""),
    file: UploadFile | None = File(None),
    a: dict = Depends(actor),
):
    path = None
    if file:
        data = await file.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024 or file.content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise HTTPException(422, detail="invalid_image")
        root = Path(os.getenv("UPLOAD_ROOT", "uploads")) / "family"
        root.mkdir(parents=True, exist_ok=True)
        path = str(root / f"{client_id}.{file.filename.rsplit('.', 1)[-1].lower()}")
        Path(path).write_bytes(data)
    return run(
        lambda: store().create_idea(workspace_id, a["id"], client_id, kind, text, caption, path)
    )


@router.post("/assets/{asset_id}/submit-review")
def submit(asset_id: str, body: ReviewIn, a: dict = Depends(actor)):
    return run(lambda: store().submit_review(body.workspace_id, a["id"], asset_id, body.note))


@router.get("/reviews")
def reviews(workspace_id: str, a: dict = Depends(actor)):
    return {"items": run(lambda: store().reviews(workspace_id, a["id"]))}


@router.post("/reviews/{review_id}/decision")
def decision(review_id: str, body: DecisionIn, a: dict = Depends(actor)):
    return run(
        lambda: store().decide_review(
            body.workspace_id, a["id"], review_id, body.decision, body.reason
        )
    )


@router.post("/publish-batches", status_code=201)
def publish(
    body: PublishIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    a: dict = Depends(actor),
):
    return run(
        lambda: store().publish(
            body.workspace_id,
            a["id"],
            body.asset_id,
            body.revision_version,
            body.channels,
            idempotency_key,
        )
    )
