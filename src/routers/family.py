"""JWT-authenticated Family Creator workflow API."""

# ruff: noqa: B008
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from src.config import get_settings
from src.connectors.errors import ConnectorError
from src.connectors.linkedin import LinkedInConnector
from src.connectors.twitter import TwitterConnector
from src.dependencies import get_current_user
from src.family.store import FamilyStore, PermissionDenied
from src.models.user import User
from src.services.publish_service import PublishService

router = APIRouter(prefix="/api/v1/family", tags=["family"])
_DB = Path(os.getenv("CONTENTFORGE_OPS_DB", "/tmp/contentforge_ops.db"))


def store():
    return FamilyStore(_DB)


def run(fn):
    try:
        return fn()
    except PermissionDenied as e:
        raise HTTPException(403, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(404, detail=str(e)) from e
    except ValueError as e:
        code = (
            410
            if "expired" in str(e) or "revoked" in str(e)
            else 409
            if any(
                x in str(e)
                for x in [
                    "approval_",
                    "stale",
                    "idempotency",
                    "last_owner",
                    "nothing_to_retry",
                    "reconciliation_required",
                ]
            )
            else 422
        )
        raise HTTPException(code, detail=str(e)) from e


def actor(u: User):
    return u.id, u.display_name or u.email.split("@")[0], u.email


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    mode: str = Field(pattern="^FAMILY_(CREATOR|BUSINESS)$")


class InviteIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str


class RoleIn(BaseModel):
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


class AutosaveIn(BaseModel):
    workspace_id: str
    content: str = Field(min_length=1, max_length=100000)
    expected_version: int = Field(ge=1)


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
    u: User = Depends(get_current_user),
):
    uid, name, _ = actor(u)
    return run(lambda: store().create_workspace(uid, name, body.name, body.mode, idempotency_key))


@router.get("/session")
def session(workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().session(workspace_id, u.id))


@router.post("/workspaces/{workspace_id}/invitations", status_code=201)
def invite(workspace_id: str, body: InviteIn, u: User = Depends(get_current_user)):
    return run(lambda: store().create_invitation(workspace_id, u.id, body.email, body.role))


@router.get("/invitations/{token}/preview")
def preview(token: str):
    return run(lambda: store().invitation_preview(token))


@router.post("/invitations/{token}/accept")
def accept(token: str, u: User = Depends(get_current_user)):
    return run(lambda: store().accept_invitation(token, u.id, u.email))


@router.get("/workspaces/{workspace_id}/members")
def members(workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().members(workspace_id, u.id))


@router.patch("/workspaces/{workspace_id}/members/{membership_id}")
def member_role(
    workspace_id: str, membership_id: str, body: RoleIn, u: User = Depends(get_current_user)
):
    return run(lambda: store().update_member(workspace_id, u.id, membership_id, body.role))


@router.delete("/workspaces/{workspace_id}/members/{membership_id}", status_code=204)
def member_remove(workspace_id: str, membership_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().remove_member(workspace_id, u.id, membership_id))


@router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}", status_code=204)
def invite_revoke(workspace_id: str, invitation_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().revoke_invitation(workspace_id, u.id, invitation_id))


@router.get("/home")
def home(workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().home(workspace_id, u.id))


@router.post("/journeys", status_code=201)
def journey(
    body: JourneyIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    u: User = Depends(get_current_user),
):
    return run(
        lambda: store().create_journey(
            body.workspace_id, u.id, body.model_dump(exclude={"workspace_id"}), idempotency_key
        )
    )


@router.get("/assets/{asset_id}")
def asset(asset_id: str, workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().asset_detail(workspace_id, u.id, asset_id))


@router.put("/assets/{asset_id}/autosave")
def autosave(asset_id: str, body: AutosaveIn, u: User = Depends(get_current_user)):
    return run(
        lambda: store().save_revision(
            body.workspace_id, u.id, asset_id, body.content, body.expected_version
        )
    )


@router.get("/assets/{asset_id}/revisions")
def revisions(asset_id: str, workspace_id: str, u: User = Depends(get_current_user)):
    return {"items": run(lambda: store().asset_detail(workspace_id, u.id, asset_id)["revisions"])}


@router.post("/assets/{asset_id}/submit-review")
def submit(asset_id: str, body: ReviewIn, u: User = Depends(get_current_user)):
    return run(lambda: store().submit_review(body.workspace_id, u.id, asset_id, body.note))


@router.get("/reviews")
def reviews(workspace_id: str, u: User = Depends(get_current_user)):
    return {"items": run(lambda: store().reviews(workspace_id, u.id))}


@router.get("/reviews/{review_id}")
def review(review_id: str, workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().review_detail(workspace_id, u.id, review_id))


@router.post("/reviews/{review_id}/decision")
def decision(review_id: str, body: DecisionIn, u: User = Depends(get_current_user)):
    return run(
        lambda: store().decide_review(
            body.workspace_id, u.id, review_id, body.decision, body.reason
        )
    )


@router.get("/assets/{asset_id}/publish-eligibility")
def eligibility(asset_id: str, workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().publish_eligibility(workspace_id, u.id, asset_id))


@router.get("/connections")
def connections(return_to: str = "#home", u: User = Depends(get_current_user)):
    cfg = get_settings()
    items = [
        {
            "channel": "linkedin",
            "label": "LinkedIn",
            "state": "HEALTHY" if cfg.LINKEDIN_ACCESS_TOKEN else "ACTION_REQUIRED",
            "action": "Return to publish" if cfg.LINKEDIN_ACCESS_TOKEN else "Reconnect",
            "authorize_url": f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={cfg.LINKEDIN_CLIENT_ID}&redirect_uri={cfg.PUBLIC_APP_URL}/auth/linkedin/callback&scope=w_member_social"
            if cfg.LINKEDIN_CLIENT_ID
            else None,
        },
        {
            "channel": "twitter",
            "label": "X",
            "state": "HEALTHY"
            if all(
                [
                    cfg.TWITTER_API_KEY,
                    cfg.TWITTER_API_SECRET,
                    cfg.TWITTER_ACCESS_TOKEN,
                    cfg.TWITTER_ACCESS_TOKEN_SECRET,
                ]
            )
            else "ACTION_REQUIRED",
            "action": "Return to publish" if cfg.TWITTER_ACCESS_TOKEN else "Reconnect",
            "authorize_url": "https://twitter.com/i/oauth2/authorize"
            if cfg.TWITTER_API_KEY
            else None,
        },
    ]
    return {"items": items, "return_to": return_to}


@router.get("/weekly-summary")
def weekly_summary(workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().weekly_summary(workspace_id, u.id))


@router.post("/publish-batches", status_code=201)
async def publish(
    body: PublishIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    u: User = Depends(get_current_user),
):
    db = store()
    batch = run(
        lambda: db.prepare_publish_batch(
            body.workspace_id,
            u.id,
            body.asset_id,
            body.revision_version,
            body.channels,
            idempotency_key,
        )
    )
    cfg = get_settings()
    connectors = {}
    if cfg.LINKEDIN_ACCESS_TOKEN:
        connectors["linkedin"] = LinkedInConnector(
            cfg.LINKEDIN_CLIENT_ID, cfg.LINKEDIN_CLIENT_SECRET, cfg.LINKEDIN_ACCESS_TOKEN
        )
    if all(
        [
            cfg.TWITTER_API_KEY,
            cfg.TWITTER_API_SECRET,
            cfg.TWITTER_ACCESS_TOKEN,
            cfg.TWITTER_ACCESS_TOKEN_SECRET,
        ]
    ):
        connectors["twitter"] = TwitterConnector(
            cfg.TWITTER_API_KEY,
            cfg.TWITTER_API_SECRET,
            cfg.TWITTER_ACCESS_TOKEN,
            cfg.TWITTER_ACCESS_TOKEN_SECRET,
        )
    service = PublishService(connectors)
    for channel in body.channels:
        if channel not in connectors:
            db.complete_delivery(batch["id"], channel, "FAILED", error_code="connection_required")
            continue
        try:
            result = await service.publish(
                body.asset_id,
                channel,
                text=batch["asset"]["content"],
                author=cfg.LINKEDIN_AUTHOR_URN or None,
            )
            db.complete_delivery(
                batch["id"],
                channel,
                "PUBLISHED",
                remote_id=result.get("platform_url") or result.get("publish_id"),
            )
        except (ConnectorError, ValueError) as exc:
            code = "auth_failed" if "auth" in str(exc).lower() else "provider_error"
            db.complete_delivery(batch["id"], channel, "RETRYABLE", error_code=code)
    return db.publish_result(body.workspace_id, u.id, batch["id"])


@router.get("/publish-batches/{batch_id}")
def result(batch_id: str, workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().publish_result(workspace_id, u.id, batch_id))


@router.post("/publish-batches/{batch_id}/retry")
def retry(batch_id: str, workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().retry_publish(workspace_id, u.id, batch_id))


@router.post("/publish-batches/{batch_id}/reconcile")
def reconcile(batch_id: str, workspace_id: str, u: User = Depends(get_current_user)):
    return run(lambda: store().reconcile_publish(workspace_id, u.id, batch_id))
