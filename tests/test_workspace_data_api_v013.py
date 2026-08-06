"""Workspace data APIs used by the complete React navigation."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import workspaces


def client(tmp_path: Path) -> TestClient:
    workspaces._DB = tmp_path / "ops.db"
    app = FastAPI()
    app.include_router(workspaces.router)
    return TestClient(app)


def test_workspace_overview_exposes_all_gui_collections(tmp_path: Path) -> None:
    api = client(tmp_path)
    response = api.get("/api/v1/workspace-overview")
    assert response.status_code == 200
    assert set(response.json()) == {
        "campaigns",
        "assets",
        "approvals",
        "publish_batches",
        "deliveries",
        "localization_jobs",
        "locale_variants",
        "voice_profiles",
        "voice_rules",
        "provenance",
        "summary",
    }


def test_campaign_and_content_lists_return_created_data(tmp_path: Path) -> None:
    api = client(tmp_path)
    campaign = api.post(
        "/api/v1/campaigns", json={"name": "Launch", "brief": "Brief", "channels": ["linkedin"]}
    ).json()
    api.post(
        f"/api/v1/campaigns/{campaign['id']}/assets",
        json={"channel": "linkedin", "title": "Post", "content": "Copy", "author": "alice"},
    )
    overview = api.get("/api/v1/workspace-overview").json()
    assert overview["campaigns"][0]["name"] == "Launch"
    assert overview["assets"][0]["title"] == "Post"


def test_python_311_dependency_marker_and_windows_runner_exist() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    runner = Path("scripts/run_backend.py").read_text(encoding="utf-8")
    assert "scipy==1.17.1" in pyproject and "python_version <" in pyproject
    assert "scipy==1.18.0" in pyproject and "python_version >=" in pyproject
    assert 'reload_dirs=["src"]' in runner
