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
                """
            )

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _id() -> str:
        return uuid.uuid4().hex

    def create_campaign(self, name: str, channels: list[str]) -> str:
        clean = sorted({x.strip() for x in channels if x.strip()})
        if not name.strip() or not clean:
            raise ValueError("CAMPAIGN_INPUT_INVALID")
        campaign_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO campaigns VALUES (?,?,?,?)",
                (campaign_id, name, "DRAFT", json.dumps(clean)),
            )
        return campaign_id

    def record_asset(self, campaign_id: str, channel: str, content: str, state: str) -> str:
        if state not in {"READY", "FAILED"}:
            raise ValueError("CAMPAIGN_ASSET_STATE_INVALID")
        asset_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO assets VALUES (?,?,?,?,?)",
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

    def request_approval(
        self, asset_id: str, requester: str, risk: str, findings: list[str]
    ) -> str:
        request_id = self._id()
        with self._db() as db:
            db.execute(
                "INSERT INTO approvals VALUES (?,?,?,?,?,'PENDING',NULL,NULL)",
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

    def rows(self, table: str) -> list[dict[str, Any]]:
        allowed = {
            "campaigns",
            "approvals",
            "voice_profiles",
            "voice_rules",
            "publish_batches",
            "deliveries",
            "localization_jobs",
            "locale_variants",
            "provenance",
        }
        if table not in allowed:
            raise ValueError("TABLE_INVALID")
        with self._db() as db:
            return [dict(x) for x in db.execute(f"SELECT * FROM {table} ORDER BY rowid DESC")]


def _esc(v: Any) -> str:
    return html.escape(str(v), quote=True)


def _layout(page: str, body: str) -> str:
    title, subtitle = PAGES[page]
    nav = "".join(
        f'<a href="/workspace/{slug}"{" aria-current=page" if slug == page else ""}>{_esc(label)}</a>'
        for slug, (label, _) in PAGES.items()
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_esc(title)} | ContentForge</title><link rel="stylesheet" href="/static/workspaces.css"></head><body><a class="skip" href="#main">Skip to content</a><header><strong>ContentForge</strong><span>Content operations</span></header><div class="shell"><nav aria-label="Workspaces">{nav}</nav><main id="main" tabindex="-1"><p class="eyebrow">Workspace</p><h1>{_esc(title)}</h1><p>{_esc(subtitle)}</p><div class="live" aria-live="polite">Ready</div>{body}<section class="recovery"><h2>Recovery</h2><p>The last stable state is preserved when a dependency fails.</p><button>Try again</button></section></main></div></body></html>"""


def _cards(rows: list[dict[str, Any]], keys: list[str], empty: str) -> str:
    if not rows:
        return f'<div class="empty"><h2>Empty state</h2><p>{_esc(empty)}</p></div>'
    return (
        '<div class="cards">'
        + "".join(
            "<article>"
            + "".join(
                f"<p><strong>{_esc(k.replace('_', ' ').title())}:</strong> {_esc(r.get(k, ''))}</p>"
                for k in keys
            )
            + "</article>"
            for r in rows
        )
        + "</div>"
    )


def render_workspace(page: str, store: ContentOpsStore) -> str:
    if page not in PAGES:
        raise KeyError(page)
    if page == "campaigns":
        body = (
            '<section class=panel><h2>New campaign</h2><label>Campaign brief<textarea></textarea></label><label>Channels<input placeholder="LinkedIn, X"></label><button class=primary>Generate assets</button></section>'
            + _cards(
                store.rows("campaigns"),
                ["name", "state"],
                "Create a campaign to turn one brief into channel-ready assets.",
            )
        )
    elif page == "approvals":
        body = (
            "<section class=panel><div class=heading><h2>Governance queue</h2><label>Risk filter<select><option>All</option><option>HIGH</option></select></label></div>"
            + _cards(
                store.rows("approvals"),
                ["asset_id", "risk", "state", "findings"],
                "New compliance or brand findings will appear here.",
            )
            + "</section>"
        )
    elif page == "voice":
        rules = store.rows("voice_rules")
        conflict = any(r["state"] == "CONFLICT" for r in rules)
        action = "" if conflict else "<button class=primary>Activate profile</button>"
        body = (
            "<section class=panel><h2>Evidence-backed rules</h2>"
            + action
            + _cards(
                rules,
                ["kind", "value", "evidence", "state"],
                "Import representative content to extract explainable voice rules.",
            )
            + "</section>"
        )
    elif page == "publish":
        body = (
            "<section class=panel><h2>Channel previews</h2><div class=preview><article>LinkedIn preview</article><article>X preview</article></div>"
            + _cards(
                store.rows("deliveries"),
                ["channel", "state", "remote_id"],
                "Choose an approved asset to validate channels and credentials.",
            )
            + "</section>"
        )
    elif page == "localization":
        body = (
            "<section class=panel><h2>Locale matrix</h2>"
            + _cards(
                store.rows("locale_variants"),
                ["locale", "score", "state", "content"],
                "Select source content and target locales to start translation QA.",
            )
            + "</section>"
        )
    else:
        body = (
            "<section class=panel><h2>Provenance ledger</h2><p>Model, prompt template, voice version, human edits, approvals, and delivery form one audit trail.</p>"
            + _cards(
                store.rows("provenance"),
                ["asset_id", "model", "voice_version", "state"],
                "Provenance records appear after the first generated asset.",
            )
            + "</section>"
        )
    return _layout(page, body)
