"""TDD coverage for revision-bound approval and audit workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.product_ops import ContentOpsStore


def prepared_asset(tmp_path: Path) -> tuple[ContentOpsStore, str]:
    store = ContentOpsStore(tmp_path / "ops.db")
    campaign = store.create_campaign("Launch", ["linkedin"], brief="Safe approval")
    asset = store.create_asset(campaign, "linkedin", "Draft", "Launch post", author="alice")
    return store, asset


def test_request_review_binds_current_revision_and_updates_asset(tmp_path: Path) -> None:
    store, asset = prepared_asset(tmp_path)
    request_id = store.request_asset_approval(asset, "alice", "MEDIUM", ["Check CTA"])
    request = store.approval(request_id)
    assert request["revision_version"] == 1
    assert request["state"] == "PENDING"
    assert store.asset(asset)["state"] == "WAITING_APPROVAL"


def test_approval_marks_same_revision_approved(tmp_path: Path) -> None:
    store, asset = prepared_asset(tmp_path)
    request_id = store.request_asset_approval(asset, "alice", "LOW", [])
    store.decide_asset_approval(request_id, "bob", "APPROVED", "Ready")
    assert store.asset(asset)["state"] == "APPROVED"
    assert store.approval(request_id)["reviewer"] == "bob"


def test_edit_after_approval_invalidates_publish_readiness(tmp_path: Path) -> None:
    store, asset = prepared_asset(tmp_path)
    request_id = store.request_asset_approval(asset, "alice", "LOW", [])
    store.decide_asset_approval(request_id, "bob", "APPROVED", "Ready")
    store.save_revision(asset, "Changed after approval", expected_version=1, author="alice")
    assert store.asset(asset)["state"] == "IN_EDITING"
    assert store.approval(request_id)["state"] == "SUPERSEDED"


def test_stale_approval_decision_is_rejected(tmp_path: Path) -> None:
    store, asset = prepared_asset(tmp_path)
    request_id = store.request_asset_approval(asset, "alice", "LOW", [])
    store.save_revision(asset, "New version", expected_version=1, author="alice")
    with pytest.raises(ValueError, match="APPROVAL_REVISION_STALE"):
        store.decide_asset_approval(request_id, "bob", "APPROVED", "Old copy")


def test_request_changes_returns_asset_to_editing(tmp_path: Path) -> None:
    store, asset = prepared_asset(tmp_path)
    request_id = store.request_asset_approval(asset, "alice", "HIGH", ["Claim"])
    store.decide_asset_approval(request_id, "legal", "NEEDS_CHANGES", "Add source")
    assert store.asset(asset)["state"] == "IN_EDITING"


def test_audit_history_records_review_lifecycle(tmp_path: Path) -> None:
    store, asset = prepared_asset(tmp_path)
    request_id = store.request_asset_approval(asset, "alice", "LOW", [])
    store.decide_asset_approval(request_id, "bob", "APPROVED", "Ready")
    events = store.audit_events(asset)
    assert [event["kind"] for event in events][-2:] == ["APPROVAL_REQUESTED", "APPROVAL_DECIDED"]
    assert all(event["payload"] for event in events)
