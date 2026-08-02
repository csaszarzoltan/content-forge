from pathlib import Path

import pytest


# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.product_ops import ContentOpsStore, render_workspace


def store(tmp_path: Path) -> ContentOpsStore:
    return ContentOpsStore(tmp_path / "ops.db")


def test_campaign_partial_run_preserves_successful_assets(tmp_path: Path) -> None:
    ops = store(tmp_path)
    campaign = ops.create_campaign("Launch", ["linkedin", "twitter"])
    ops.record_asset(campaign, "linkedin", "Ready copy", "READY")
    ops.record_asset(campaign, "twitter", "", "FAILED")
    view = ops.campaign(campaign)
    assert view["state"] == "PARTIAL"
    assert view["assets"][0]["content"] == "Ready copy"


def test_approver_cannot_approve_own_high_risk_content(tmp_path: Path) -> None:
    ops = store(tmp_path)
    request_id = ops.request_approval("asset-1", "alice", "HIGH", ["restricted claim"])
    with pytest.raises(PermissionError, match="APPROVAL_SELF_REVIEW"):
        ops.decide_approval(request_id, "alice", "APPROVED", "looks good")


def test_voice_rule_retains_evidence_and_conflict(tmp_path: Path) -> None:
    ops = store(tmp_path)
    profile = ops.create_voice_profile("Acme", "Direct and concise.")
    ops.add_voice_rule(profile, "tone", "direct", "Direct and concise.", conflict=True)
    page = render_workspace("voice", ops)
    assert "Direct and concise." in page
    assert "Conflict" in page
    assert "Activate profile" not in page


def test_publish_retry_only_returns_failed_channels(tmp_path: Path) -> None:
    ops = store(tmp_path)
    batch = ops.create_publish_batch("asset-1", ["linkedin", "twitter"])
    ops.record_delivery(batch, "linkedin", "PUBLISHED", "remote-1")
    ops.record_delivery(batch, "twitter", "RETRYABLE", None)
    assert ops.retryable_channels(batch) == ["twitter"]


def test_low_localization_score_blocks_bulk_approval_only_for_locale(tmp_path: Path) -> None:
    ops = store(tmp_path)
    job = ops.create_localization_job("asset-1", ["de", "fr"])
    ops.record_locale(job, "de", "Text", 0.45)
    ops.record_locale(job, "fr", "Texte", 0.92)
    assert ops.approvable_locales(job) == ["fr"]
    page = render_workspace("localization", ops)
    assert "Review required" in page and "Approved" in page


def test_provenance_export_redacts_secrets_and_keeps_human_edits(tmp_path: Path) -> None:
    ops = store(tmp_path)
    record = ops.capture_provenance("asset-1", "gpt-x", "Write {{API_KEY}}", "voice-3")
    ops.add_provenance_event(record, "HUMAN_EDIT", {"summary": "Changed headline"})
    exported = ops.export_provenance(record)
    assert "Changed headline" in exported
    assert "API_KEY" not in exported
    assert "[REDACTED]" in exported


def test_all_workspaces_have_accessible_status_and_no_false_recovery(tmp_path: Path) -> None:
    ops = store(tmp_path)
    for page in ("campaigns", "approvals", "voice", "publish", "localization", "provenance"):
        html = render_workspace(page, ops)
        assert "Skip to content" in html
        assert 'aria-live="polite"' in html
        assert "Nothing here yet" in html
        assert "The last stable state is preserved" not in html


def test_public_workspace_routes_are_registered() -> None:
    from src.main import app

    paths = set(app.openapi()["paths"])
    assert "/workspace/{page}" in paths
    assert "/api/v1/campaigns" in paths
    assert "/api/v1/approvals" in paths
    assert "/api/v1/publish-batches" in paths
    assert "/api/v1/localization-jobs" in paths
    assert "/api/v1/provenance" in paths
