"""Content-Forge brief store (spec §3.1, P0-1).

Versioned, append-only Brief persistence following the ContentOpsStore
pattern: sync sqlite3, JSON-encoded payloads, uuid-hex ids, append-only
audit events. Each save is immutable — updates append a NEW version and the
old versions stay retrievable via ``versions()``.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from src.forge.brief_schemas import Brief, BriefCreate
from src.forge.constants import FORGE_CHANNELS


class BriefStore:
    """Persist and validate versioned briefs (sync sqlite3)."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS briefs(
                    brief_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (brief_id, version)
                );
                CREATE TABLE IF NOT EXISTS brief_audit_events(
                    id TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
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

    def _audit(self, db: sqlite3.Connection, entity_id: str, kind: str, payload: dict) -> None:
        db.execute(
            "INSERT INTO brief_audit_events VALUES (?,?,?,?,?)",
            (self._id(), entity_id, kind, json.dumps(payload, sort_keys=True), time.time()),
        )

    # -- row <-> model helpers -------------------------------------------------

    def _row_to_brief(self, row: sqlite3.Row) -> Brief:
        payload = json.loads(row["payload"])
        return Brief(
            **payload,
            brief_id=row["brief_id"],
            version=row["version"],
            status=row["status"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )

    def _latest_row(self, db: sqlite3.Connection, brief_id: str) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM briefs WHERE brief_id=? ORDER BY version DESC LIMIT 1",
            (brief_id,),
        ).fetchone()
        if not row:
            raise KeyError(brief_id)
        return row

    # -- public API -------------------------------------------------------------

    def create_brief(self, payload: BriefCreate, created_by: str = "system") -> Brief:
        brief_id = self._id()
        now = time.time()
        with self._db() as db:
            db.execute(
                "INSERT INTO briefs(brief_id,version,payload,status,created_by,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (brief_id, 1, payload.model_dump_json(), "draft", created_by, now),
            )
            self._audit(db, brief_id, "BRIEF_CREATED", {"version": 1, "created_by": created_by})
        return self.get_brief(brief_id)

    def get_brief(self, brief_id: str) -> Brief:
        """Return the LATEST version of a brief. Raises KeyError(brief_id) if missing."""
        with self._db() as db:
            row = self._latest_row(db, brief_id)
            return self._row_to_brief(row)

    def update_brief(self, brief_id: str, payload: BriefCreate, created_by: str) -> Brief:
        """Bump version += 1 and store a NEW immutable version; returns it."""
        with self._db() as db:
            latest = self._latest_row(db, brief_id)
            new_version = latest["version"] + 1
            now = time.time()
            db.execute(
                "INSERT INTO briefs(brief_id,version,payload,status,created_by,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (brief_id, new_version, payload.model_dump_json(), "draft", created_by, now),
            )
            self._audit(
                db,
                brief_id,
                "BRIEF_UPDATED",
                {"version": new_version, "created_by": created_by},
            )
            return self._row_to_brief(self._latest_row(db, brief_id))

    def versions(self, brief_id: str) -> list[Brief]:
        """All versions of a brief, oldest → newest. Raises KeyError if missing."""
        with self._db() as db:
            rows = db.execute(
                "SELECT * FROM briefs WHERE brief_id=? ORDER BY version ASC",
                (brief_id,),
            ).fetchall()
            if not rows:
                raise KeyError(brief_id)
            return [self._row_to_brief(r) for r in rows]

    def validate(self, brief_id: str) -> dict:
        """Deterministic validation of the LATEST brief version (spec §3.1).

        Returns {"valid": bool, "errors": [str], "warnings": [str]}.
        """
        brief = self.get_brief(brief_id)
        errors: list[str] = []
        warnings: list[str] = []

        channels = brief.channels
        if not channels:
            errors.append("channels_empty")
        unknown = sorted(set(channels) - set(FORGE_CHANNELS))
        if unknown:
            errors.append("channels_unknown:" + ",".join(unknown))

        if channels:
            constraint_keys = set(brief.output_constraints)
            if not constraint_keys.issubset(set(channels)):
                errors.append("output_constraints_channel_mismatch")

        for phrase in brief.prohibited_phrases:
            if not phrase.strip():
                errors.append("prohibited_phrase_empty")
                break
        seen: set[str] = set()
        for phrase in brief.prohibited_phrases:
            key = phrase.strip().lower()
            if key in seen:
                warnings.append("duplicate_prohibited_phrase")
                break
            seen.add(key)

        for claim in brief.required_claims:
            if not claim.strip():
                errors.append("required_claim_empty")
                break

        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def archive_brief(self, brief_id: str) -> None:
        """Mark the LATEST version archived (append-only history untouched)."""
        with self._db() as db:
            latest = self._latest_row(db, brief_id)
            db.execute(
                "UPDATE briefs SET status='archived' WHERE brief_id=? AND version=?",
                (brief_id, latest["version"]),
            )
            self._audit(db, brief_id, "BRIEF_ARCHIVED", {"version": latest["version"]})


__all__ = ["BriefStore"]
