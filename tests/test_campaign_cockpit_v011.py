"""TDD contract for the v0.11 campaign cockpit vertical slice."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.product_ops import ContentOpsStore


def test_campaign_brief_is_persisted_and_returned(tmp_path: Path) -> None:
    store = ContentOpsStore(tmp_path / "ops.db")
    campaign_id = store.create_campaign("Autumn launch", ["linkedin"], brief="Launch in DACH")
    assert store.campaign(campaign_id)["brief"] == "Launch in DACH"


def test_asset_revision_autosave_uses_optimistic_version(tmp_path: Path) -> None:
    store = ContentOpsStore(tmp_path / "ops.db")
    campaign_id = store.create_campaign("Launch", ["linkedin"], brief="Brief")
    asset_id = store.create_asset(campaign_id, "linkedin", "Draft", "Launch post")
    first = store.save_revision(asset_id, "Draft two", expected_version=1, author="anna")
    assert first["version"] == 2
    assert first["content"] == "Draft two"
    with pytest.raises(ValueError, match="ASSET_VERSION_CONFLICT"):
        store.save_revision(asset_id, "Stale edit", expected_version=1, author="bob")


def test_revision_history_and_restore_are_append_only(tmp_path: Path) -> None:
    store = ContentOpsStore(tmp_path / "ops.db")
    campaign_id = store.create_campaign("Launch", ["linkedin"], brief="Brief")
    asset_id = store.create_asset(campaign_id, "linkedin", "v1", "Post")
    store.save_revision(asset_id, "v2", expected_version=1, author="anna")
    restored = store.restore_revision(asset_id, version=1, expected_version=2, author="anna")
    assert restored["version"] == 3
    assert restored["content"] == "v1"
    assert [row["version"] for row in store.revisions(asset_id)] == [3, 2, 1]


def test_readiness_explains_blockers(tmp_path: Path) -> None:
    store = ContentOpsStore(tmp_path / "ops.db")
    campaign_id = store.create_campaign("Launch", ["linkedin", "x"], brief="Brief")
    store.create_asset(campaign_id, "linkedin", "Approved post", "LinkedIn", state="APPROVED")
    readiness = store.campaign_readiness(campaign_id)
    assert readiness["score"] == 50
    assert readiness["ready_channels"] == ["linkedin"]
    assert readiness["blockers"] == ["Create an approved asset for x"]


def test_my_work_contains_actionable_approval_and_publish_items(tmp_path: Path) -> None:
    store = ContentOpsStore(tmp_path / "ops.db")
    campaign_id = store.create_campaign("Launch", ["linkedin"], brief="Brief")
    asset_id = store.create_asset(campaign_id, "linkedin", "Copy", "Post")
    approval_id = store.request_approval(asset_id, "alice", "HIGH", ["Legal claim"])
    batch_id = store.create_publish_batch(asset_id, ["linkedin"])
    store.record_delivery(batch_id, "linkedin", "FAILED", None)
    items = store.my_work()
    assert any(item["kind"] == "approval" and item["id"] == approval_id for item in items)
    assert any(item["kind"] == "publish_failure" and item["id"] == batch_id for item in items)


def test_cockpit_real_io_survives_store_reopen(tmp_path: Path) -> None:
    database = tmp_path / "ops.db"
    campaign_id = ContentOpsStore(database).create_campaign("Persistent", ["x"], brief="Keep me")
    reopened = ContentOpsStore(database)
    assert reopened.campaign(campaign_id)["name"] == "Persistent"
    assert reopened.campaign_readiness(campaign_id)["score"] == 0
