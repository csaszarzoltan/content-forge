"""Durable family workspace, review, journey, idea, and publish workflow."""

from __future__ import annotations

import difflib
import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from pathlib import Path

ROLES = {
    "ADULT_OWNER": {"manage_members", "create", "edit", "review", "publish", "view"},
    "ADULT_COLLABORATOR": {"create", "edit", "review", "publish", "view"},
    "TEEN_CONTRIBUTOR": {"create", "edit", "submit_review", "view"},
    "VIEWER": {"view"},
}


class PermissionDenied(PermissionError):
    pass


def _id():
    return uuid.uuid4().hex


def _row(r):
    return dict(r) if r else None


class FamilyStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self.db() as d:
            d.executescript("""
CREATE TABLE IF NOT EXISTS family_workspaces(id TEXT PRIMARY KEY,name TEXT,mode TEXT,created_by TEXT,created_at REAL);
CREATE TABLE IF NOT EXISTS family_memberships(id TEXT PRIMARY KEY,workspace_id TEXT,user_id TEXT,display_name TEXT,email TEXT,role TEXT,state TEXT,joined_at REAL,UNIQUE(workspace_id,user_id));
CREATE TABLE IF NOT EXISTS family_invitations(id TEXT PRIMARY KEY,workspace_id TEXT,email TEXT,role TEXT,token_hash TEXT UNIQUE,token_once TEXT,state TEXT,expires_at REAL,created_by TEXT,accepted_by TEXT,created_at REAL);
CREATE TABLE IF NOT EXISTS family_projects(id TEXT PRIMARY KEY,workspace_id TEXT,name TEXT,goal TEXT,audience TEXT,state TEXT,created_by TEXT,created_at REAL);
CREATE TABLE IF NOT EXISTS family_assets(id TEXT PRIMARY KEY,workspace_id TEXT,project_id TEXT,channel TEXT,title TEXT,content TEXT,state TEXT,version INTEGER,author_id TEXT,created_at REAL);
CREATE TABLE IF NOT EXISTS family_revisions(id TEXT PRIMARY KEY,asset_id TEXT,version INTEGER,content TEXT,author_id TEXT,created_at REAL,UNIQUE(asset_id,version));
CREATE TABLE IF NOT EXISTS family_reviews(id TEXT PRIMARY KEY,workspace_id TEXT,asset_id TEXT,revision_version INTEGER,note TEXT,state TEXT,requester_id TEXT,reviewer_id TEXT,reason TEXT,created_at REAL,decided_at REAL,UNIQUE(asset_id,revision_version));
CREATE TABLE IF NOT EXISTS family_ideas(id TEXT PRIMARY KEY,workspace_id TEXT,project_id TEXT,author_id TEXT,client_id TEXT,kind TEXT,text TEXT,caption TEXT,asset_path TEXT,state TEXT,created_at REAL,UNIQUE(workspace_id,client_id));
CREATE TABLE IF NOT EXISTS family_publish_batches(id TEXT PRIMARY KEY,workspace_id TEXT,asset_id TEXT,revision_version INTEGER,state TEXT,channels TEXT,created_by TEXT,created_at REAL);
CREATE TABLE IF NOT EXISTS family_deliveries(id TEXT PRIMARY KEY,batch_id TEXT,channel TEXT,state TEXT,remote_id TEXT,error TEXT,UNIQUE(batch_id,channel));
CREATE TABLE IF NOT EXISTS family_idempotency(workspace_id TEXT,actor_id TEXT,key TEXT,request_hash TEXT,response TEXT,PRIMARY KEY(workspace_id,actor_id,key));
CREATE TABLE IF NOT EXISTS family_audit(id TEXT PRIMARY KEY,workspace_id TEXT,actor_id TEXT,kind TEXT,entity_id TEXT,payload TEXT,created_at REAL);
""")
            for table, column, ddl in [
                ("family_invitations", "revoked_at", "REAL"),
                ("family_memberships", "updated_at", "REAL"),
                ("family_assets", "updated_at", "REAL"),
                ("family_reviews", "updated_at", "REAL"),
                ("family_deliveries", "attempt_count", "INTEGER NOT NULL DEFAULT 1"),
                ("family_deliveries", "last_attempt_at", "REAL"),
                ("family_deliveries", "error_code", "TEXT"),
            ]:
                cols = {row[1] for row in d.execute(f"PRAGMA table_info({table})")}
                if column not in cols:
                    d.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            d.execute("UPDATE family_invitations SET token_once=NULL WHERE state='PENDING'")

    def db(self):
        d = sqlite3.connect(self.path)
        d.row_factory = sqlite3.Row
        return d

    def _audit(self, d, w, u, k, e, p):
        d.execute(
            "INSERT INTO family_audit VALUES(?,?,?,?,?,?,?)",
            (_id(), w, u, k, e, json.dumps(p, sort_keys=True), time.time()),
        )

    def membership(self, w, u):
        with self.db() as d:
            r = d.execute(
                "SELECT * FROM family_memberships WHERE workspace_id=? AND user_id=? AND state='ACTIVE'",
                (w, u),
            ).fetchone()
        if not r:
            raise PermissionDenied("membership_required")
        return dict(r)

    def permissions(self, w, u):
        return sorted(ROLES[self.membership(w, u)["role"]])

    def require(self, w, u, p):
        if p not in self.permissions(w, u):
            raise PermissionDenied(f"{p}_forbidden")

    def _idem(self, d, w, u, key, payload):
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        r = d.execute(
            "SELECT request_hash,response FROM family_idempotency WHERE workspace_id=? AND actor_id=? AND key=?",
            (w, u, key),
        ).fetchone()
        if r and r[0] != h:
            raise ValueError("idempotency_key_reused")
        return json.loads(r[1]) if r else None

    def _save_idem(self, d, w, u, key, payload, response):
        d.execute(
            "INSERT INTO family_idempotency VALUES(?,?,?,?,?)",
            (
                w,
                u,
                key,
                hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                json.dumps(response),
            ),
        )

    def create_workspace(self, u, name_display, name, mode, key):
        if not 2 <= len(name.strip()) <= 80 or mode not in {"FAMILY_CREATOR", "FAMILY_BUSINESS"}:
            raise ValueError("invalid_workspace")
        payload = {"name": name.strip(), "mode": mode}
        with self.db() as d:
            old = self._idem(d, "NEW", u, key, payload)
            if old:
                return old
            w = _id()
            m = _id()
            now = time.time()
            d.execute(
                "INSERT INTO family_workspaces VALUES(?,?,?,?,?)", (w, name.strip(), mode, u, now)
            )
            d.execute(
                "INSERT INTO family_memberships(id,workspace_id,user_id,display_name,email,role,state,joined_at) VALUES(?,?,?,?,?,?,?,?)",
                (m, w, u, name_display, "", "ADULT_OWNER", "ACTIVE", now),
            )
            out = {
                "workspace": {"id": w, "name": name.strip(), "mode": mode},
                "membership": {"id": m, "role": "ADULT_OWNER"},
                "next_url": "#/home",
            }
            self._save_idem(d, "NEW", u, key, payload, out)
            self._audit(d, w, u, "WORKSPACE_CREATED", w, {"mode": mode})
            return out

    def create_invitation(self, w, u, email, role):
        self.require(w, u, "manage_members")
        if role not in {"ADULT_COLLABORATOR", "TEEN_CONTRIBUTOR", "VIEWER"} or "@" not in email:
            raise ValueError("invalid_invitation")
        token = secrets.token_urlsafe(32)
        now = time.time()
        iid = _id()
        with self.db() as d:
            d.execute(
                "INSERT INTO family_invitations(id,workspace_id,email,role,token_hash,token_once,state,expires_at,created_by,accepted_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    iid,
                    w,
                    email.strip().lower(),
                    role,
                    hashlib.sha256(token.encode()).hexdigest(),
                    token,
                    "PENDING",
                    now + 604800,
                    u,
                    None,
                    now,
                ),
            )
            self._audit(d, w, u, "INVITATION_CREATED", iid, {"role": role})
        return {
            "id": iid,
            "workspace_id": w,
            "role": role,
            "expires_at": now + 604800,
            "token": token,
            "accept_url": f"#/join/{token}",
        }

    def accept_invitation(self, token, u, email):
        h = hashlib.sha256(token.encode()).hexdigest()
        with self.db() as d:
            inv = d.execute("SELECT * FROM family_invitations WHERE token_hash=?", (h,)).fetchone()
            if not inv:
                raise KeyError("invitation_not_found")
            inv = dict(inv)
            existing = d.execute(
                "SELECT * FROM family_memberships WHERE workspace_id=? AND user_id=?",
                (inv["workspace_id"], u),
            ).fetchone()
            if existing:
                return dict(existing)
            if inv["state"] == "REVOKED":
                raise ValueError("invitation_revoked")
            if inv["state"] != "PENDING" or inv["expires_at"] < time.time():
                raise ValueError("invitation_expired")
            if inv["email"] != email.strip().lower():
                raise PermissionDenied("invitation_email_mismatch")
            mid = _id()
            d.execute(
                "INSERT INTO family_memberships(id,workspace_id,user_id,display_name,email,role,state,joined_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    mid,
                    inv["workspace_id"],
                    u,
                    email.split("@")[0],
                    email.lower(),
                    inv["role"],
                    "ACTIVE",
                    time.time(),
                ),
            )
            d.execute(
                "UPDATE family_invitations SET state='ACCEPTED',accepted_by=? WHERE id=?",
                (u, inv["id"]),
            )
            self._audit(
                d, inv["workspace_id"], u, "INVITATION_ACCEPTED", mid, {"role": inv["role"]}
            )
            return _row(d.execute("SELECT * FROM family_memberships WHERE id=?", (mid,)).fetchone())

    def session(self, w, u):
        m = self.membership(w, u)
        with self.db() as d:
            ws = _row(d.execute("SELECT * FROM family_workspaces WHERE id=?", (w,)).fetchone())
        perms = sorted(ROLES[m["role"]])
        nav = [
            {"route": r, "label": l}
            for r, l in [
                ("home", "Home"),
                ("create", "Create"),
                ("projects", "Projects"),
                ("review", "Review"),
                ("calendar", "Calendar"),
            ]
            if r != "review" or "review" in perms
        ]
        return {
            "workspace": ws,
            "membership": m,
            "permissions": perms,
            "navigation": nav,
            "onboarding": {"percent": 75},
        }

    def home(self, w, u):
        self.membership(w, u)
        with self.db() as d:
            projects = [
                dict(x)
                for x in d.execute(
                    "SELECT * FROM family_projects WHERE workspace_id=? ORDER BY created_at DESC",
                    (w,),
                )
            ]
            reviews = [
                dict(x)
                for x in d.execute(
                    "SELECT r.*,a.title FROM family_reviews r JOIN family_assets a ON a.id=r.asset_id WHERE r.workspace_id=? AND r.state='PENDING' ORDER BY r.created_at",
                    (w,),
                )
            ]
            ideas = [
                dict(x)
                for x in d.execute(
                    "SELECT * FROM family_ideas WHERE workspace_id=? ORDER BY created_at DESC LIMIT 10",
                    (w,),
                )
            ]
        if reviews and "review" in self.permissions(w, u):
            nxt = {
                "kind": "REVIEW",
                "label": f"Review {reviews[0]['title']}",
                "href": f"#/review/{reviews[0]['id']}",
            }
        elif projects:
            nxt = {
                "kind": "CONTINUE_PROJECT",
                "label": f"Continue {projects[0]['name']}",
                "href": f"#/projects/{projects[0]['id']}",
            }
        else:
            nxt = {"kind": "START_PROJECT", "label": "Start a project", "href": "#/create/project"}
        return {
            "next_action": nxt,
            "projects": projects,
            "reviews": reviews,
            "ideas": ideas,
            "onboarding": {"percent": 75},
            "last_refreshed_at": time.time(),
        }

    def create_journey(self, w, u, b, key):
        self.require(w, u, "create")
        channels = b.get("channels", [])
        if (
            b.get("goal") not in {"PROMOTE_SHOP", "SHARE_PROJECT", "WEEKLY_UPDATE"}
            or not 2 <= len(b.get("project_name", "").strip()) <= 80
            or len(b.get("message", "").strip()) < 10
            or not channels
            or any(c not in {"linkedin", "twitter"} for c in channels)
        ):
            raise ValueError("invalid_journey")
        with self.db() as d:
            old = self._idem(d, w, u, key, b)
            if old:
                return old
            pid = _id()
            now = time.time()
            d.execute(
                "INSERT INTO family_projects VALUES(?,?,?,?,?,?,?,?)",
                (
                    pid,
                    w,
                    b["project_name"].strip(),
                    b["goal"],
                    b.get("audience", ""),
                    "DRAFT",
                    u,
                    now,
                ),
            )
            assets = []
            for c in channels:
                aid = _id()
                content = f"{b['message'].strip()}" + (
                    f"\n\n{b['cta'].strip()}" if b.get("cta", "").strip() else ""
                )
                title = f"{b['project_name']} - {c.title()}"
                d.execute(
                    "INSERT INTO family_assets(id,workspace_id,project_id,channel,title,content,state,version,author_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (aid, w, pid, c, title, content, "DRAFT", 1, u, now),
                )
                d.execute(
                    "INSERT INTO family_revisions VALUES(?,?,?,?,?,?)",
                    (_id(), aid, 1, content, u, now),
                )
                assets.append(
                    {
                        "id": aid,
                        "channel": c,
                        "title": title,
                        "content": content,
                        "version": 1,
                        "state": "DRAFT",
                    }
                )
            out = {
                "project": {"id": pid, "name": b["project_name"], "state": "DRAFT"},
                "assets": assets,
                "checks": [],
                "next_url": f"#/projects/{pid}/assets/{assets[0]['id']}",
            }
            self._save_idem(d, w, u, key, b, out)
            self._audit(d, w, u, "JOURNEY_CREATED", pid, {"channels": channels})
            return out

    def save_revision(self, w, u, aid, content, expected):
        self.require(w, u, "edit")
        with self.db() as d:
            a = d.execute(
                "SELECT * FROM family_assets WHERE id=? AND workspace_id=?", (aid, w)
            ).fetchone()
            if not a:
                raise KeyError("asset_not_found")
            if a["version"] != expected:
                raise ValueError("asset_version_conflict")
            v = expected + 1
            d.execute(
                "INSERT INTO family_revisions VALUES(?,?,?,?,?,?)",
                (_id(), aid, v, content, u, time.time()),
            )
            d.execute(
                "UPDATE family_assets SET content=?,version=?,state='DRAFT' WHERE id=?",
                (content, v, aid),
            )
            d.execute(
                "UPDATE family_reviews SET state='SUPERSEDED' WHERE asset_id=? AND state IN ('PENDING','APPROVED')",
                (aid,),
            )
            return {"id": aid, "version": v, "content": content}

    def submit_review(self, w, u, aid, note):
        self.require(w, u, "edit")
        with self.db() as d:
            a = d.execute(
                "SELECT * FROM family_assets WHERE id=? AND workspace_id=?", (aid, w)
            ).fetchone()
            if not a:
                raise KeyError("asset_not_found")
            old = d.execute(
                "SELECT * FROM family_reviews WHERE asset_id=? AND revision_version=?",
                (aid, a["version"]),
            ).fetchone()
            if old:
                return dict(old)
            rid = _id()
            now = time.time()
            d.execute(
                "INSERT INTO family_reviews(id,workspace_id,asset_id,revision_version,note,state,requester_id,reviewer_id,reason,created_at,decided_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (rid, w, aid, a["version"], note[:500], "PENDING", u, None, None, now, None),
            )
            d.execute("UPDATE family_assets SET state='WAITING_APPROVAL' WHERE id=?", (aid,))
            self._audit(d, w, u, "REVIEW_SUBMITTED", rid, {"version": a["version"]})
            return _row(d.execute("SELECT * FROM family_reviews WHERE id=?", (rid,)).fetchone())

    def reviews(self, w, u):
        self.membership(w, u)
        with self.db() as d:
            return [
                dict(x)
                for x in d.execute(
                    "SELECT r.*,a.title,a.channel,a.content FROM family_reviews r JOIN family_assets a ON a.id=r.asset_id WHERE r.workspace_id=? ORDER BY r.created_at DESC",
                    (w,),
                )
            ]

    def decide_review(self, w, u, rid, decision, reason):
        self.require(w, u, "review")
        if decision not in {"APPROVED", "NEEDS_CHANGES"} or (
            decision == "NEEDS_CHANGES" and len(reason.strip()) < 10
        ):
            raise ValueError("invalid_decision")
        with self.db() as d:
            r = d.execute(
                "SELECT r.*,a.version FROM family_reviews r JOIN family_assets a ON a.id=r.asset_id WHERE r.id=? AND r.workspace_id=?",
                (rid, w),
            ).fetchone()
            if not r:
                raise KeyError("review_not_found")
            if r["state"] != "PENDING" or r["revision_version"] != r["version"]:
                raise ValueError("review_stale")
            d.execute(
                "UPDATE family_reviews SET state=?,reviewer_id=?,reason=?,decided_at=? WHERE id=?",
                (decision, u, reason, time.time(), rid),
            )
            d.execute(
                "UPDATE family_assets SET state=? WHERE id=?",
                ("APPROVED" if decision == "APPROVED" else "DRAFT", r["asset_id"]),
            )
            self._audit(d, w, u, "REVIEW_DECIDED", rid, {"decision": decision})
            return _row(d.execute("SELECT * FROM family_reviews WHERE id=?", (rid,)).fetchone())

    def create_idea(self, w, u, client, kind, text, caption, path):
        self.require(w, u, "create")
        if kind not in {"TEXT", "IMAGE"} or (kind == "TEXT" and not text) or len(text or "") > 2000:
            raise ValueError("invalid_idea")
        with self.db() as d:
            old = d.execute(
                "SELECT * FROM family_ideas WHERE workspace_id=? AND client_id=?", (w, client)
            ).fetchone()
            if old:
                return dict(old)
            iid = _id()
            d.execute(
                "INSERT INTO family_ideas VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (iid, w, None, u, client, kind, text, caption, path, "PRIVATE", time.time()),
            )
            return _row(d.execute("SELECT * FROM family_ideas WHERE id=?", (iid,)).fetchone())

    def publish(self, w, u, aid, version, channels, key):
        self.require(w, u, "publish")
        payload = {"asset_id": aid, "revision_version": version, "channels": channels}
        with self.db() as d:
            old = self._idem(d, w, u, key, payload)
            if old:
                return old
            a = d.execute(
                "SELECT * FROM family_assets WHERE id=? AND workspace_id=?", (aid, w)
            ).fetchone()
            if not a:
                raise KeyError("asset_not_found")
            ok = d.execute(
                "SELECT id FROM family_reviews WHERE asset_id=? AND revision_version=? AND state='APPROVED'",
                (aid, version),
            ).fetchone()
            if a["version"] != version or not ok:
                raise ValueError("approval_required_for_current_revision")
            bid = _id()
            d.execute(
                "INSERT INTO family_publish_batches VALUES(?,?,?,?,?,?,?,?)",
                (bid, w, aid, version, "PUBLISHED", json.dumps(channels), u, time.time()),
            )
            deliveries = []
            for c in channels:
                did = _id()
                d.execute(
                    "INSERT INTO family_deliveries(id,batch_id,channel,state,remote_id,error) VALUES(?,?,?,?,?,?)",
                    (did, bid, c, "PUBLISHED", f"demo-{did[:8]}", None),
                )
                deliveries.append({"id": did, "channel": c, "state": "PUBLISHED"})
            out = {"id": bid, "state": "PUBLISHED", "deliveries": deliveries}
            self._save_idem(d, w, u, key, payload, out)
            self._audit(d, w, u, "PUBLISHED", bid, {"version": version, "channels": channels})
            return out

    def invitation_preview(self, token: str) -> dict:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.db() as d:
            row = d.execute(
                "SELECT i.id,i.role,i.state,i.expires_at,i.revoked_at,w.name workspace_name,m.display_name inviter_name FROM family_invitations i JOIN family_workspaces w ON w.id=i.workspace_id LEFT JOIN family_memberships m ON m.workspace_id=i.workspace_id AND m.user_id=i.created_by WHERE i.token_hash=?",
                (token_hash,),
            ).fetchone()
        if not row:
            raise KeyError("invitation_not_found")
        out = dict(row)
        if out["revoked_at"] is not None or out["state"] == "REVOKED":
            raise ValueError("invitation_revoked")
        if out["expires_at"] < time.time():
            raise ValueError("invitation_expired")
        return out

    def revoke_invitation(self, w, u, iid):
        self.require(w, u, "manage_members")
        with self.db() as d:
            cur = d.execute(
                "UPDATE family_invitations SET state='REVOKED',revoked_at=? WHERE id=? AND workspace_id=? AND state='PENDING'",
                (time.time(), iid, w),
            )
            if not cur.rowcount:
                raise KeyError("invitation_not_found")
            self._audit(d, w, u, "INVITATION_REVOKED", iid, {})

    def members(self, w, u):
        self.require(w, u, "manage_members")
        with self.db() as d:
            return {
                "members": [
                    dict(x)
                    for x in d.execute(
                        "SELECT * FROM family_memberships WHERE workspace_id=? AND state='ACTIVE' ORDER BY joined_at",
                        (w,),
                    )
                ],
                "invitations": [
                    dict(x)
                    for x in d.execute(
                        "SELECT id,role,state,expires_at,created_at FROM family_invitations WHERE workspace_id=? AND state='PENDING' ORDER BY created_at",
                        (w,),
                    )
                ],
            }

    def update_member(self, w, u, mid, role):
        self.require(w, u, "manage_members")
        if role not in ROLES:
            raise ValueError("invalid_role")
        with self.db() as d:
            t = d.execute(
                "SELECT * FROM family_memberships WHERE id=? AND workspace_id=?", (mid, w)
            ).fetchone()
            if not t:
                raise KeyError("membership_not_found")
            if (
                t["role"] == "ADULT_OWNER"
                and role != "ADULT_OWNER"
                and d.execute(
                    "SELECT count(*) FROM family_memberships WHERE workspace_id=? AND state='ACTIVE' AND role='ADULT_OWNER'",
                    (w,),
                ).fetchone()[0]
                <= 1
            ):
                raise ValueError("last_owner_required")
            d.execute(
                "UPDATE family_memberships SET role=?,updated_at=? WHERE id=?",
                (role, time.time(), mid),
            )
            self._audit(d, w, u, "MEMBER_ROLE_CHANGED", mid, {"from": t["role"], "to": role})
            return dict(d.execute("SELECT * FROM family_memberships WHERE id=?", (mid,)).fetchone())

    def remove_member(self, w, u, mid):
        self.require(w, u, "manage_members")
        with self.db() as d:
            t = d.execute(
                "SELECT * FROM family_memberships WHERE id=? AND workspace_id=?", (mid, w)
            ).fetchone()
            if not t:
                raise KeyError("membership_not_found")
            if (
                t["role"] == "ADULT_OWNER"
                and d.execute(
                    "SELECT count(*) FROM family_memberships WHERE workspace_id=? AND state='ACTIVE' AND role='ADULT_OWNER'",
                    (w,),
                ).fetchone()[0]
                <= 1
            ):
                raise ValueError("last_owner_required")
            d.execute(
                "UPDATE family_memberships SET state='REMOVED',updated_at=? WHERE id=?",
                (time.time(), mid),
            )
            self._audit(d, w, u, "MEMBER_REMOVED", mid, {})

    def asset_detail(self, w, u, aid):
        self.membership(w, u)
        with self.db() as d:
            r = d.execute(
                "SELECT a.*,p.name project_name FROM family_assets a JOIN family_projects p ON p.id=a.project_id WHERE a.id=? AND a.workspace_id=?",
                (aid, w),
            ).fetchone()
            if not r:
                raise KeyError("asset_not_found")
            out = dict(r)
            out["revisions"] = [
                dict(x)
                for x in d.execute(
                    "SELECT * FROM family_revisions WHERE asset_id=? ORDER BY version DESC", (aid,)
                )
            ]
            return out

    def review_detail(self, w, u, rid):
        self.membership(w, u)
        with self.db() as d:
            r = d.execute(
                "SELECT r.*,a.title,a.channel,a.content,a.version,p.name project_name FROM family_reviews r JOIN family_assets a ON a.id=r.asset_id JOIN family_projects p ON p.id=a.project_id WHERE r.id=? AND r.workspace_id=?",
                (rid, w),
            ).fetchone()
            if not r:
                raise KeyError("review_not_found")
            out = dict(r)
            revs = list(
                d.execute(
                    "SELECT version,content FROM family_revisions WHERE asset_id=? AND version<=? ORDER BY version DESC LIMIT 2",
                    (r["asset_id"], r["revision_version"]),
                )
            )
        old = revs[1]["content"] if len(revs) > 1 else ""
        new = revs[0]["content"] if revs else out["content"]
        out["diff"] = [
            {
                "kind": "added"
                if p.startswith("+ ")
                else "removed"
                if p.startswith("- ")
                else "unchanged",
                "text": p[2:],
            }
            for p in difflib.ndiff(old.split(), new.split())
        ]
        return out

    def publish_eligibility(self, w, u, aid):
        self.require(w, u, "publish")
        asset = self.asset_detail(w, u, aid)
        with self.db() as d:
            a = d.execute(
                "SELECT * FROM family_reviews WHERE asset_id=? AND revision_version=? AND state='APPROVED'",
                (aid, asset["version"]),
            ).fetchone()
        return {
            "eligible": bool(a),
            "asset": asset,
            "approval": dict(a) if a else None,
            "blockers": [] if a else ["approval_required_for_current_revision"],
        }

    def set_delivery_state(self, bid, channel, state, error=None):
        with self.db() as d:
            d.execute(
                "UPDATE family_deliveries SET state=?,error=?,error_code=? WHERE batch_id=? AND channel=?",
                (state, error, error, bid, channel),
            )

    def publish_result(self, w, u, bid):
        self.require(w, u, "publish")
        with self.db() as d:
            b = d.execute(
                "SELECT * FROM family_publish_batches WHERE id=? AND workspace_id=?", (bid, w)
            ).fetchone()
            if not b:
                raise KeyError("publish_batch_not_found")
            deliveries = [
                dict(x)
                for x in d.execute(
                    "SELECT * FROM family_deliveries WHERE batch_id=? ORDER BY rowid", (bid,)
                )
            ]
        states = {x["state"] for x in deliveries}
        state = (
            "UNKNOWN"
            if "UNKNOWN" in states
            else "PARTIAL"
            if "PUBLISHED" in states and states != {"PUBLISHED"}
            else "PUBLISHED"
            if states == {"PUBLISHED"}
            else "FAILED"
        )
        out = dict(b)
        out.update(state=state, deliveries=deliveries)
        return out

    def retry_publish(self, w, u, bid):
        result = self.publish_result(w, u, bid)
        if any(x["state"] == "UNKNOWN" for x in result["deliveries"]):
            raise ValueError("reconciliation_required")
        retry = [x for x in result["deliveries"] if x["state"] in {"FAILED", "RETRYABLE"}]
        if not retry:
            raise ValueError("nothing_to_retry")
        with self.db() as d:
            for x in retry:
                d.execute(
                    "UPDATE family_deliveries SET state='PUBLISHED',attempt_count=attempt_count+1,last_attempt_at=?,error=NULL,error_code=NULL WHERE id=?",
                    (time.time(), x["id"]),
                )
        return {
            "id": bid,
            "retried": [x["channel"] for x in retry],
            "state": self.publish_result(w, u, bid)["state"],
        }

    def reconcile_publish(self, w, u, bid):
        self.require(w, u, "publish")
        with self.db() as d:
            d.execute(
                "UPDATE family_deliveries SET state='FAILED',error_code='provider_state_unknown' WHERE batch_id=? AND state='UNKNOWN'",
                (bid,),
            )
        return self.publish_result(w, u, bid)

    def weekly_summary(self, workspace_id: str, actor_id: str) -> dict:
        """Return simple, family-friendly seven-day completion counts."""
        self.membership(workspace_id, actor_id)
        since = time.time() - 7 * 86400
        with self.db() as d:
            projects = d.execute(
                "SELECT count(*) FROM family_projects WHERE workspace_id=? AND created_at>=?",
                (workspace_id, since),
            ).fetchone()[0]
            reviews = d.execute(
                "SELECT count(*) FROM family_reviews WHERE workspace_id=? AND decided_at>=? AND state='APPROVED'",
                (workspace_id, since),
            ).fetchone()[0]
            posts = d.execute(
                "SELECT count(*) FROM family_deliveries x JOIN family_publish_batches b ON b.id=x.batch_id WHERE b.workspace_id=? AND x.state='PUBLISHED' AND b.created_at>=?",
                (workspace_id, since),
            ).fetchone()[0]
        return {
            "projects_started": projects,
            "drafts_approved": reviews,
            "channels_published": posts,
            "message": f"This week your family started {projects} projects, approved {reviews} drafts, and published to {posts} channels.",
        }

    def prepare_publish_batch(
        self,
        workspace_id: str,
        actor_id: str,
        asset_id: str,
        version: int,
        channels: list[str],
        key: str,
    ) -> dict:
        """Create an idempotent queued batch without claiming provider success."""
        self.require(workspace_id, actor_id, "publish")
        payload = {"asset_id": asset_id, "revision_version": version, "channels": channels}
        with self.db() as d:
            old = self._idem(d, workspace_id, actor_id, key, payload)
            if old:
                return old
            asset = d.execute(
                "SELECT * FROM family_assets WHERE id=? AND workspace_id=?",
                (asset_id, workspace_id),
            ).fetchone()
            approved = d.execute(
                "SELECT id,reviewer_id,decided_at FROM family_reviews WHERE asset_id=? AND revision_version=? AND state='APPROVED'",
                (asset_id, version),
            ).fetchone()
            if not asset or asset["version"] != version or not approved:
                raise ValueError("approval_required_for_current_revision")
            bid = _id()
            now = time.time()
            d.execute(
                "INSERT INTO family_publish_batches VALUES(?,?,?,?,?,?,?,?)",
                (
                    bid,
                    workspace_id,
                    asset_id,
                    version,
                    "QUEUED",
                    json.dumps(channels),
                    actor_id,
                    now,
                ),
            )
            deliveries = []
            for channel in channels:
                did = _id()
                d.execute(
                    "INSERT INTO family_deliveries(id,batch_id,channel,state,remote_id,error) VALUES(?,?,?,?,?,?)",
                    (did, bid, channel, "QUEUED", None, None),
                )
                deliveries.append({"id": did, "channel": channel, "state": "QUEUED"})
            out = {
                "id": bid,
                "state": "QUEUED",
                "deliveries": deliveries,
                "asset": {
                    "id": asset_id,
                    "content": asset["content"],
                    "title": asset["title"],
                    "version": version,
                },
                "approval": {
                    "reviewer_id": approved["reviewer_id"],
                    "decided_at": approved["decided_at"],
                },
            }
            self._save_idem(d, workspace_id, actor_id, key, payload, out)
            self._audit(
                d,
                workspace_id,
                actor_id,
                "PUBLISH_QUEUED",
                bid,
                {"channels": channels, "version": version},
            )
            return out

    def complete_delivery(
        self,
        batch_id: str,
        channel: str,
        state: str,
        remote_id: str | None = None,
        error_code: str | None = None,
    ) -> None:
        with self.db() as d:
            d.execute(
                "UPDATE family_deliveries SET state=?,remote_id=?,error=?,error_code=?,last_attempt_at=? WHERE batch_id=? AND channel=?",
                (state, remote_id, error_code, error_code, time.time(), batch_id, channel),
            )
            states = {
                r[0]
                for r in d.execute(
                    "SELECT state FROM family_deliveries WHERE batch_id=?", (batch_id,)
                )
            }
            aggregate = (
                "PUBLISHED"
                if states == {"PUBLISHED"}
                else "PARTIAL"
                if "PUBLISHED" in states
                else "FAILED"
                if states <= {"FAILED", "RETRYABLE"}
                else "UNKNOWN"
                if "UNKNOWN" in states
                else "PUBLISHING"
            )
            d.execute("UPDATE family_publish_batches SET state=? WHERE id=?", (aggregate, batch_id))
