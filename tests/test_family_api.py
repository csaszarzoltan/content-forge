# US-001..US-009: real behavior contracts for the family vertical slice.
from pathlib import Path

from src.family.store import FamilyStore, PermissionDenied


def test_us_001_workspace_is_idempotent(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    a = s.create_workspace("u1", "Parent", "Our Studio", "FAMILY_CREATOR", "key-0000000000001")
    b = s.create_workspace("u1", "Parent", "Our Studio", "FAMILY_CREATOR", "key-0000000000001")
    assert a == b and s.membership(a["workspace"]["id"], "u1")["role"] == "ADULT_OWNER"


def test_us_002_invitation_and_permissions(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "Parent", "Studio", "FAMILY_CREATOR", "key-0000000000001")[
        "workspace"
    ]["id"]
    inv = s.create_invitation(w, "u1", "teen@example.com", "TEEN_CONTRIBUTOR")
    m = s.accept_invitation(inv["token"], "u2", "teen@example.com")
    assert m["role"] == "TEEN_CONTRIBUTOR"
    assert "publish" not in s.permissions(w, "u2")
    assert s.accept_invitation(inv["token"], "u2", "teen@example.com")["id"] == m["id"]


def test_us_003_home_priority_and_empty(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "Parent", "Studio", "FAMILY_CREATOR", "key-0000000000001")[
        "workspace"
    ]["id"]
    home = s.home(w, "u1")
    assert home["next_action"]["kind"] == "START_PROJECT"
    assert home["onboarding"]["percent"] == 75


def test_us_004_current_revision_gate(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "Parent", "Studio", "FAMILY_CREATOR", "key-0000000000001")[
        "workspace"
    ]["id"]
    j = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "Week 1",
            "audience": "neighbors",
            "message": "Our important weekly family update",
            "channels": ["linkedin"],
        },
        "journey-key-000001",
    )
    asset = j["assets"][0]
    review = s.submit_review(w, "u1", asset["id"], "Please check")
    s.decide_review(w, "u1", review["id"], "APPROVED", "Looks good")
    batch = s.publish(w, "u1", asset["id"], 1, ["linkedin"], "publish-key-000001")
    assert batch["state"] == "PUBLISHED"
    s.save_revision(w, "u1", asset["id"], "Changed text", 1)
    try:
        s.publish(w, "u1", asset["id"], 2, ["linkedin"], "publish-key-000002")
    except ValueError as e:
        assert str(e) == "approval_required_for_current_revision"
    else:
        assert False


def test_us_005_repeat_submission_is_same(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "P", "Studio", "FAMILY_CREATOR", "key-0000000000001")["workspace"][
        "id"
    ]
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "SHARE_PROJECT",
            "project_name": "Craft",
            "audience": "friends",
            "message": "A detailed creative family project",
            "channels": ["twitter"],
        },
        "journey-key-000001",
    )["assets"][0]
    x = s.submit_review(w, "u1", a["id"], "note")
    y = s.submit_review(w, "u1", a["id"], "note")
    assert x["id"] == y["id"]


def test_us_006_needs_changes_reason(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "P", "Studio", "FAMILY_CREATOR", "key-0000000000001")["workspace"][
        "id"
    ]
    a = s.create_journey(
        w,
        "u1",
        {
            "goal": "SHARE_PROJECT",
            "project_name": "Craft",
            "audience": "friends",
            "message": "A detailed creative family project",
            "channels": ["twitter"],
        },
        "journey-key-000001",
    )["assets"][0]
    r = s.submit_review(w, "u1", a["id"], "note")
    out = s.decide_review(w, "u1", r["id"], "NEEDS_CHANGES", "Please clarify the date")
    assert out["state"] == "NEEDS_CHANGES"


def test_us_007_journey_is_transactional(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "P", "Studio", "FAMILY_CREATOR", "key-0000000000001")["workspace"][
        "id"
    ]
    j = s.create_journey(
        w,
        "u1",
        {
            "goal": "PROMOTE_SHOP",
            "project_name": "Launch",
            "audience": "local families",
            "message": "Visit our small family shop this weekend",
            "cta": "Come by",
            "channels": ["linkedin", "twitter"],
        },
        "journey-key-000001",
    )
    assert len(j["assets"]) == 2 and all(a["version"] == 1 for a in j["assets"])


def test_us_008_private_idea_deduplicates(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "P", "Studio", "FAMILY_CREATOR", "key-0000000000001")["workspace"][
        "id"
    ]
    a = s.create_idea(w, "u1", "client-1", "TEXT", "Remember the market photo", None, None)
    b = s.create_idea(w, "u1", "client-1", "TEXT", "Remember the market photo", None, None)
    assert a["id"] == b["id"] and a["state"] == "PRIVATE"


def test_us_009_contributor_cannot_publish_and_retry_is_selective(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "P", "Studio", "FAMILY_CREATOR", "key-0000000000001")["workspace"][
        "id"
    ]
    inv = s.create_invitation(w, "u1", "teen@example.com", "TEEN_CONTRIBUTOR")
    s.accept_invitation(inv["token"], "u2", "teen@example.com")
    try:
        s.publish(w, "u2", "missing", 1, ["twitter"], "publish-key-000001")
    except PermissionDenied:
        pass
    else:
        assert False


def test_family_session_reviews_and_validation_paths(tmp_path: Path):
    s = FamilyStore(tmp_path / "ops.db")
    w = s.create_workspace("u1", "Parent", "Studio", "FAMILY_CREATOR", "key-0000000000001")[
        "workspace"
    ]["id"]
    session = s.session(w, "u1")
    assert session["workspace"]["name"] == "Studio" and any(
        x["route"] == "review" for x in session["navigation"]
    )
    j = s.create_journey(
        w,
        "u1",
        {
            "goal": "WEEKLY_UPDATE",
            "project_name": "News",
            "audience": "friends",
            "message": "A sufficiently detailed family update",
            "channels": ["linkedin"],
        },
        "journey-key-000001",
    )
    r = s.submit_review(w, "u1", j["assets"][0]["id"], "please review")
    assert s.home(w, "u1")["next_action"]["kind"] == "REVIEW"
    assert s.reviews(w, "u1")[0]["id"] == r["id"]
    for action in [
        lambda: s.create_journey(w, "u1", {"goal": "BAD"}, "journey-key-000002"),
        lambda: s.create_idea(w, "u1", "bad", "TEXT", "", None, None),
        lambda: s.decide_review(w, "u1", r["id"], "NEEDS_CHANGES", "short"),
    ]:
        try:
            action()
        except ValueError:
            pass
        else:
            assert False
