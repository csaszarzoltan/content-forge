"""Content-Forge review workflow adapter (spec §3.5, P0-5).

Thin adapter over the EXISTING ContentOpsStore approval machine — the state
transitions, revision binding, stale-decision rejection and edit-after-
approval invalidation all come from the store (never rebuilt). This module
adds: review decision models, FR-15 findings gating (APPROVAL_BLOCKED),
version diff rendering via difflib, and explicit revocation (FR-17
complement).
"""

from __future__ import annotations

import difflib
import hashlib
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReviewDecision(str, Enum):
    """Review decision values — map 1:1 to ContentOpsStore approval states."""

    approved = "APPROVED"
    rejected = "REJECTED"
    needs_changes = "NEEDS_CHANGES"


class ReviewRequest(BaseModel):
    """Request to review the CURRENT revision of a draft."""

    draft_id: str
    requester: str
    risk: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    findings: list[str] = Field(default_factory=list)


class ReviewOutcome(BaseModel):
    """Result of a review decision."""

    decision_id: str
    draft_id: str
    decision: ReviewDecision
    reviewer: str
    reason: str
    version_hash: str  # sha256 of the locked approved body


class ReviewWorkflow:
    """Adapter over ContentOpsStore: request → decide → diff → versions → revoke."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def request(self, req: ReviewRequest) -> str:
        """Bind the CURRENT revision and return the request_id."""
        return self._store.request_asset_approval(
            req.draft_id, req.requester, req.risk, req.findings
        )

    def decide(
        self,
        request_id: str,
        reviewer: str,
        decision: ReviewDecision,
        reason: str,
    ) -> ReviewOutcome:
        """Record a revision-bound decision.

        FR-15: an APPROVED decision is blocked while open findings remain
        (the request's findings list is non-empty) — ValueError APPROVAL_BLOCKED.
        Blocked-term and unsupported-claim gates are wired by the caller per
        spec; this adapter enforces the findings gate deterministically.
        """
        approval = self._store._db().execute(  # noqa: SLF001 — store-internal read
            "SELECT asset_id, findings FROM approvals WHERE id=?",
            (request_id,),
        ).fetchone()
        if approval is None:
            raise KeyError(request_id)
        if decision == ReviewDecision.approved and approval["findings"]:
            findings = approval["findings"]
            import json

            try:
                open_findings = json.loads(findings)
            except (TypeError, ValueError):
                open_findings = []
            if open_findings:
                raise ValueError("APPROVAL_BLOCKED")
        self._store.decide_asset_approval(request_id, reviewer, decision.value, reason)
        asset_id = approval["asset_id"]
        asset = self._store.asset(asset_id)
        return ReviewOutcome(
            decision_id=request_id,
            draft_id=asset_id,
            decision=decision,
            reviewer=reviewer,
            reason=reason,
            version_hash=hashlib.sha256(asset["content"].encode()).hexdigest(),
        )

    def diff(self, draft_id: str, v1: int, v2: int) -> dict:
        """Unified diff between two immutable revisions.

        Returns {"v1", "v2", "unified", "added", "removed", "meta"}.
        """
        revisions = {r["version"]: r for r in self._store.revisions(draft_id)}
        if v1 not in revisions or v2 not in revisions:
            raise KeyError((draft_id, v1, v2))
        c1 = revisions[v1]["content"]
        c2 = revisions[v2]["content"]
        unified = "".join(
            difflib.unified_diff(
                c1.splitlines(),
                c2.splitlines(),
                lineterm="",
                fromfile=f"v{v1}",
                tofile=f"v{v2}",
            )
        )
        removed = [l for l in c1.splitlines() if l not in c2.splitlines()]
        added = [l for l in c2.splitlines() if l not in c1.splitlines()]
        return {
            "v1": v1,
            "v2": v2,
            "unified": unified,
            "added": added,
            "removed": removed,
            "meta": {
                "v1_author": revisions[v1]["author"],
                "v2_author": revisions[v2]["author"],
            },
        }

    def versions(self, draft_id: str) -> list[dict]:
        """Delegate to store.revisions() (newest first)."""
        return self._store.revisions(draft_id)

    def revoke(self, draft_id: str) -> None:
        """Explicit revocation: supersede any pending/approved approval so the
        asset returns to editing (FR-17 complement). No-op when nothing is
        pending/approved (asset stays IN_EDITING)."""
        db = self._store._db()  # noqa: SLF001 — store-internal mutation path
        try:
            self._store.asset(draft_id)  # KeyError when missing
            db.execute(
                "UPDATE approvals SET state='SUPERSEDED' "
                "WHERE asset_id=? AND state IN ('PENDING','APPROVED')",
                (draft_id,),
            )
            db.execute("UPDATE assets SET state='IN_EDITING' WHERE id=?", (draft_id,))
            db.commit()
        finally:
            db.close()


__all__ = ["ReviewDecision", "ReviewOutcome", "ReviewRequest", "ReviewWorkflow"]
