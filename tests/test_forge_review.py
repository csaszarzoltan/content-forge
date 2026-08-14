"""Pre-development contract tests: Content-Forge P0-5 (analysis/forge-spec.md §3.5).

Review/approval workflow + review decision + version diff — wraps the EXISTING
ContentOpsStore approval machine (MVP FR-12, FR-14, FR-15, FR-16, FR-17; US-003).

Target package: src/forge/review.py (spec §3.5; commit 9c8cd2b / fd0b99f).
Reuse (do NOT rebuild): ContentOpsStore.request_asset_approval,
decide_asset_approval (revision-bound, stale-decision APPROVAL_REVISION_STALE,
SUPERSEDED on edit-after-approval), save_revision, audit_events — pinned by
tests/test_approval_workflow_v012.py.

Suite layout (three layers, repo convention):
  1. Spec-contract guards  -- GREEN now. Pin the committed spec §3.5 so
     signature drift in the contract source of truth fails loudly.
  2. Interface tests       -- SKIP while src/forge is absent (no stubs
     permitted). Pure contract pins (imports + exact signatures/defaults) that
     must pass immediately once the developer creates the module.
  3. Behavioral tests      -- RED until implementation (assert-based; the
     P0-5 expectations may partly pass already because ContentOpsStore exists
     and the spec expects the adapter to reuse it — that pins existing
     behavior). Imports live inside each test so the failure is a clean
     per-test ModuleNotFoundError, not a collection error.

Expectations are behavioral (assert-based), NOT pytest.raises(NotImplementedError)
stub-guards.
"""

from __future__ import annotations

import hashlib
import inspect
from enum import Enum
from pathlib import Path

import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_SECTION = REPO_ROOT / "analysis" / "forge-spec.md"

# Capability probe: no stubs are permitted by this task, so the forge package
# does not exist yet. Interface tests skip until the developer creates it;
# behavioral tests fail with ModuleNotFoundError (the intended RED signal).
HAS_FORGE = False
try:
    from forge.review import (  # noqa: F401
        ReviewDecision,
        ReviewOutcome,
        ReviewRequest,
        ReviewWorkflow,
    )

    HAS_FORGE = True
except ImportError:
    pass

requires_forge = pytest.mark.skipif(
    not HAS_FORGE,
    reason="RED phase: src/forge package does not exist yet (no stubs permitted)",
)

# ── Shared fixture helpers ──────────────────────────────────────────────────


def _store_and_asset(tmp_path: Path) -> tuple:
    """Fresh ContentOpsStore with one approved-v1 asset (spec §3.5 flow)."""
    from src.product_ops import ContentOpsStore

    store = ContentOpsStore(tmp_path / "ops.db")
    campaign = store.create_campaign("Launch", ["linkedin"], brief="Safe approval")
    asset = store.create_asset(campaign, "linkedin", "Draft v1", "Launch post", author="alice")
    return store, asset


# ---------------------------------------------------------------------------
# Layer 1 -- spec-contract guards (GREEN now; pin the committed spec)
# ---------------------------------------------------------------------------


def test_spec_guard_p0_5_files_declared():
    text = SPEC_SECTION.read_text()
    for line in ("src/forge/review.py", "src/forge/review_schemas.py"):
        assert line in text, f"spec §3.5 must declare {line}"


def test_spec_guard_review_classes_declared():
    text = SPEC_SECTION.read_text()
    for line in (
        "class ReviewDecision(str, Enum):",
        "class ReviewRequest(BaseModel):",
        "class ReviewOutcome(BaseModel):",
        "class ReviewWorkflow:",
    ):
        assert line in text, f"spec §3.5 must declare {line}"


def test_spec_guard_review_method_signatures():
    text = SPEC_SECTION.read_text()
    for line in (
        "def __init__(self, store: ContentOpsStore) -> None",
        "def request(self, req: ReviewRequest) -> str",
        "def decide(self, request_id: str, reviewer: str, decision: ReviewDecision, reason: str) -> ReviewOutcome",
        'def diff(self, draft_id: str, v1: int, v2: int) -> dict:',
        "def versions(self, draft_id: str) -> list[dict]",
        "def revoke(self, draft_id: str) -> None",
    ):
        assert line in text, f"spec §3.5 must declare {line}"


def test_spec_guard_review_invariants():
    text = SPEC_SECTION.read_text()
    for invariant in ("APPROVAL_BLOCKED", "APPROVAL_REVISION_STALE", "SUPERSEDED"):
        assert invariant in text, f"spec §3.5 must mention {invariant}"


# ---------------------------------------------------------------------------
# Layer 2 -- interface tests (imports + exact signatures; SKIP until forge exists)
# ---------------------------------------------------------------------------


@requires_forge
def test_interface_review_decision_enum_members():
    from forge.review import ReviewDecision

    assert ReviewDecision.approved.value == "APPROVED"
    assert ReviewDecision.rejected.value == "REJECTED"
    assert ReviewDecision.needs_changes.value == "NEEDS_CHANGES"
    assert issubclass(ReviewDecision, str)
    assert issubclass(ReviewDecision, Enum)


@requires_forge
def test_interface_review_request_fields_and_defaults():
    from forge.review import ReviewRequest

    for field in ("draft_id", "requester", "risk", "findings"):
        assert field in ReviewRequest.model_fields

    req = ReviewRequest(draft_id="d1", requester="alice")
    assert req.risk == "MEDIUM"
    assert req.findings == []

    req_high = ReviewRequest(draft_id="d1", requester="alice", risk="HIGH")
    assert req_high.risk == "HIGH"

    with pytest.raises(ValidationError):
        ReviewRequest(draft_id="d1", requester="alice", risk="URGENT")  # Literal


@requires_forge
def test_interface_review_outcome_fields():
    from forge.review import ReviewOutcome

    for field in (
        "decision_id",
        "draft_id",
        "decision",
        "reviewer",
        "reason",
        "version_hash",
    ):
        assert field in ReviewOutcome.model_fields


@requires_forge
def test_interface_review_workflow_signatures():
    from forge.review import ReviewWorkflow

    init_sig = inspect.signature(ReviewWorkflow.__init__)
    assert list(init_sig.parameters) == ["self", "store"]

    req_sig = inspect.signature(ReviewWorkflow.request)
    assert list(req_sig.parameters) == ["self", "req"]

    decide_sig = inspect.signature(ReviewWorkflow.decide)
    assert list(decide_sig.parameters) == [
        "self",
        "request_id",
        "reviewer",
        "decision",
        "reason",
    ]

    diff_sig = inspect.signature(ReviewWorkflow.diff)
    assert list(diff_sig.parameters) == ["self", "draft_id", "v1", "v2"]

    versions_sig = inspect.signature(ReviewWorkflow.versions)
    assert list(versions_sig.parameters) == ["self", "draft_id"]

    revoke_sig = inspect.signature(ReviewWorkflow.revoke)
    assert list(revoke_sig.parameters) == ["self", "draft_id"]


@requires_forge
def test_interface_review_workflow_accepts_contentops_store(tmp_path):
    from forge.review import ReviewWorkflow

    from src.product_ops import ContentOpsStore

    store = ContentOpsStore(tmp_path / "ops.db")
    wf = ReviewWorkflow(store=store)
    assert isinstance(wf, ReviewWorkflow)


# ---------------------------------------------------------------------------
# Layer 3 -- behavioral tests (RED until implementation; P0-5 reuses the store)
# ---------------------------------------------------------------------------


def test_behavior_spec_expectation_flow(tmp_path):
    """Mirrors the §3.5 expectation block verbatim.

    request binds current revision -> approve locks version_hash = sha256(body)
    -> state APPROVED -> edit invalidates approval (IN_EDITING, FR-17) ->
    diff v1..v2 -> versions == 2 -> FR-15 blocks decide while findings open.
    """
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)

    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice"))
    out = wf.decide(rid, reviewer="bob", decision=ReviewDecision.approved, reason="OK")
    assert out.decision == ReviewDecision.approved
    assert out.version_hash == hashlib.sha256(b"Draft v1").hexdigest()
    assert store.asset(asset)["state"] == "APPROVED"

    store.save_revision(asset, "Draft v2", expected_version=1, author="alice")
    assert store.asset(asset)["state"] == "IN_EDITING"  # FR-17: edit invalidates approval

    d = wf.diff(asset, 1, 2)
    assert "Draft v1" in d["unified"] and "Draft v2" in d["unified"]
    assert len(wf.versions(asset)) == 2

    # FR-15: decision blocked while findings remain open
    rid2 = wf.request(ReviewRequest(draft_id=asset, requester="alice", findings=["Fix CTA"]))
    with pytest.raises(ValueError, match="APPROVAL_BLOCKED"):
        wf.decide(rid2, reviewer="bob", decision=ReviewDecision.approved, reason="x")


def test_behavior_decision_outcome_shape(tmp_path):
    """ReviewOutcome carries decision_id, draft_id, reviewer, reason + hash."""
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice"))
    out = wf.decide(rid, reviewer="bob", decision=ReviewDecision.approved, reason="OK")

    assert out.decision_id == rid
    assert out.draft_id == asset
    assert out.reviewer == "bob"
    assert out.reason == "OK"
    assert out.decision is ReviewDecision.approved


def test_behavior_request_binds_current_revision(tmp_path):
    """request() binds the CURRENT revision; later save bumps the asset."""
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice"))
    out = wf.decide(rid, reviewer="bob", decision=ReviewDecision.approved, reason="OK")
    # locked hash is of the revision bound at request time
    assert out.version_hash == hashlib.sha256(b"Draft v1").hexdigest()
    assert store.asset(asset)["state"] == "APPROVED"


def test_behavior_rejected_returns_asset_to_editing(tmp_path):
    """REJECTED decision -> asset IN_EDITING (store machine contract)."""
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice"))
    out = wf.decide(rid, reviewer="bob", decision=ReviewDecision.rejected, reason="Off-brand")
    assert out.decision is ReviewDecision.rejected
    assert store.asset(asset)["state"] == "IN_EDITING"


def test_behavior_needs_changes_returns_asset_to_editing(tmp_path):
    """NEEDS_CHANGES decision -> asset IN_EDITING (store machine contract)."""
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice", findings=["Tone"]))
    out = wf.decide(
        rid, reviewer="bob", decision=ReviewDecision.needs_changes, reason="Tighten CTA"
    )
    assert out.decision is ReviewDecision.needs_changes
    assert store.asset(asset)["state"] == "IN_EDITING"


def test_behavior_stale_decision_rejected(tmp_path):
    """Deciding an approval whose revision moved on raises (store contract)."""
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice"))
    store.save_revision(asset, "Draft v2", expected_version=1, author="alice")
    with pytest.raises(ValueError, match="APPROVAL_REVISION_STALE"):
        wf.decide(rid, reviewer="bob", decision=ReviewDecision.approved, reason="old copy")


def test_behavior_findings_require_changes_block_approval(tmp_path):
    """FR-15: an APPROVED decision is blocked while findings remain open."""
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice", findings=["Fix CTA"]))
    with pytest.raises(ValueError, match="APPROVAL_BLOCKED"):
        wf.decide(rid, reviewer="bob", decision=ReviewDecision.approved, reason="x")


def test_behavior_no_findings_allows_approval(tmp_path):
    """Empty findings -> approval proceeds (FR-15 complement)."""
    from forge.review import ReviewDecision, ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    rid = wf.request(ReviewRequest(draft_id=asset, requester="alice", findings=[]))
    out = wf.decide(rid, reviewer="bob", decision=ReviewDecision.approved, reason="x")
    assert out.decision is ReviewDecision.approved


def test_behavior_diff_shape(tmp_path):
    """diff returns {v1, v2, unified, added, removed, meta}."""
    from forge.review import ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    store.save_revision(asset, "Draft v2", expected_version=1, author="alice")
    wf = ReviewWorkflow(store)
    d = wf.diff(asset, 1, 2)
    assert set(d.keys()) == {"v1", "v2", "unified", "added", "removed", "meta"}
    assert d["v1"] == 1
    assert d["v2"] == 2
    assert isinstance(d["unified"], str)
    assert isinstance(d["added"], list)
    assert isinstance(d["removed"], list)
    assert isinstance(d["meta"], dict)


def test_behavior_diff_unified_and_added_removed(tmp_path):
    """unified diff contains both bodies; added/removed are the changed lines."""
    from forge.review import ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    store.save_revision(asset, "Draft v2", expected_version=1, author="alice")
    wf = ReviewWorkflow(store)
    d = wf.diff(asset, 1, 2)
    assert "Draft v1" in d["unified"]
    assert "Draft v2" in d["unified"]
    assert "Draft v1" in d["removed"]
    assert "Draft v2" in d["added"]


def test_behavior_diff_uses_difflib_unified_diff(tmp_path):
    """unified is produced by difflib.unified_diff (spec §3.5)."""
    import difflib

    from forge.review import ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    store.save_revision(asset, "Draft v2", expected_version=1, author="alice")
    wf = ReviewWorkflow(store)
    d = wf.diff(asset, 1, 2)
    expected = "".join(
        difflib.unified_diff(
            ["Draft v1"], ["Draft v2"], lineterm="", fromfile="v1", tofile="v2"
        )
    )
    assert d["unified"].strip() == expected.strip()


def test_behavior_versions_delegates_to_store(tmp_path):
    """versions() returns store.revisions() — newest first, 2 revisions."""
    from forge.review import ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    store.save_revision(asset, "Draft v2", expected_version=1, author="alice")
    wf = ReviewWorkflow(store)
    versions = wf.versions(asset)
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[1]["version"] == 1
    assert versions[0]["content"] == "Draft v2"


def test_behavior_revoke_returns_asset_to_editing(tmp_path):
    """revoke() is the FR-17 complement: explicit revocation reopens editing."""
    from forge.review import ReviewRequest, ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    wf.request(ReviewRequest(draft_id=asset, requester="alice"))
    wf.revoke(asset)
    assert store.asset(asset)["state"] == "IN_EDITING"


def test_behavior_revoke_without_pending_request_is_noop(tmp_path):
    """revoke() on an asset with no pending/approved approval stays IN_EDITING."""
    from forge.review import ReviewWorkflow

    store, asset = _store_and_asset(tmp_path)
    wf = ReviewWorkflow(store)
    wf.revoke(asset)
    assert store.asset(asset)["state"] == "IN_EDITING"
