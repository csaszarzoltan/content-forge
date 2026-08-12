"""US-010..US-018 completion contracts using real SQLite I/O."""

from pathlib import Path

import pytest

from src.family.store import FamilyStore, PermissionDenied


def seeded(tmp_path: Path):
    s = FamilyStore(tmp_path / "f.db")
    w = s.create_workspace("u1", "Parent", "Studio", "FAMILY_CREATOR", "key-0000000000001")[
        "workspace"
    ]["id"]
    return s, w


def test_us_010_invite_preview_revoke(tmp_path):
    s, w = seeded(tmp_path)
    i = s.create_invitation(w, "u1", "teen@example.com", "TEEN_CONTRIBUTOR")
    p = s.invitation_preview(i["token"])
    assert p["workspace_name"] == "Studio" and "email" not in p
    s.revoke_invitation(w, "u1", i["id"])
    with pytest.raises(ValueError, match="invitation_revoked"):
        s.accept_invitation(i["token"], "u2", "teen@example.com")


def test_us_011_email_bound_accept(tmp_path):
    s, w = seeded(tmp_path)
    i = s.create_invitation(w, "u1", "teen@example.com", "TEEN_CONTRIBUTOR")
    with pytest.raises(PermissionDenied):
        s.accept_invitation(i["token"], "u2", "other@example.com")
    assert s.accept_invitation(i["token"], "u2", "teen@example.com")["role"] == "TEEN_CONTRIBUTOR"


def test_us_012_last_owner_and_member_roles(tmp_path):
    s, w = seeded(tmp_path)
    i = s.create_invitation(w, "u1", "adult@example.com", "ADULT_COLLABORATOR")
    m = s.accept_invitation(i["token"], "u2", "adult@example.com")
    s.update_member(w, "u1", m["id"], "ADULT_OWNER")
    s.update_member(w, "u2", s.membership(w, "u1")["id"], "ADULT_COLLABORATOR")
    with pytest.raises(ValueError, match="last_owner_required"):
        s.remove_member(w, "u2", m["id"])


def test_us_013_asset_autosave_and_conflict(tmp_path):
    s, w = seeded(tmp_path)
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "A complete weekly family message",
            "channels": ["linkedin"],
        },
        "j-key-0000000001",
    )["assets"][0]
    assert s.asset_detail(w, "u1", a["id"])["version"] == 1
    assert s.save_revision(w, "u1", a["id"], "Updated family message", 1)["version"] == 2
    with pytest.raises(ValueError, match="asset_version_conflict"):
        s.save_revision(w, "u1", a["id"], "stale", 1)


def test_us_014_exact_review_is_idempotent(tmp_path):
    s, w = seeded(tmp_path)
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "A complete weekly family message",
            "channels": ["linkedin"],
        },
        "j-key-0000000001",
    )["assets"][0]
    x = s.submit_review(w, "u1", a["id"], "check")
    y = s.submit_review(w, "u1", a["id"], "check")
    assert x["id"] == y["id"]


def test_us_015_review_diff_and_stale(tmp_path):
    s, w = seeded(tmp_path)
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "Original weekly family message",
            "channels": ["linkedin"],
        },
        "j-key-0000000001",
    )["assets"][0]
    s.save_revision(w, "u1", a["id"], "Updated weekly family message", 1)
    r = s.submit_review(w, "u1", a["id"], "check")
    d = s.review_detail(w, "u1", r["id"])
    assert any(x["kind"] in {"added", "removed"} for x in d["diff"])
    s.save_revision(w, "u1", a["id"], "Third family message", 2)
    assert s.review_detail(w, "u1", r["id"])["state"] == "SUPERSEDED"


def test_us_016_publish_eligibility_and_idempotency(tmp_path):
    s, w = seeded(tmp_path)
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "A complete weekly family message",
            "channels": ["linkedin"],
        },
        "j-key-0000000001",
    )["assets"][0]
    r = s.submit_review(w, "u1", a["id"], "check")
    s.decide_review(w, "u1", r["id"], "APPROVED", "approved")
    assert s.publish_eligibility(w, "u1", a["id"])["eligible"] is True
    x = s.publish(w, "u1", a["id"], 1, ["linkedin"], "p-key-000000001")
    y = s.publish(w, "u1", a["id"], 1, ["linkedin"], "p-key-000000001")
    assert x["id"] == y["id"]


def test_us_017_selective_retry(tmp_path):
    s, w = seeded(tmp_path)
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "A complete weekly family message",
            "channels": ["linkedin", "twitter"],
        },
        "j-key-0000000001",
    )["assets"][0]
    r = s.submit_review(w, "u1", a["id"], "check")
    s.decide_review(w, "u1", r["id"], "APPROVED", "approved")
    b = s.publish(w, "u1", a["id"], 1, ["linkedin", "twitter"], "p-key-000000001")
    s.set_delivery_state(b["id"], "twitter", "RETRYABLE", "temporary")
    out = s.retry_publish(w, "u1", b["id"])
    assert out["retried"] == ["twitter"]
    assert (
        next(
            x
            for x in s.publish_result(w, "u1", b["id"])["deliveries"]
            if x["channel"] == "linkedin"
        )["attempt_count"]
        == 1
    )


def test_us_018_unknown_must_reconcile(tmp_path):
    s, w = seeded(tmp_path)
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "A complete weekly family message",
            "channels": ["linkedin"],
        },
        "j-key-0000000001",
    )["assets"][0]
    r = s.submit_review(w, "u1", a["id"], "check")
    s.decide_review(w, "u1", r["id"], "APPROVED", "approved")
    b = s.publish(w, "u1", a["id"], 1, ["linkedin"], "p-key-000000001")
    s.set_delivery_state(b["id"], "linkedin", "UNKNOWN", "provider timeout")
    with pytest.raises(ValueError, match="reconciliation_required"):
        s.retry_publish(w, "u1", b["id"])
    assert s.reconcile_publish(w, "u1", b["id"])["state"] == "FAILED"


def test_paid_release_publish_batch_starts_queued_and_never_claims_fake_success(tmp_path):
    s, w = seeded(tmp_path)
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "A complete weekly family message",
            "channels": ["linkedin"],
        },
        "j-key-real-publish",
    )["assets"][0]
    r = s.submit_review(w, "u1", a["id"], "check")
    s.decide_review(w, "u1", r["id"], "APPROVED", "approved")
    b = s.prepare_publish_batch(w, "u1", a["id"], 1, ["linkedin"], "provider-key-1")
    assert b["state"] == "QUEUED"
    s.complete_delivery(b["id"], "linkedin", "FAILED", error_code="connection_required")
    result = s.publish_result(w, "u1", b["id"])
    assert (
        result["state"] == "FAILED"
        and result["deliveries"][0]["error_code"] == "connection_required"
    )


def test_weekly_summary_reports_family_outcomes(tmp_path):
    s, w = seeded(tmp_path)
    out = s.weekly_summary(w, "u1")
    assert out["projects_started"] == 0 and "This week your family" in out["message"]
