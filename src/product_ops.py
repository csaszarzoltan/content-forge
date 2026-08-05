"""Workflow domain and accessible HTML views for ContentForge product workspaces.

The module has no web-framework dependency. SQLite persistence and pure rendering
keep the workflow rules deterministic and independently testable.
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

PAGES = {
    "campaigns": ("Campaign workspace", "Plan, generate, review, and schedule channel assets."),
    "approvals": ("Approval inbox", "Review brand, compliance, and publishing risk in one queue."),
    "voice": ("Brand voice studio", "Turn evidence into editable, versioned voice rules."),
    "publish": ("Publish center", "Preview every channel and recover without duplicate posts."),
    "localization": (
        "Localization QA",
        "Review meaning, terminology, voice, and channel fit by locale.",
    ),
    "provenance": ("Trust & audit", "Trace model output, human edits, approval, and publication."),
}

# Static per-table SELECTs for ContentOpsStore.rows(). Table names are allowlisted
# (see rows()) and never interpolated into SQL, so the queries stay literal strings.
_TABLE_SELECTS = {
    "campaigns": "SELECT * FROM campaigns ORDER BY rowid DESC",
    "approvals": "SELECT * FROM approvals ORDER BY rowid DESC",
    "voice_profiles": "SELECT * FROM voice_profiles ORDER BY rowid DESC",
    "voice_rules": "SELECT * FROM voice_rules ORDER BY rowid DESC",
    "publish_batches": "SELECT * FROM publish_batches ORDER BY rowid DESC",
    "deliveries": "SELECT * FROM deliveries ORDER BY rowid DESC",
    "localization_jobs": "SELECT * FROM localization_jobs ORDER BY rowid DESC",
    "locale_variants": "SELECT * FROM locale_variants ORDER BY rowid DESC",
    "provenance": "SELECT * FROM provenance ORDER BY rowid DESC",
}


class ContentOpsStore:
    """Persist campaign operations with explicit workflow invariants."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,name TEXT,state TEXT,channels TEXT);
                CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,campaign_id TEXT,channel TEXT,content TEXT,state TEXT);
                CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY,asset_id TEXT,requester TEXT,risk TEXT,findings TEXT,state TEXT,reviewer TEXT,reason TEXT);
                CREATE TABLE IF NOT EXISTS voice_profiles(id TEXT PRIMARY KEY,name TEXT,source TEXT,state TEXT);
                CREATE TABLE IF NOT EXISTS voice_rules(id TEXT PRIMARY KEY,profile_id TEXT,kind TEXT,value TEXT,evidence TEXT,state TEXT);
                CREATE TABLE IF NOT EXISTS publish_batches(id TEXT PRIMARY KEY,asset_id TEXT,state TEXT,channels TEXT);
                CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY,batch_id TEXT,channel TEXT,state TEXT,remote_id TEXT,UNIQUE(batch_id,channel));
                CREATE TABLE IF NOT EXISTS localization_jobs(id TEXT PRIMARY KEY,asset_id TEXT,state TEXT,locales TEXT);
                CREATE TABLE IF NOT EXISTS locale_variants(id TEXT PRIMARY KEY,job_id TEXT,locale TEXT,content TEXT,score REAL,state TEXT,UNIQUE(job_id,locale));
                CREATE TABLE IF NOT EXISTS provenance(id TEXT PRIMARY KEY,asset_id TEXT,model TEXT,prompt TEXT,voice_version TEXT,state TEXT,created_at REAL);
                CREATE TABLE IF NOT EXISTS provenance_events(id TEXT PRIMARY KEY,record_id TEXT,kind TEXT,payload TEXT,created_at REAL);
                CREATE TABLE IF NOT EXISTS asset_revisions(id TEXT PRIMARY KEY,asset_id TEXT,version INTEGER,content TEXT,author TEXT,created_at REAL,UNIQUE(asset_id,version));
                """
            )
            campaign_columns = {row[1] for row in db.execute("PRAGMA table_info(campaigns)")}
            if "brief" not in campaign_columns:
                db.execute("ALTER TABLE campaigns ADD COLUMN brief TEXT NOT NULL DEFAULT ''")
            asset_columns = {row[1] for row in db.execute("PRAGMA table_info(assets)")}
            if "title" not in asset_columns:
                db.execute("ALTER TABLE assets ADD COLUMN title TEXT NOT NULL DEFAULT ''")
            if "version" not in asset_columns:
                db.execute("ALTER TABLE assets ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
            approval_columns = {row[1] for row in db.execute("PRAGMA table_info(approvals)")}
            if "revision_version" not in approval_columns:
                db.execute("ALTER TABLE approvals ADD COLUMN revision_version INTEGER")
            db.execute(
                "CREATE TABLE IF NOT EXISTS audit_events("
                "id TEXT PRIMARY KEY,entity_id TEXT,kind TEXT,payload TEXT,created_at REAL)"
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _id() -> str:
        return uuid.uuid4().hex

    def create_campaign(self, name: str, channels: list[str], brief: str = "") -> str:
        """Create a campaign with a durable brief and normalized channels."""
        clean = sorted({x.strip() for x in channels if x.strip()})
        if not name.strip() or not clean:
            raise ValueError("CAMPAIGN_INPUT_INVALID")
        campaign_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO campaigns(id,name,state,channels,brief) VALUES (?,?,?,?,?)",
                (campaign_id, name.strip(), "DRAFT", json.dumps(clean), brief.strip()),
            )
        return campaign_id

    def create_asset(
        self,
        campaign_id: str,
        channel: str,
        content: str,
        title: str,
        state: str = "DRAFT",
        author: str = "system",
    ) -> str:
        """Create an editable asset and immutable first revision."""
        if state not in {"DRAFT", "IN_EDITING", "WAITING_APPROVAL", "APPROVED"}:
            raise ValueError("ASSET_STATE_INVALID")
        if not content.strip() or not title.strip():
            raise ValueError("ASSET_INPUT_INVALID")
        asset_id = self._id()
        revision_id = self._id()
        with self._db() as db:
            campaign = db.execute("SELECT id FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
            if not campaign:
                raise KeyError(campaign_id)
            db.execute(
                "INSERT INTO assets(id,campaign_id,channel,content,state,title,version) VALUES (?,?,?,?,?,?,1)",
                (asset_id, campaign_id, channel, content, state, title),
            )
            db.execute(
                "INSERT INTO asset_revisions VALUES (?,?,?,?,?,?)",
                (revision_id, asset_id, 1, content, author, time.time()),
            )
        return asset_id

    def save_revision(
        self, asset_id: str, content: str, expected_version: int, author: str
    ) -> dict[str, Any]:
        """Autosave new content with optimistic concurrency protection."""
        if not content.strip() or not author.strip():
            raise ValueError("ASSET_REVISION_INPUT_INVALID")
        with self._db() as db:
            asset = db.execute("SELECT version FROM assets WHERE id=?", (asset_id,)).fetchone()
            if not asset:
                raise KeyError(asset_id)
            if asset[0] != expected_version:
                raise ValueError("ASSET_VERSION_CONFLICT")
            version = expected_version + 1
            revision_id = self._id()
            db.execute(
                "INSERT INTO asset_revisions VALUES (?,?,?,?,?,?)",
                (revision_id, asset_id, version, content, author, time.time()),
            )
            db.execute(
                "UPDATE assets SET content=?,version=?,state='IN_EDITING' WHERE id=?",
                (content, version, asset_id),
            )
            db.execute(
                "UPDATE approvals SET state='SUPERSEDED' "
                "WHERE asset_id=? AND state IN ('PENDING','APPROVED')",
                (asset_id,),
            )
        return {
            "id": revision_id,
            "asset_id": asset_id,
            "version": version,
            "content": content,
            "author": author,
        }

    def revisions(self, asset_id: str) -> list[dict[str, Any]]:
        """List immutable revisions newest first."""
        with self._db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM asset_revisions WHERE asset_id=? ORDER BY version DESC",
                    (asset_id,),
                )
            ]

    def restore_revision(
        self, asset_id: str, version: int, expected_version: int, author: str
    ) -> dict[str, Any]:
        """Restore historical content by appending a new revision."""
        with self._db() as db:
            row = db.execute(
                "SELECT content FROM asset_revisions WHERE asset_id=? AND version=?",
                (asset_id, version),
            ).fetchone()
            if not row:
                raise KeyError((asset_id, version))
            content = row[0]
        return self.save_revision(asset_id, content, expected_version, author)

    def campaign_readiness(self, campaign_id: str) -> dict[str, Any]:
        """Explain channel readiness for the campaign cockpit."""
        campaign = self.campaign(campaign_id)
        channels = json.loads(campaign["channels"])
        ready = sorted(
            {asset["channel"] for asset in campaign["assets"] if asset["state"] == "APPROVED"}
        )
        blockers = [
            f"Create an approved asset for {channel}"
            for channel in channels
            if channel not in ready
        ]
        score = round(100 * len(ready) / len(channels)) if channels else 0
        return {"score": score, "ready_channels": ready, "blockers": blockers}

    def my_work(self) -> list[dict[str, Any]]:
        """Return actionable approval and publishing recovery work."""
        items: list[dict[str, Any]] = []
        with self._db() as db:
            for row in db.execute(
                "SELECT id,risk,asset_id FROM approvals WHERE state='PENDING' ORDER BY rowid"
            ):
                items.append(
                    {
                        "kind": "approval",
                        "id": row[0],
                        "priority": row[1],
                        "asset_id": row[2],
                        "action": "Review content",
                    }
                )
            for row in db.execute(
                "SELECT DISTINCT b.id FROM publish_batches b JOIN deliveries d ON d.batch_id=b.id WHERE d.state IN ('FAILED','RETRYABLE') ORDER BY b.rowid"
            ):
                items.append(
                    {
                        "kind": "publish_failure",
                        "id": row[0],
                        "priority": "HIGH",
                        "action": "Recover publication",
                    }
                )
        return items

    def record_asset(self, campaign_id: str, channel: str, content: str, state: str) -> str:
        if state not in {"READY", "FAILED"}:
            raise ValueError("CAMPAIGN_ASSET_STATE_INVALID")
        asset_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO assets(id,campaign_id,channel,content,state) VALUES (?,?,?,?,?)",
                (asset_id, campaign_id, channel, content, state),
            )
            states = [
                r[0]
                for r in db.execute("SELECT state FROM assets WHERE campaign_id=?", (campaign_id,))
            ]
            campaign_state = (
                "PARTIAL"
                if "FAILED" in states and "READY" in states
                else ("FAILED" if states and set(states) == {"FAILED"} else "REVIEW_READY")
            )
            db.execute("UPDATE campaigns SET state=? WHERE id=?", (campaign_state, campaign_id))
        return asset_id

    def campaign(self, campaign_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
            if not row:
                raise KeyError(campaign_id)
            result = dict(row)
            result["assets"] = [
                dict(x)
                for x in db.execute(
                    "SELECT * FROM assets WHERE campaign_id=? ORDER BY rowid", (campaign_id,)
                )
            ]
            return result

    def asset(self, asset_id: str) -> dict[str, Any]:
        """Return one editable asset."""
        with self._db() as db:
            row = db.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
            if not row:
                raise KeyError(asset_id)
            return dict(row)

    def _audit(
        self, db: sqlite3.Connection, entity_id: str, kind: str, payload: dict[str, Any]
    ) -> None:
        db.execute(
            "INSERT INTO audit_events VALUES (?,?,?,?,?)",
            (self._id(), entity_id, kind, json.dumps(payload, sort_keys=True), time.time()),
        )

    def audit_events(self, entity_id: str) -> list[dict[str, Any]]:
        """Return chronological audit events for an entity."""
        with self._db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM audit_events WHERE entity_id=? ORDER BY created_at,rowid",
                    (entity_id,),
                )
            ]

    def request_asset_approval(
        self, asset_id: str, requester: str, risk: str, findings: list[str]
    ) -> str:
        """Request review for the asset's exact current revision."""
        if risk not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("APPROVAL_RISK_INVALID")
        request_id = self._id()
        with self._db() as db:
            asset = db.execute("SELECT version FROM assets WHERE id=?", (asset_id,)).fetchone()
            if not asset:
                raise KeyError(asset_id)
            db.execute(
                "UPDATE approvals SET state='SUPERSEDED' WHERE asset_id=? AND state='PENDING'",
                (asset_id,),
            )
            db.execute(
                "INSERT INTO approvals(id,asset_id,requester,risk,findings,state,reviewer,reason,revision_version) "
                "VALUES (?,?,?,?,?,'PENDING',NULL,NULL,?)",
                (request_id, asset_id, requester, risk, json.dumps(findings), asset[0]),
            )
            db.execute("UPDATE assets SET state='WAITING_APPROVAL' WHERE id=?", (asset_id,))
            self._audit(
                db,
                asset_id,
                "APPROVAL_REQUESTED",
                {"request_id": request_id, "revision_version": asset[0], "risk": risk},
            )
        return request_id

    def decide_asset_approval(
        self, request_id: str, reviewer: str, decision: str, reason: str
    ) -> None:
        """Record a revision-bound decision and update asset readiness."""
        if decision not in {"APPROVED", "NEEDS_CHANGES", "REJECTED"}:
            raise ValueError("APPROVAL_DECISION_INVALID")
        if not reviewer.strip() or not reason.strip():
            raise ValueError("APPROVAL_DECISION_INPUT_INVALID")
        with self._db() as db:
            row = db.execute(
                "SELECT asset_id,requester,risk,state,revision_version FROM approvals WHERE id=?",
                (request_id,),
            ).fetchone()
            if not row:
                raise KeyError(request_id)
            if row[3] != "PENDING":
                raise ValueError("APPROVAL_REVISION_STALE")
            asset = db.execute("SELECT version FROM assets WHERE id=?", (row[0],)).fetchone()
            if not asset or asset[0] != row[4]:
                db.execute("UPDATE approvals SET state='SUPERSEDED' WHERE id=?", (request_id,))
                raise ValueError("APPROVAL_REVISION_STALE")
            if row[1] == reviewer and row[2] == "HIGH" and decision == "APPROVED":
                raise PermissionError("APPROVAL_SELF_REVIEW")
            db.execute(
                "UPDATE approvals SET state=?,reviewer=?,reason=? WHERE id=?",
                (decision, reviewer, reason, request_id),
            )
            asset_state = "APPROVED" if decision == "APPROVED" else "IN_EDITING"
            db.execute("UPDATE assets SET state=? WHERE id=?", (asset_state, row[0]))
            self._audit(
                db,
                row[0],
                "APPROVAL_DECIDED",
                {
                    "request_id": request_id,
                    "decision": decision,
                    "reviewer": reviewer,
                    "reason": reason,
                    "revision_version": row[4],
                },
            )

    def request_approval(
        self, asset_id: str, requester: str, risk: str, findings: list[str]
    ) -> str:
        request_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO approvals(id,asset_id,requester,risk,findings,state,reviewer,reason) VALUES (?,?,?,?,?,'PENDING',NULL,NULL)",
                (request_id, asset_id, requester, risk, json.dumps(findings)),
            )
        return request_id

    def decide_approval(self, request_id: str, reviewer: str, decision: str, reason: str) -> None:
        if decision not in {"APPROVED", "NEEDS_CHANGES", "REJECTED"}:
            raise ValueError("APPROVAL_DECISION_INVALID")
        with self._db() as db:
            row = db.execute(
                "SELECT requester,risk FROM approvals WHERE id=?", (request_id,)
            ).fetchone()
            if not row:
                raise KeyError(request_id)
            if row[0] == reviewer and row[1] == "HIGH" and decision == "APPROVED":
                raise PermissionError("APPROVAL_SELF_REVIEW")
            db.execute(
                "UPDATE approvals SET state=?,reviewer=?,reason=? WHERE id=?",
                (decision, reviewer, reason, request_id),
            )

    def create_voice_profile(self, name: str, source: str) -> str:
        profile_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO voice_profiles VALUES (?,?,?,'DRAFT')", (profile_id, name, source)
            )
        return profile_id

    def add_voice_rule(
        self, profile_id: str, kind: str, value: str, evidence: str, *, conflict: bool = False
    ) -> str:
        rule_id = self._id()
        state = "CONFLICT" if conflict else "VALIDATED"
        with self._db() as db:
            db.execute(
                "INSERT INTO voice_rules VALUES (?,?,?,?,?,?)",
                (rule_id, profile_id, kind, value, evidence, state),
            )
            if conflict:
                db.execute("UPDATE voice_profiles SET state='CONFLICT' WHERE id=?", (profile_id,))
        return rule_id

    def create_publish_batch(self, asset_id: str, channels: list[str]) -> str:
        batch_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO publish_batches VALUES (?,?,?,?)",
                (batch_id, asset_id, "VALIDATING", json.dumps(channels)),
            )
        return batch_id

    def record_delivery(
        self, batch_id: str, channel: str, state: str, remote_id: str | None
    ) -> None:
        if state not in {"PUBLISHED", "RETRYABLE", "FAILED"}:
            raise ValueError("PUBLISH_STATE_INVALID")
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO deliveries VALUES (?,?,?,?,?)",
                (self._id(), batch_id, channel, state, remote_id),
            )
            states = [
                x[0]
                for x in db.execute("SELECT state FROM deliveries WHERE batch_id=?", (batch_id,))
            ]
            overall = (
                "PUBLISHED"
                if states and set(states) == {"PUBLISHED"}
                else ("PARTIAL" if "PUBLISHED" in states else "RETRYABLE")
            )
            db.execute("UPDATE publish_batches SET state=? WHERE id=?", (overall, batch_id))

    def retryable_channels(self, batch_id: str) -> list[str]:
        with self._db() as db:
            return [
                x[0]
                for x in db.execute(
                    "SELECT channel FROM deliveries WHERE batch_id=? AND state IN ('RETRYABLE','FAILED') ORDER BY channel",
                    (batch_id,),
                )
            ]

    def publish_batch(self, batch_id: str) -> dict[str, Any]:
        """Return one publish batch and its per-channel delivery outcomes."""
        with self._db() as db:
            row = db.execute("SELECT * FROM publish_batches WHERE id=?", (batch_id,)).fetchone()
            if not row:
                raise KeyError(batch_id)
            result = dict(row)
            result["channels"] = json.loads(result["channels"])
            result["deliveries"] = [
                dict(x)
                for x in db.execute(
                    "SELECT * FROM deliveries WHERE batch_id=? ORDER BY channel", (batch_id,)
                )
            ]
            return result

    def request_publish_retry(self, batch_id: str) -> list[str]:
        """Queue only failed/retryable channels while preserving successful deliveries."""
        channels = self.retryable_channels(batch_id)
        if not channels:
            raise ValueError("PUBLISH_NOT_RETRYABLE")
        with self._db() as db:
            db.execute("UPDATE publish_batches SET state='RETRYING' WHERE id=?", (batch_id,))
        return channels

    def create_localization_job(self, asset_id: str, locales: list[str]) -> str:
        job_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO localization_jobs VALUES (?,?,?,?)",
                (job_id, asset_id, "QUEUED", json.dumps(locales)),
            )
        return job_id

    def record_locale(self, job_id: str, locale: str, content: str, score: float) -> None:
        if not 0 <= score <= 1:
            raise ValueError("LOCALE_SCORE_INVALID")
        state = "APPROVED" if score >= 0.8 else "REVIEW_REQUIRED"
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO locale_variants VALUES (?,?,?,?,?,?)",
                (self._id(), job_id, locale, content, score, state),
            )
            states = [
                x[0]
                for x in db.execute("SELECT state FROM locale_variants WHERE job_id=?", (job_id,))
            ]
            db.execute(
                "UPDATE localization_jobs SET state=? WHERE id=?",
                ("PARTIAL" if len(set(states)) > 1 else states[0], job_id),
            )

    def approvable_locales(self, job_id: str) -> list[str]:
        with self._db() as db:
            return [
                x[0]
                for x in db.execute(
                    "SELECT locale FROM locale_variants WHERE job_id=? AND state='APPROVED' ORDER BY locale",
                    (job_id,),
                )
            ]

    def capture_provenance(self, asset_id: str, model: str, prompt: str, voice_version: str) -> str:
        record_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO provenance VALUES (?,?,?,?,?,'CAPTURED',?)",
                (record_id, asset_id, model, prompt, voice_version, time.time()),
            )
        return record_id

    def add_provenance_event(self, record_id: str, kind: str, payload: dict[str, Any]) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO provenance_events VALUES (?,?,?,?,?)",
                (self._id(), record_id, kind, json.dumps(payload, sort_keys=True), time.time()),
            )

    def export_provenance(self, record_id: str) -> str:
        with self._db() as db:
            row = db.execute("SELECT * FROM provenance WHERE id=?", (record_id,)).fetchone()
            if not row:
                raise KeyError(record_id)
            data = dict(row)
            data["prompt"] = re.sub(r"\{\{[^}]+\}\}", "[REDACTED]", data["prompt"])
            data["events"] = [
                dict(x)
                for x in db.execute(
                    "SELECT kind,payload,created_at FROM provenance_events WHERE record_id=? ORDER BY created_at",
                    (record_id,),
                )
            ]
        return json.dumps(data, sort_keys=True)

    def approval(self, request_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute("SELECT * FROM approvals WHERE id=?", (request_id,)).fetchone()
            if not row:
                raise KeyError(request_id)
            result = dict(row)
            result["findings"] = json.loads(result["findings"])
            return result

    def attention_summary(self) -> dict[str, int]:
        with self._db() as db:
            pending = db.execute("SELECT COUNT(*) FROM approvals WHERE state='PENDING'").fetchone()[
                0
            ]
            retries = db.execute(
                "SELECT COUNT(*) FROM deliveries WHERE state IN ('FAILED','RETRYABLE')"
            ).fetchone()[0]
            locales = db.execute(
                "SELECT COUNT(*) FROM locale_variants WHERE state='REVIEW_REQUIRED'"
            ).fetchone()[0]
        return {
            "pending_approvals": int(pending),
            "retryable_deliveries": int(retries),
            "locales_to_review": int(locales),
        }

    def rows(self, table: str) -> list[dict[str, Any]]:
        query = _TABLE_SELECTS.get(table)
        if query is None:
            raise ValueError("TABLE_INVALID")
        with self._db() as db:
            return [dict(x) for x in db.execute(query)]


def _esc(v: Any) -> str:
    return html.escape(str(v), quote=True)


STATE_COPY = {
    "DRAFT": ("Draft", "Add or generate channel assets"),
    "PARTIAL": ("Partially ready", "Resolve failed assets while keeping successful work"),
    "PENDING": ("Awaiting review", "An assigned reviewer must make a decision"),
    "APPROVED": ("Approved", "Continue to publishing"),
    "NEEDS_CHANGES": ("Changes requested", "Update the asset and resubmit it"),
    "REJECTED": ("Rejected", "Review the decision reason"),
    "RETRYABLE": ("Retry available", "Retry without republishing successful channels"),
    "REVIEW_REQUIRED": ("Review required", "A reviewer must check this locale"),
    "CONFLICT": ("Conflict", "Resolve conflicting rules before activation"),
}


def _notice(message: str | None, error: bool = False) -> str:
    if not message:
        return ""
    role = "alert" if error else "status"
    kind = "notice-error" if error else "notice-success"
    return f'<section class="notice {kind}" role="{role}"><p>{_esc(message)}</p></section>'


def _layout(page: str, body: str, notice: str | None = None, error: bool = False) -> str:
    title, subtitle = PAGES[page]
    nav = "".join(
        f'<a href="/workspace/{slug}"{" aria-current=page" if slug == page else ""}>{_esc(label)}</a>'
        for slug, (label, _) in PAGES.items()
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + _esc(title)
        + ' | ContentForge</title><link rel="stylesheet" href="/static/workspaces.css"></head><body><a class="skip" href="#main">Skip to content</a><header><strong>ContentForge</strong><span>Content operations</span></header><div class="shell"><nav aria-label="Workspaces">'
        + nav
        + '</nav><main id="main" tabindex="-1"><p class="eyebrow">Workspace</p><h1>'
        + _esc(title)
        + "</h1><p>"
        + _esc(subtitle)
        + '</p><div class="live" aria-live="polite">Ready</div>'
        + _notice(notice, error)
        + body
        + "</main></div></body></html>"
    )


def _cards(
    rows: list[dict[str, Any]],
    keys: list[str],
    empty: str,
    link_base: str | None = None,
    action_label: str = "Open",
) -> str:
    if not rows:
        return f'<div class="empty"><h2>Nothing here yet</h2><p>{_esc(empty)}</p></div>'
    cards = []
    for row in rows:
        state = str(row.get("state", ""))
        label, nxt = STATE_COPY.get(state, (state.replace("_", " ").title(), "Open for details"))
        fields = "".join(
            f"<p><strong>{_esc(k.replace('_', ' ').title())}:</strong> {_esc(label if k == 'state' else row.get(k, ''))}</p>"
            for k in keys
        )
        link = (
            f'<a class="card-action" href="{_esc(link_base)}/{_esc(row.get("id", ""))}">{_esc(action_label)}</a>'
            if link_base
            else ""
        )
        cards.append(
            f'<article>{fields}<p class="next-action"><strong>Next:</strong> {_esc(nxt)}</p>{link}</article>'
        )
    return '<div class="cards">' + "".join(cards) + "</div>"


def _attention(store: ContentOpsStore) -> str:
    x = store.attention_summary()
    plural = "s" if x["pending_approvals"] != 1 else ""
    return f'<aside class="attention" aria-label="Work requiring attention"><strong>{x["pending_approvals"]} pending approval{plural}</strong><span>{x["retryable_deliveries"]} delivery retries</span><span>{x["locales_to_review"]} locales to review</span></aside>'


def render_workspace(
    page: str, store: ContentOpsStore, notice: str | None = None, error: bool = False
) -> str:
    if page not in PAGES:
        raise KeyError(page)
    q = _attention(store)
    if page == "campaigns":
        body = (
            q
            + '<section class="panel"><h2>New campaign</h2><form method="post" action="/workspace/campaigns/create"><label>Campaign name<input name="name" required maxlength="160"></label><label>Campaign brief<textarea name="brief" required maxlength="4000"></textarea></label><label>Channels<input name="channels" required aria-describedby="channels-help"></label><p id="channels-help" class="help">Enter comma-separated channels.</p><button class="primary">Create campaign</button></form></section>'
            + _cards(
                store.rows("campaigns"),
                ["name", "state"],
                "Create a campaign.",
                "/workspace/campaigns",
                "Open campaign",
            )
        )
    elif page == "approvals":
        body = (
            q
            + '<section class="panel"><h2>Governance queue</h2>'
            + _cards(
                store.rows("approvals"),
                ["asset_id", "risk", "state", "findings"],
                "New approval requests appear here.",
                "/workspace/approvals",
                "Review request",
            )
            + "</section>"
        )
    elif page == "voice":
        body = (
            q
            + '<section class="panel"><h2>Evidence-backed rules</h2>'
            + _cards(
                store.rows("voice_rules"),
                ["kind", "value", "evidence", "state"],
                "Import representative content.",
            )
            + "</section>"
        )
    elif page == "publish":
        body = (
            q
            + '<section class="panel"><h2>Delivery batches</h2><p class="help">Open a batch to inspect channel outcomes and retry only failed channels.</p>'
            + _cards(
                store.rows("publish_batches"),
                ["asset_id", "state"],
                "Published and retryable batches will appear here.",
                "/workspace/publish",
                "Open delivery batch",
            )
            + "</section>"
        )
    elif page == "localization":
        body = (
            q
            + '<section class="panel"><h2>Locale matrix</h2>'
            + _cards(
                store.rows("locale_variants"),
                ["locale", "score", "state", "content"],
                "Start translation QA.",
            )
            + "</section>"
        )
    else:
        body = (
            q
            + '<section class="panel"><h2>Provenance ledger</h2>'
            + _cards(
                store.rows("provenance"),
                ["asset_id", "model", "voice_version", "state"],
                "Records appear after generation.",
            )
            + "</section>"
        )
    return _layout(page, body, notice, error)


def render_campaign_detail(campaign_id: str, store: ContentOpsStore) -> str:
    c = store.campaign(campaign_id)
    label, nxt = STATE_COPY.get(c["state"], (c["state"], "Review campaign"))
    channels = json.loads(c["channels"])
    assets = c["assets"]
    body = (
        f'<p><a href="/workspace/campaigns">Back to campaigns</a></p><section class="panel context"><h2>{_esc(c["name"])}</h2><p><span class="status">{_esc(label)}</span></p><p><strong>Next:</strong> {_esc(nxt)}</p><p aria-label="Campaign progress">{len(assets)} of {len(channels)} channel assets created</p></section>'
        + _cards(assets, ["channel", "state", "content"], "No assets yet.")
    )
    return _layout("campaigns", body)


def render_approval_detail(
    request_id: str, store: ContentOpsStore, notice: str | None = None, error: bool = False
) -> str:
    a = store.approval(request_id)
    label, nxt = STATE_COPY.get(a["state"], (a["state"], "Review request"))
    findings = (
        "".join(f"<li>{_esc(x)}</li>" for x in a["findings"]) or "<li>No findings recorded.</li>"
    )
    form = ""
    if a["state"] == "PENDING":
        form = f'<section class="panel"><h2>Record decision</h2><form method="post" action="/workspace/approvals/{_esc(request_id)}/decision"><label>Reviewer<input name="reviewer" required></label><fieldset><legend>Decision</legend><label><input type="radio" name="decision" value="APPROVED" required> Approve</label><label><input type="radio" name="decision" value="NEEDS_CHANGES"> Request changes</label><label><input type="radio" name="decision" value="REJECTED"> Reject</label></fieldset><label>Reason<textarea name="reason" required maxlength="2000"></textarea></label><button class="primary">Save decision</button></form></section>'
    body = (
        f'<p><a href="/workspace/approvals">Back to approvals</a></p><section class="panel context"><h2>Asset {_esc(a["asset_id"])}</h2><p><span class="status">{_esc(label)}</span></p><p><strong>Risk:</strong> {_esc(a["risk"])}</p><p><strong>Requester:</strong> {_esc(a["requester"])}</p><h3>Findings</h3><ul>{findings}</ul><p><strong>Next:</strong> {_esc(nxt)}</p></section>'
        + form
    )
    return _layout("approvals", body, notice, error)


def render_publish_batch_detail(
    batch_id: str, store: ContentOpsStore, notice: str | None = None, error: bool = False
) -> str:
    batch = store.publish_batch(batch_id)
    retryable = store.retryable_channels(batch_id)
    cards = []
    for item in batch["deliveries"]:
        label, nxt = STATE_COPY.get(item["state"], (item["state"].title(), "Review delivery"))
        cards.append(
            f'<article><h3>{_esc(item["channel"].title())}</h3><p><span class="status">{_esc(label)}</span></p><p><strong>Remote ID:</strong> {_esc(item.get("remote_id") or "Not available")}</p><p class="next-action"><strong>Next:</strong> {_esc(nxt)}</p></article>'
        )
    retry = ""
    if retryable:
        inputs = "".join(
            f'<input type="hidden" name="channels" value="{_esc(channel)}">'
            for channel in retryable
        )
        retry = f'<section class="panel recovery"><h2>Safe recovery</h2><p>Only failed or retryable channels will be queued. Successful deliveries will not be published again.</p><p><strong>Retry scope:</strong> {_esc(", ".join(retryable))}</p><form method="post" action="/workspace/publish/{_esc(batch_id)}/retry">{inputs}<button class="primary">Retry failed channels</button></form></section>'
    body = f'<p><a href="/workspace/publish">Back to publish center</a></p><section class="panel context"><p class="eyebrow">Delivery batch</p><h2>Asset {_esc(batch["asset_id"])}</h2><p><span class="status">{_esc(batch["state"].replace("_", " ").title())}</span></p></section><div class="cards">{"".join(cards)}</div>{retry}'
    return _layout("publish", body, notice, error)
