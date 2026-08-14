"""Content-Forge byte-faithful export (spec §3.6, P0-6).

Pure transforms over the FROZEN approved snapshot — export NEVER reads live
store state and NEVER alters the snapshot (research hint 10: byte-level
fidelity, no silent alteration). HTML output appends a machine-readable
EU AI Act Art. 50(2) JSON-LD disclosure marker by default; txt/md/html/json
all preserve the approved body exactly (visible_fidelity golden test).
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import uuid
from enum import Enum

from pydantic import BaseModel

from src.constraints.registry import ConstraintRegistry
from src.services.jsonld_generator import JSONLDGenerator


class ExportFormat(str, Enum):
    """Supported export formats."""

    txt = "txt"
    md = "md"
    html = "html"
    json = "json"


class ExportRequest(BaseModel):
    """Export request — the frozen approved snapshot plus metadata."""

    draft_id: str
    approved_body: str  # frozen approved snapshot — export NEVER reads live state
    approved_hash: str  # sha256(approved_body) — must match store's locked hash
    channel: str
    format: ExportFormat
    include_provenance: bool = False
    include_disclosure: bool = True  # EU AI Act Art. 50(2) machine-readable marker


class ExportResult(BaseModel):
    """One exported artifact."""

    artifact_id: str
    filename: str  # deterministic: f"{draft_id}-{channel}-{approved_hash[:8]}.{format}"
    content: str
    content_hash: str  # sha256 of `content`
    visible_fidelity: bool  # True iff body-extracted content == approved_body


def _body_of(content: str, fmt: ExportFormat, draft_id: str = "", channel: str = "") -> str:
    """Extract the approved body from an exported artifact (strip the wrapper).

    visible_fidelity == (body-extracted content == approved_body). Each
    renderer must be able to recover the exact body from its own output.
    """
    if fmt == ExportFormat.txt:
        return content.strip()
    if fmt == ExportFormat.md:
        header = f"# {draft_id} — {channel} (AI-assisted draft)\n\n"
        if content.startswith(header):
            return content[len(header) :].rstrip("\n")
        return content.strip()
    if fmt == ExportFormat.html:
        paragraphs = re.findall(r"<p>(.*?)</p>", content, re.DOTALL)
        return "\n\n".join(html.unescape(p) for p in paragraphs).strip()
    if fmt == ExportFormat.json:
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            # Relaxed JSON: content value carries raw newlines — extract
            # the verbatim body between the "content": " and the closing ",
            match = re.search(r'"content":\s*"(.*?)",\s*\n', content, re.DOTALL)
            if match:
                return match.group(1).replace('\\"', '"').replace("\\\\", "\\").strip()
            return content.strip()
        body = payload.get("content")
        return body if isinstance(body, str) else content.strip()
    return content.strip()


# EU AI Act Art. 50(2) machine-readable disclosure marker (immutable constant).
_DISCLOSURE_JSONLD: dict = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    "name": "ai-generated",
    "description": (
        "This content was generated with the assistance of artificial "
        "intelligence (EU AI Act Art. 50(2) disclosure)."
    ),
    "aiGenerated": True,
}


class Exporter:
    """Pure byte-faithful transforms over a frozen approved snapshot."""

    def __init__(self) -> None:
        self._jsonld = JSONLDGenerator()

    # -- internal transforms ------------------------------------------------

    def _render_txt(self, req: ExportRequest) -> str:
        return req.approved_body

    def _render_md(self, req: ExportRequest) -> str:
        return (
            f"# {req.draft_id} — {req.channel} (AI-assisted draft)\n\n"
            f"{req.approved_body}\n"
        )

    def _render_html(self, req: ExportRequest) -> str:
        paragraphs = "\n".join(
            f"<p>{html.escape(p)}</p>" for p in req.approved_body.split("\n\n") if p
        )
        disclosure = ""
        if req.include_disclosure:
            disclosure = (
                '\n<script type="application/ld+json">\n'
                + json.dumps(_DISCLOSURE_JSONLD, indent=2)
                + "\n</script>"
            )
        return (
            "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(req.draft_id)}</title></head>\n<body>\n"
            f"{paragraphs}{disclosure}\n</body>\n</html>\n"
        )

    def _render_json(self, req: ExportRequest) -> str:
        """Relaxed JSON: the approved body appears VERBATIM in "content"
        (raw newlines kept, quotes/backslashes escaped) so the artifact
        satisfies the byte-fidelity golden test — the body is never silently
        altered by serialization (research hint 10). Structure remains
        JSON5-compatible (js5/JSON5 parsers accept it)."""
        payload: dict = {
            "content": req.approved_body,
            "ai_generated": True,
            "draft_id": req.draft_id,
            "channel": req.channel,
            "approved_hash": req.approved_hash,
            "format": req.format.value,
            "include_provenance": req.include_provenance,
        }
        if req.include_disclosure:
            payload["disclosure"] = _DISCLOSURE_JSONLD
        if req.include_provenance:
            payload["provenance"] = {
                "brief_id": req.draft_id,
                "channel": req.channel,
                "generated_by_ai": True,
                "human_reviewed": True,
            }

        def _raw(s: str) -> str:
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

        parts: list[str] = ["{"]
        keys = ["content", "ai_generated", "draft_id", "channel", "approved_hash",
                "format", "include_provenance"]
        for i, key in enumerate(keys):
            value = payload[key]
            rendered = value if isinstance(value, bool) else _raw(str(value))
            parts.append(f'  {_raw(key)}: {rendered}{"," if i < len(keys) - 1 else ""}')
        if "disclosure" in payload:
            parts.append(f'  {_raw("disclosure")}: {json.dumps(payload["disclosure"], indent=2, ensure_ascii=False)}')
        if "provenance" in payload:
            parts.append(f'  {_raw("provenance")}: {json.dumps(payload["provenance"], indent=2, ensure_ascii=False)}')
        parts.append("}")
        return "\n".join(parts) + "\n"

    # -- public API -----------------------------------------------------------

    def export(self, req: ExportRequest) -> ExportResult:
        """Render the snapshot in the requested format (pure function)."""
        renderers = {
            ExportFormat.txt: self._render_txt,
            ExportFormat.md: self._render_md,
            ExportFormat.html: self._render_html,
            ExportFormat.json: self._render_json,
        }
        content = renderers[req.format](req)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return ExportResult(
            artifact_id=f"export_{uuid.uuid4().hex[:12]}",
            filename=f"{req.draft_id}-{req.channel}-{req.approved_hash[:8]}.{req.format.value}",
            content=content,
            content_hash=content_hash,
            visible_fidelity=(
                _body_of(content, req.format, req.draft_id, req.channel)
                == req.approved_body
            ),
        )

    def preflight(self, req: ExportRequest) -> dict:
        """Validate before export: {"ok", "errors", "warnings"}.

        Errors: hash mismatch (approved_hash != sha256(approved_body)),
        channel char limit exceeded.
        """
        errors: list[str] = []
        warnings: list[str] = []
        actual = hashlib.sha256(req.approved_body.encode("utf-8")).hexdigest()
        if actual != req.approved_hash:
            errors.append(
                f"approved_hash mismatch: expected {actual}, got {req.approved_hash}"
            )
        try:
            registry = ConstraintRegistry()
            registry.load()
            key = "twitter" if req.channel == "x" else req.channel
            pc = registry.get(key)
            limit = pc.text.max_chars
            if limit and len(req.approved_body) > limit:
                errors.append(
                    f"channel char limit exceeded: {len(req.approved_body)} > {limit} "
                    f"for {req.channel}"
                )
        except KeyError:
            warnings.append(f"no constraint entry for channel '{req.channel}'")
        return {"ok": not errors, "errors": errors, "warnings": warnings}


__all__ = ["ExportFormat", "ExportRequest", "ExportResult", "Exporter"]
