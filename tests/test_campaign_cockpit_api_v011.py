"""API contract tests for the campaign cockpit vertical slice."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import workspaces


def client(tmp_path: Path) -> TestClient:
    workspaces._DB = tmp_path / "ops.db"
    app = FastAPI()
    app.include_router(workspaces.router)
    return TestClient(app)


def test_campaign_create_cockpit_and_asset_flow(tmp_path: Path) -> None:
    api = client(tmp_path)
    created = api.post(
        "/api/v1/campaigns",
        json={"name": "Launch", "brief": "DACH launch", "channels": ["linkedin", "x"]},
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]
    asset = api.post(
        f"/api/v1/campaigns/{campaign_id}/assets",
        json={"channel": "linkedin", "title": "Launch post", "content": "Hello", "author": "anna"},
    )
    assert asset.status_code == 201
    cockpit = api.get(f"/api/v1/campaigns/{campaign_id}/cockpit")
    assert cockpit.status_code == 200
    assert cockpit.json()["campaign"]["brief"] == "DACH launch"
    assert cockpit.json()["readiness"]["score"] == 0


def test_revision_conflict_returns_409(tmp_path: Path) -> None:
    api = client(tmp_path)
    campaign_id = api.post(
        "/api/v1/campaigns", json={"name": "Launch", "brief": "Brief", "channels": ["x"]}
    ).json()["id"]
    asset_id = api.post(
        f"/api/v1/campaigns/{campaign_id}/assets",
        json={"channel": "x", "title": "Post", "content": "v1", "author": "anna"},
    ).json()["id"]
    assert (
        api.put(
            f"/api/v1/assets/{asset_id}/autosave",
            json={"content": "v2", "expected_version": 1, "author": "anna"},
        ).status_code
        == 200
    )
    stale = api.put(
        f"/api/v1/assets/{asset_id}/autosave",
        json={"content": "stale", "expected_version": 1, "author": "anna"},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == "asset_version_conflict"


def test_my_work_empty_state(tmp_path: Path) -> None:
    response = client(tmp_path).get("/api/v1/my-work")
    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0}
