"""Acceptance tests for the actionable workspace UX added in v0.11."""
from pathlib import Path

import pytest

from src.product_ops import ContentOpsStore, render_campaign_detail, render_workspace

pytestmark = pytest.mark.quick


def _store(tmp_path: Path) -> ContentOpsStore:
    return ContentOpsStore(tmp_path / "ops.db")


def test_campaign_workspace_has_real_form_and_structured_fields(tmp_path: Path) -> None:
    html = render_workspace("campaigns", _store(tmp_path))
    assert 'action="/workspace/campaigns/create"' in html
    assert 'name="name"' in html
    assert 'name="brief"' in html
    assert 'name="channels"' in html
    assert 'aria-describedby="channels-help"' in html


def test_campaign_cards_link_to_contextual_detail(tmp_path: Path) -> None:
    ops = _store(tmp_path)
    campaign_id = ops.create_campaign("Launch", ["linkedin", "twitter"])
    html = render_workspace("campaigns", ops)
    assert f'/workspace/campaigns/{campaign_id}' in html
    assert "Open campaign" in html


def test_campaign_detail_explains_state_and_next_action(tmp_path: Path) -> None:
    ops = _store(tmp_path)
    campaign_id = ops.create_campaign("Launch", ["linkedin"])
    html = render_campaign_detail(campaign_id, ops)
    assert "Draft" in html
    assert "Add or generate channel assets" in html
    assert "Back to campaigns" in html
    assert 'aria-label="Campaign progress"' in html


def test_recovery_is_contextual_not_always_visible(tmp_path: Path) -> None:
    html = render_workspace("campaigns", _store(tmp_path))
    assert "The last stable state is preserved" not in html
    error_html = render_workspace("campaigns", _store(tmp_path), notice="Campaign could not be created", error=True)
    assert 'role="alert"' in error_html
    assert "Campaign could not be created" in error_html


def test_workspace_summary_exposes_attention_counts(tmp_path: Path) -> None:
    ops = _store(tmp_path)
    ops.request_approval("asset-1", "alice", "HIGH", ["claim"])
    summary = ops.attention_summary()
    assert summary["pending_approvals"] == 1
    html = render_workspace("approvals", ops)
    assert "1 pending approval" in html

def test_workspace_campaign_form_creates_and_redirects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from src.main import app
    from src.routers import workspaces

    monkeypatch.setattr(workspaces, "_DB", tmp_path / "web.db")
    client = TestClient(app)
    response = client.post(
        "/workspace/campaigns/create",
        data={"name": "Launch", "brief": "Introduce the product", "channels": "LinkedIn, X"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/workspace/campaigns/")


def test_workspace_campaign_form_preserves_accessible_error_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from src.main import app
    from src.routers import workspaces

    monkeypatch.setattr(workspaces, "_DB", tmp_path / "web.db")
    response = TestClient(app).post(
        "/workspace/campaigns/create",
        data={"name": "", "brief": "", "channels": ""},
    )
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert "Check the campaign name" in response.text
