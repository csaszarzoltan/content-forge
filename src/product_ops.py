"""Workflow domain and accessible HTML views for ContentForge product workspaces.

The module has no web-framework dependency. SQLite persistence and pure rendering
keep the workflow rules deterministic and independently testable.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from src.schemas.transcreation import TranscreationResult

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
                CREATE TABLE IF NOT EXISTS transcreation_results(id TEXT PRIMARY KEY,asset_id TEXT,locale TEXT,analysis TEXT,adaptation TEXT,preflight TEXT,decisions TEXT,created_at REAL,updated_at REAL);
                CREATE TABLE IF NOT EXISTS transcreation_flags(id TEXT PRIMARY KEY,asset_id TEXT,segment_id TEXT,resolved INTEGER DEFAULT 0,override INTEGER DEFAULT 0,created_at REAL,UNIQUE(asset_id,segment_id));
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


class TranscreationStore:
    """Persist transcreation analysis/adaptation/preflight results per asset.

    Follows the ContentOpsStore pattern: SQLite with JSON columns and an
    audit log. Results are keyed by asset + locale; every write upserts the
    latest snapshot and appends a provenance event so downstream workers
    (review UI, publish gate) can read them back deterministically.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS transcreation_results(
                    id TEXT PRIMARY KEY,
                    asset_id TEXT,
                    locale TEXT,
                    analysis TEXT,
                    adaptation TEXT,
                    preflight TEXT,
                    decisions TEXT,
                    created_at REAL,
                    updated_at REAL,
                    UNIQUE(asset_id, locale)
                );
                CREATE TABLE IF NOT EXISTS transcreation_flags(
                    id TEXT PRIMARY KEY,
                    asset_id TEXT,
                    segment_id TEXT,
                    resolved INTEGER DEFAULT 0,
                    override INTEGER DEFAULT 0,
                    created_at REAL,
                    UNIQUE(asset_id, segment_id)
                );
                CREATE TABLE IF NOT EXISTS audit_events(
                    id TEXT PRIMARY KEY,
                    entity_id TEXT,
                    kind TEXT,
                    payload TEXT,
                    created_at REAL
                );
                """
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _id() -> str:
        return uuid.uuid4().hex

    def save_result(self, result: TranscreationResult) -> None:
        """Upsert one analysis/adaptation/preflight snapshot for an asset."""
        data = result.model_dump(mode="json")
        locale = "unknown"
        for snapshot in (result.analysis, result.adaptation, result.preflight):
            if snapshot is not None:
                locale = getattr(snapshot, "locale", locale) or locale
                break
        with self._db() as db:
            db.execute(
                """
                INSERT INTO transcreation_results(
                    id, asset_id, locale, analysis, adaptation, preflight,
                    decisions, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(asset_id, locale) DO UPDATE SET
                    analysis=excluded.analysis,
                    adaptation=excluded.adaptation,
                    preflight=excluded.preflight,
                    decisions=excluded.decisions,
                    updated_at=excluded.updated_at
                """,
                (
                    result.id,
                    result.asset_id,
                    locale,
                    json.dumps(data.get("analysis")),
                    json.dumps(data.get("adaptation")),
                    json.dumps(data.get("preflight")),
                    json.dumps(data.get("decisions")),
                    result.created_at.timestamp(),
                    time.time(),
                ),
            )
            self._audit(db, result.asset_id, "TRANSCREATION_SAVED", {"result_id": result.id})

    def result(self, asset_id: str) -> TranscreationResult:
        """Return the latest stored result for an asset (any locale)."""
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM transcreation_results WHERE asset_id=? "
                "ORDER BY updated_at DESC, rowid DESC LIMIT 1",
                (asset_id,),
            ).fetchone()
            if not row:
                raise KeyError(asset_id)
            return self._row_to_result(row)

    def result_for_locale(self, asset_id: str, locale: str) -> TranscreationResult:
        """Return the stored result for an exact asset + locale pair."""
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM transcreation_results WHERE asset_id=? AND locale=?",
                (asset_id, locale),
            ).fetchone()
            if not row:
                raise KeyError((asset_id, locale))
            return self._row_to_result(row)

    def results(self, asset_id: str) -> list[TranscreationResult]:
        """Return all stored results for an asset, newest first."""
        with self._db() as db:
            rows = db.execute(
                "SELECT * FROM transcreation_results WHERE asset_id=? "
                "ORDER BY updated_at DESC, rowid DESC",
                (asset_id,),
            ).fetchall()
        return [self._row_to_result(row) for row in rows]

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> TranscreationResult:
        from src.schemas.transcreation import TranscreationResult

        data: dict[str, Any] = {
            "id": row["id"],
            "asset_id": row["asset_id"],
            "analysis": _json_or_none(row["analysis"]),
            "adaptation": _json_or_none(row["adaptation"]),
            "preflight": _json_or_none(row["preflight"]),
            "decisions": json.loads(row["decisions"]) if row["decisions"] else [],
        }
        return TranscreationResult.model_validate(data)

    def add_decision(self, asset_id: str, decision: dict[str, Any]) -> None:
        """Append one reviewer decision to the asset's latest result."""
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM transcreation_results WHERE asset_id=? "
                "ORDER BY updated_at DESC, rowid DESC LIMIT 1",
                (asset_id,),
            ).fetchone()
            if not row:
                raise KeyError(asset_id)
            decisions = json.loads(row["decisions"]) if row["decisions"] else []
            decisions.append(decision)
            db.execute(
                "UPDATE transcreation_results SET decisions=?,updated_at=? WHERE id=?",
                (json.dumps(decisions, sort_keys=True), time.time(), row["id"]),
            )
            self._audit(
                db,
                asset_id,
                "TRANSCREATION_DECISION",
                {"segment_id": decision.get("segment_id"), "decision": decision.get("decision")},
            )

    def flags(self, asset_id: str) -> list[dict[str, Any]]:
        """Return the unresolved/low-confidence flag rows for an asset."""
        with self._db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM transcreation_flags WHERE asset_id=? AND resolved=0 "
                    "ORDER BY rowid",
                    (asset_id,),
                )
            ]

    def resolve_flags(self, asset_id: str, segment_ids: list[str]) -> int:
        """Mark flagged segments resolved (review decisions taken). Returns count."""
        if not segment_ids:
            return 0
        with self._db() as db:
            db.executemany(
                "INSERT OR IGNORE INTO transcreation_flags(id,asset_id,segment_id,resolved,created_at) "
                "VALUES (?,?,?,1,?)",
                [(self._id(), asset_id, seg, time.time()) for seg in segment_ids],
            )
            placeholders = ",".join("?" * len(segment_ids))
            sql = (
                "UPDATE transcreation_flags SET resolved=1 WHERE asset_id=? AND "
                "segment_id IN (" + placeholders + ")"
            )
            db.execute(sql, (asset_id, *segment_ids))
            self._audit(db, asset_id, "TRANSCREATION_FLAGS_RESOLVED", {"count": len(segment_ids)})
            return len(segment_ids)

    def set_override(self, asset_id: str, override: bool = True) -> None:
        """Explicitly override the preflight block for an asset (US-005).

        Unblocks publishing by clearing the ``blocked`` flag on the stored
        preflight snapshot while keeping the risk items for the audit trail.
        """
        with self._db() as db:
            row = db.execute(
                "SELECT id, preflight FROM transcreation_results WHERE asset_id=? "
                "ORDER BY updated_at DESC, rowid DESC LIMIT 1",
                (asset_id,),
            ).fetchone()
            if not row or not row["preflight"]:
                raise KeyError(asset_id)
            payload = json.loads(row["preflight"])
            payload["blocked"] = False
            payload["override_available"] = bool(override)
            payload["audit_status"] = "review_needed"
            db.execute(
                "UPDATE transcreation_results SET preflight=?,updated_at=? WHERE id=?",
                (json.dumps(payload), time.time(), row["id"]),
            )
            self._audit(db, asset_id, "TRANSCREATION_OVERRIDE", {"override": override})

    def publish_blocked(self, asset_id: str) -> bool:
        """True when the latest preflight blocks publishing (US-005 gate)."""
        with self._db() as db:
            row = db.execute(
                "SELECT preflight FROM transcreation_results WHERE asset_id=? "
                "ORDER BY updated_at DESC, rowid DESC LIMIT 1",
                (asset_id,),
            ).fetchone()
            if not row or not row["preflight"]:
                return False
            payload = json.loads(row["preflight"])
            return bool(payload.get("blocked"))

    def _audit(
        self, db: sqlite3.Connection, entity_id: str, kind: str, payload: dict[str, Any]
    ) -> None:
        db.execute(
            "INSERT INTO audit_events VALUES (?,?,?,?,?)",
            (self._id(), entity_id, kind, json.dumps(payload, sort_keys=True), time.time()),
        )


def _json_or_none(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


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


def workspace_overview(store: ContentOpsStore) -> dict[str, Any]:
    """Return normalized collections for the complete React workspace shell."""
    assets: list[dict[str, Any]] = []
    with store._db() as db:
        assets = [dict(row) for row in db.execute("SELECT * FROM assets ORDER BY rowid DESC")]
    return {
        "campaigns": store.rows("campaigns"),
        "assets": assets,
        "approvals": store.rows("approvals"),
        "publish_batches": store.rows("publish_batches"),
        "deliveries": store.rows("deliveries"),
        "localization_jobs": store.rows("localization_jobs"),
        "locale_variants": store.rows("locale_variants"),
        "voice_profiles": store.rows("voice_profiles"),
        "voice_rules": store.rows("voice_rules"),
        "provenance": store.rows("provenance"),
        "summary": store.attention_summary(),
    }


# ============================================================================
# VideoJobStore — PROVISIONAL STUB (pre-tester scaffold, t_ba5cfcec)
# ----------------------------------------------------------------------------
# Persistence for the video pipeline (P0-1, analysis-brief.md §6). Follows the
# TranscreationStore pattern: raw sqlite3, JSON columns, audit log, uuid hex
# ids. Runtime behavior is implemented by the developer:
#
#   create_job(source) -> str              # VideoJobSource dict/dataclass
#   get_job(job_id) -> VideoJobRecord      # dict incl. scenes[]
#   update_state(job_id, state)            # state machine guard
#   list_scenes(job_id) -> list[dict]
#   update_scene(job_id, scene_id, **fields)
#   scene(job_id, scene_id) -> dict
#   audit(job_id, kind, payload)           # append audit event
#
# Job state machine: queued → outline → scenes → render → ready | failed
# Scene sub-states:  pending → generating → done | failed (attempts ≤ 3)
# ============================================================================


# Video job state machine: queued → outline → scenes → render → ready | failed.
# ``failed`` is reachable from any state; backwards jumps (e.g. ready → scenes)
# are rejected. Scene sub-states: pending → generating → done | failed.
_JOB_STATE_ORDER: tuple[str, ...] = ("queued", "outline", "scenes", "render", "ready")

# Live VideoJobStore instances keyed by DB path (see VideoJobStore.__init__).
_LIVE_VIDEO_STORES: dict[str, VideoJobStore] = {}

_SCENE_FIELDS: tuple[str, ...] = (
    "state",
    "attempts",
    "error",
    "image_path",
    "audio_path",
    "clip_path",
    "heading",
    "narration",
    "tts_text",
)


def _image_for_section(heading: str | None, images: dict) -> str | None:
    """Return the reused blog image for a section, or None when broken/missing.

    Matches the section heading against the blog post's image map (headings →
    image paths). Only images that exist on disk are reused; broken or missing
    images are skipped so the scene falls back to a styled title card
    (P0-3 acceptance: broken images never fail the job).
    """
    if not heading or not images:
        return None
    path = images.get(heading)
    if not path:
        return None
    candidate = Path(str(path))
    if candidate.is_file():
        return str(path)
    return None


class VideoJobStore:
    """Persist video jobs with a per-scene state machine (P0-1).

    Follows the TranscreationStore pattern: raw sqlite3 with JSON columns and
    an audit log. Jobs persist a source snapshot, brand voice / style / voice /
    resolution selection and per-scene rows (pending → generating → done |
    failed) with attempts, error and cached asset paths, so retries never
    re-synthesize/re-render completed scenes (US-003).
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        # Keep a module-level registry of live stores so direct-call helpers
        # (e.g. ``retry_video_job`` in the router) can resolve the store that
        # actually holds a job even when it was created on a different path
        # (the test seam points the module at a temp DB per fixture).
        _LIVE_VIDEO_STORES[self.path] = self
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS video_jobs(
                    id TEXT PRIMARY KEY,
                    source_type TEXT,
                    source_ref TEXT,
                    state TEXT,
                    brand_voice_id TEXT,
                    voice_profile_name TEXT,
                    style_preset TEXT,
                    voice TEXT,
                    resolution TEXT,
                    auto_segment INTEGER DEFAULT 1,
                    segment_order INTEGER,
                    parent_job_id TEXT,
                    error TEXT,
                    created_at REAL,
                    updated_at REAL,
                    output_path TEXT
                );
                CREATE TABLE IF NOT EXISTS video_scenes(
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    order_index INTEGER,
                    heading TEXT,
                    narration TEXT,
                    tts_text TEXT,
                    state TEXT,
                    attempts INTEGER DEFAULT 0,
                    error TEXT,
                    image_path TEXT,
                    audio_path TEXT,
                    clip_path TEXT,
                    created_at REAL,
                    updated_at REAL
                );
                CREATE TABLE IF NOT EXISTS video_audit(
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    kind TEXT,
                    payload TEXT,
                    created_at REAL
                );
                """
            )
            # Lightweight migration: pre-existing DBs (created before the
            # worker/combine pass) lack the new columns. CREATE TABLE IF NOT
            # EXISTS never alters an existing table, so add the columns here
            # (idempotent — sqlite ignores duplicate ADD COLUMN only via the
            # pragma guard below).
            _existing_job_cols = {r[1] for r in db.execute("PRAGMA table_info(video_jobs)")}
            if "output_path" not in _existing_job_cols:
                db.execute("ALTER TABLE video_jobs ADD COLUMN output_path TEXT")
            _existing_scene_cols = {r[1] for r in db.execute("PRAGMA table_info(video_scenes)")}
            if "clip_path" not in _existing_scene_cols:
                db.execute("ALTER TABLE video_scenes ADD COLUMN clip_path TEXT")

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _id() -> str:
        return uuid.uuid4().hex

    def create_job(self, source: dict) -> str:
        """Create a video job from a source dict; return the job id.

        Scenes are created from the source sections via split_sections so the
        job starts with an ordered scene list (P0-3 contract).
        """
        job_id = self._id()
        now = time.time()
        from src.services.video_scenes import split_sections

        with self._db() as db:
            db.execute(
                "INSERT INTO video_jobs("
                "id,source_type,source_ref,state,brand_voice_id,voice_profile_name,"
                "style_preset,voice,resolution,auto_segment,segment_order,parent_job_id,"
                "error,created_at,updated_at,output_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    str(source.get("source_type") or "script"),
                    str(source.get("source_ref") or ""),
                    "queued",
                    source.get("brand_voice_id"),
                    source.get("voice_profile_name"),
                    source.get("style_preset") or "explainer",
                    source.get("voice"),
                    source.get("resolution") or "720p",
                    1 if source.get("auto_segment", True) else 0,
                    source.get("segment_order"),
                    source.get("parent_job_id"),
                    None,
                    now,
                    now,
                    None,
                ),
            )
            sections = split_sections(str(source.get("source_ref") or ""))
            images: dict = source.get("images") or {}
            for idx, section_text in enumerate(sections, start=1):
                heading = None
                lines = [ln.strip() for ln in section_text.splitlines() if ln.strip()]
                if lines and lines[0].startswith("#"):
                    heading = lines[0].lstrip("#").strip()
                scene_id = self._id()
                db.execute(
                    "INSERT INTO video_scenes("
                    "id,job_id,order_index,heading,narration,tts_text,state,attempts,"
                    "error,image_path,audio_path,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        scene_id,
                        job_id,
                        idx,
                        heading,
                        section_text,
                        section_text,
                        "pending",
                        0,
                        None,
                        _image_for_section(heading, images),
                        None,
                        now,
                        now,
                    ),
                )
            self._audit(db, job_id, "JOB_CREATED", {"source_type": source.get("source_type")})
        return job_id

    def get_job(self, job_id: str) -> dict:
        """Return the full job record including its scenes and audit events."""
        with self._db() as db:
            row = db.execute("SELECT * FROM video_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            scenes = []
            for s in db.execute(
                "SELECT * FROM video_scenes WHERE job_id=? ORDER BY order_index", (job_id,)
            ):
                scene = dict(s)
                scene["order"] = scene.pop("order_index", 0)
                scenes.append(scene)
            events = []
            for e in db.execute(
                "SELECT * FROM video_audit WHERE job_id=? ORDER BY created_at, rowid", (job_id,)
            ):
                event = dict(e)
                try:
                    event["payload"] = json.loads(event["payload"]) if event.get("payload") else {}
                except (TypeError, json.JSONDecodeError):
                    event["payload"] = {}
                events.append(event)
        record = dict(row)
        record["scenes"] = scenes
        record["audit_events"] = events
        return record

    def update_state(self, job_id: str, state: str) -> None:
        """Transition the job to a valid next state (state machine guard)."""
        if state not in {"queued", "outline", "scenes", "render", "ready", "failed"}:
            raise ValueError(f"invalid video job state: {state}")
        with self._db() as db:
            row = db.execute("SELECT state FROM video_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            current = row["state"]
            if state == "failed":
                pass  # any state can fail
            elif current == "failed" and state in _JOB_STATE_ORDER:
                pass  # retry recovery: a failed job can re-enter the pipeline
            elif state in _JOB_STATE_ORDER and current in _JOB_STATE_ORDER:
                if _JOB_STATE_ORDER.index(state) < _JOB_STATE_ORDER.index(current):
                    raise ValueError(
                        f"invalid video job state transition: {current} -> {state}"
                    )
            else:
                raise ValueError(f"invalid video job state transition: {current} -> {state}")
            db.execute(
                "UPDATE video_jobs SET state=?, updated_at=? WHERE id=?",
                (state, time.time(), job_id),
            )
            self._audit(db, job_id, "JOB_STATE", {"state": state})

    def list_scenes(self, job_id: str) -> list[dict]:
        """Return all scene rows for a job, ordered by their section order."""
        with self._db() as db:
            row = db.execute("SELECT id FROM video_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            scenes = []
            for s in db.execute(
                "SELECT * FROM video_scenes WHERE job_id=? ORDER BY order_index", (job_id,)
            ):
                scene = dict(s)
                scene["order"] = scene.pop("order_index", 0)
                scenes.append(scene)
            return scenes

    def segment_job_ids(self, parent_id: str) -> list[str]:
        """Return child segment job ids whose ``parent_job_id`` matches parent_id."""
        with self._db() as db:
            return [
                str(row[0])
                for row in db.execute(
                    "SELECT id FROM video_jobs WHERE parent_job_id=? ORDER BY segment_order, rowid",
                    (parent_id,),
                )
            ]

    def queued_job_ids(self) -> list[str]:
        """Return processable job ids in FIFO order (worker pick-up list).

        The worker processes jobs whose state is queued/outline/scenes —
        newly created jobs plus jobs whose failed scenes were re-queued via
        the retry endpoint (which moves the job back to ``scenes``).
        """
        with self._db() as db:
            rows = db.execute(
                "SELECT id FROM video_jobs WHERE state IN ('queued','outline','scenes')"
                " ORDER BY created_at, rowid"
            ).fetchall()
            return [str(r[0]) for r in rows]

    def set_output_path(self, job_id: str, path: str | Path) -> None:
        """Persist a pre-rendered output file for a job (combine results)."""
        with self._db() as db:
            row = db.execute("SELECT id FROM video_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            db.execute(
                "UPDATE video_jobs SET output_path=?, updated_at=? WHERE id=?",
                (str(path), time.time(), job_id),
            )

    def update_scene(self, job_id: str, scene_id: str, **fields: Any) -> None:
        """Update scene fields (state, attempts, error, asset paths, ...).

        Only known columns are accepted (allowlist) so callers can never
        inject arbitrary SQL or write junk columns. The UPDATE statement is
        fully static — every column is a literal in the query text and all
        values are bound parameters (no string-built SQL).
        """
        updates: dict[str, Any] = {k: v for k, v in fields.items() if k in _SCENE_FIELDS}
        if not updates:
            return
        now = time.time()
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM video_scenes WHERE id=? AND job_id=?", (scene_id, job_id)
            ).fetchone()
            if not row:
                raise KeyError(scene_id)
            merged: dict[str, Any] = dict(row)
            merged.update(updates)
            merged["updated_at"] = now
            db.execute(
                "UPDATE video_scenes SET state=?, attempts=?, error=?, image_path=?,"
                " audio_path=?, clip_path=?, heading=?, narration=?, tts_text=?, updated_at=?"
                " WHERE id=? AND job_id=?",
                (
                    merged.get("state"),
                    merged.get("attempts") or 0,
                    merged.get("error"),
                    merged.get("image_path"),
                    merged.get("audio_path"),
                    merged.get("clip_path"),
                    merged.get("heading"),
                    merged.get("narration"),
                    merged.get("tts_text"),
                    now,
                    scene_id,
                    job_id,
                ),
            )
            if "state" in updates:
                self._audit(db, job_id, "SCENE_STATE", {"scene_id": scene_id, "state": updates["state"]})

    def scene(self, job_id: str, scene_id: str) -> dict:
        """Return one scene row."""
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM video_scenes WHERE id=? AND job_id=?", (scene_id, job_id)
            ).fetchone()
            if not row:
                raise KeyError(scene_id)
            return dict(row)

    def audit(self, job_id: str, kind: str, payload: dict | None = None) -> None:
        """Append an audit event for the job."""
        with self._db() as db:
            self._audit(db, job_id, kind, payload or {})

    def _audit(self, db: sqlite3.Connection, job_id: str, kind: str, payload: dict) -> None:
        db.execute(
            "INSERT INTO video_audit VALUES (?,?,?,?,?)",
            (self._id(), job_id, kind, json.dumps(payload, sort_keys=True), time.time()),
        )


class ContentPackageStore:
    """Persist content-creation packages with a workflow state machine (P0-1).

    Follows the TranscreationStore/FamilyStore pattern: raw sqlite3 with JSON
    columns and an audit log. A package records one source asset and the
    per-platform variants derived from it:

      package state: draft → generating → validating → ready_to_approve →
                     approved → publishing → published | failed
      variant state: pending → generated → validated → published | failed

    Idempotency: create/publish honour the FamilyStore ``_idem()`` pattern
    (request_hash + cached response; same key + different payload → 409).
    """

    VALID_TRANSITIONS: ClassVar[dict[str, set[str]]] = {
        "draft": {"generating", "failed"},
        "generating": {"validating", "failed"},
        "validating": {"ready_to_approve", "failed"},
        "ready_to_approve": {"approved", "failed"},
        "approved": {"publishing", "failed"},
        "publishing": {"published", "failed"},
        "published": set(),
        "failed": set(),
    }

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS content_packages(
                    id TEXT PRIMARY KEY,
                    source_type TEXT,
                    source_ref TEXT,
                    state TEXT,
                    brand_voice_id TEXT,
                    platforms TEXT,
                    created_at REAL,
                    updated_at REAL
                );
                CREATE TABLE IF NOT EXISTS content_variants(
                    id TEXT PRIMARY KEY,
                    package_id TEXT,
                    platform TEXT,
                    content TEXT,
                    char_count INTEGER DEFAULT 0,
                    validation_status TEXT DEFAULT 'pending',
                    publish_status TEXT DEFAULT 'pending',
                    error TEXT,
                    remote_id TEXT,
                    created_at REAL,
                    updated_at REAL
                );
                CREATE TABLE IF NOT EXISTS content_package_audit(
                    id TEXT PRIMARY KEY,
                    package_id TEXT,
                    kind TEXT,
                    payload TEXT,
                    created_at REAL
                );
                CREATE TABLE IF NOT EXISTS content_package_idempotency(
                    package_id TEXT,
                    actor_id TEXT,
                    key TEXT,
                    request_hash TEXT,
                    response TEXT,
                    PRIMARY KEY(package_id, actor_id, key)
                );
                """
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _id() -> str:
        return uuid.uuid4().hex

    # ── Idempotency (FamilyStore pattern) ───────────────────────────────────

    def _idem(self, d, w, u, key, payload):
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        r = d.execute(
            "SELECT request_hash,response FROM content_package_idempotency "
            "WHERE package_id=? AND actor_id=? AND key=?",
            (w, u, key),
        ).fetchone()
        if r and r[0] != h:
            raise ValueError("idempotency_key_reused")
        return json.loads(r[1]) if r else None

    def _save_idem(self, d, w, u, key, payload, response):
        d.execute(
            "INSERT INTO content_package_idempotency VALUES(?,?,?,?,?)",
            (
                w,
                u,
                key,
                hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                json.dumps(response),
            ),
        )

    # ── Package CRUD + state machine ────────────────────────────────────────

    def create_package(
        self,
        source_type: str,
        source_ref: str,
        platforms: list[str],
        brand_voice_id: str | None = None,
        idempotency_key: str | None = None,
        actor_id: str = "system",
    ) -> dict:
        """Create a package in ``draft`` state with one pending variant per platform."""
        payload = {
            "source_type": source_type,
            "source_ref": source_ref,
            "platforms": sorted(platforms),
            "brand_voice_id": brand_voice_id,
        }
        now = time.time()
        with self._db() as db:
            if idempotency_key:
                old = self._idem(db, "NEW", actor_id, idempotency_key, payload)
                if old:
                    return old
            pkg_id = self._id()
            db.execute(
                "INSERT INTO content_packages(id,source_type,source_ref,state,brand_voice_id,platforms,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (pkg_id, source_type, source_ref, "draft", brand_voice_id, json.dumps(sorted(platforms)), now, now),
            )
            for platform in platforms:
                db.execute(
                    "INSERT INTO content_variants(id,package_id,platform,content,char_count,validation_status,publish_status,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (self._id(), pkg_id, platform, "", 0, "pending", "pending", now, now),
                )
            out = {
                "id": pkg_id,
                "state": "draft",
                "platforms": sorted(platforms),
                "created_at": now,
            }
            if idempotency_key:
                self._save_idem(db, "NEW", actor_id, idempotency_key, payload, out)
            self._audit(db, pkg_id, "PACKAGE_CREATED", {"source_type": source_type, "platforms": sorted(platforms)})
            return out

    def get_package(self, package_id: str) -> dict:
        """Return the full package record with variants and timestamps."""
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM content_packages WHERE id=?", (package_id,)
            ).fetchone()
            if not row:
                raise KeyError(package_id)
            record = dict(row)
            record["platforms"] = json.loads(record.get("platforms") or "[]")
            record["variants"] = self._variants(db, package_id)
            return record

    def _variants(self, db: sqlite3.Connection, package_id: str) -> list[dict]:
        rows = db.execute(
            "SELECT * FROM content_variants WHERE package_id=? ORDER BY rowid", (package_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_state(self, package_id: str, state: str) -> None:
        """Validate the transition and persist the new package state."""
        with self._db() as db:
            row = db.execute(
                "SELECT state FROM content_packages WHERE id=?", (package_id,)
            ).fetchone()
            if not row:
                raise KeyError(package_id)
            current = row["state"]
            allowed = self.VALID_TRANSITIONS.get(current, set())
            if state not in allowed:
                raise ValueError(f"invalid_transition:{current}->{state}")
            db.execute(
                "UPDATE content_packages SET state=?, updated_at=? WHERE id=?",
                (state, time.time(), package_id),
            )
            self._audit(db, package_id, "STATE_CHANGE", {"from": current, "to": state})

    def save_variants(self, package_id: str, variants: list[dict]) -> None:
        """Upsert generated variant content (keyed by package + platform)."""
        now = time.time()
        with self._db() as db:
            for variant in variants:
                platform = variant["platform"]
                existing = db.execute(
                    "SELECT id FROM content_variants WHERE package_id=? AND platform=?",
                    (package_id, platform),
                ).fetchone()
                content = variant.get("content", "")
                char_count = variant.get("char_count", len(content))
                if existing:
                    db.execute(
                        "UPDATE content_variants SET content=?, char_count=?, "
                        "validation_status='generated', updated_at=? WHERE id=?",
                        (content, char_count, now, existing["id"]),
                    )
                else:
                    db.execute(
                        "INSERT INTO content_variants(id,package_id,platform,content,char_count,validation_status,publish_status,created_at,updated_at) "
                        "VALUES(?,?,?,?,?,?,?,?,?)",
                        (self._id(), package_id, platform, content, char_count, "generated", "pending", now, now),
                    )
            self._audit(db, package_id, "VARIANTS_SAVED", {"count": len(variants)})

    def get_variants(self, package_id: str) -> list[dict]:
        """Return all variant rows for a package."""
        with self._db() as db:
            return self._variants(db, package_id)

    def update_variant(self, package_id: str, variant_id: str, **fields) -> None:
        """Update one variant row (validation_status, publish_status, content, error, remote_id)."""
        allowed = {
            "content",
            "char_count",
            "validation_status",
            "publish_status",
            "error",
            "remote_id",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        sets = ", ".join(f"{key}=?" for key in updates)
        values = list(updates.values())
        with self._db() as db:
            db.execute(
                f"UPDATE content_variants SET {sets}, updated_at=? WHERE id=? AND package_id=?",
                values + [time.time(), variant_id, package_id],
            )
            self._audit(db, package_id, "VARIANT_UPDATE", {"variant_id": variant_id, **updates})

    def approve(self, package_id: str) -> dict:
        """Transition to ``approved`` — requires every variant to be ``validated``."""
        with self._db() as db:
            row = db.execute(
                "SELECT state FROM content_packages WHERE id=?", (package_id,)
            ).fetchone()
            if not row:
                raise KeyError(package_id)
            variants = self._variants(db, package_id)
            if not variants or any(
                v["validation_status"] != "validated" for v in variants
            ):
                raise ValueError("not_all_validated")
            if row["state"] != "ready_to_approve":
                # allow direct approve from ready_to_approve only
                raise ValueError(f"invalid_transition:{row['state']}->approved")
            db.execute(
                "UPDATE content_packages SET state='approved', updated_at=? WHERE id=?",
                (time.time(), package_id),
            )
            self._audit(db, package_id, "APPROVED", {})
            return {"state": "approved"}

    # ── Audit ───────────────────────────────────────────────────────────────

    def audit(self, package_id: str, kind: str, payload: dict | None = None) -> None:
        """Append an audit event for the package."""
        with self._db() as db:
            self._audit(db, package_id, kind, payload or {})

    def history(self, package_id: str) -> list[dict]:
        """Return the audit trail for a package (newest first)."""
        with self._db() as db:
            rows = db.execute(
                "SELECT * FROM content_package_audit WHERE package_id=? "
                "ORDER BY created_at DESC, rowid DESC",
                (package_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def _audit(self, db: sqlite3.Connection, package_id: str, kind: str, payload: dict) -> None:
        db.execute(
            "INSERT INTO content_package_audit VALUES (?,?,?,?,?)",
            (self._id(), package_id, kind, json.dumps(payload, sort_keys=True), time.time()),
        )
