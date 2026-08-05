"""API tests for revision-bound approvals."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import workspaces


def client(tmp_path: Path) -> TestClient:
    workspaces._DB = tmp_path / "ops.db"
    app = FastAPI()
    app.include_router(workspaces.router)
    return TestClient(app)


def create_asset(api: TestClient) -> str:
    campaign = api.post(
        "/api/v1/campaigns", json={"name": "Launch", "brief": "Brief", "channels": ["linkedin"]}
    ).json()
    return api.post(
        f"/api/v1/campaigns/{campaign['id']}/assets",
        json={"channel": "linkedin", "title": "Post", "content": "Copy", "author": "alice"},
    ).json()["id"]


def test_request_and_decide_approval_api(tmp_path: Path) -> None:
    api = client(tmp_path)
    asset = create_asset(api)
    requested = api.post(
        f"/api/v1/assets/{asset}/approval",
        json={"requester": "alice", "risk": "LOW", "findings": []},
    )
    assert requested.status_code == 201
    request_id = requested.json()["id"]
    decided = api.post(
        f"/api/v1/approvals/{request_id}/decision",
        json={"reviewer": "bob", "decision": "APPROVED", "reason": "Ready"},
    )
    assert decided.status_code == 200
    audit = api.get(f"/api/v1/assets/{asset}/audit")
    assert audit.json()["count"] == 2


def test_stale_approval_returns_conflict(tmp_path: Path) -> None:
    api = client(tmp_path)
    asset = create_asset(api)
    request_id = api.post(
        f"/api/v1/assets/{asset}/approval",
        json={"requester": "alice", "risk": "LOW", "findings": []},
    ).json()["id"]
    api.put(
        f"/api/v1/assets/{asset}/autosave",
        json={"content": "Changed", "expected_version": 1, "author": "alice"},
    )
    response = api.post(
        f"/api/v1/approvals/{request_id}/decision",
        json={"reviewer": "bob", "decision": "APPROVED", "reason": "Old"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "approval_revision_stale"
